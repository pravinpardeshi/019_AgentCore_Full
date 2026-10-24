from typing import TypedDict, Annotated, Sequence, Optional
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
from sqlalchemy.orm import Session
from src.services.rag import rag_service
from src.tools.registry import registry
from config.config import settings


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    query: str
    context: str
    web_context: str
    sources: list
    answer: str
    _search_query: str
    _tool_name: str
    _tool_args: dict
    tool_result: str


class ServiceNowRAGAgent:
    """LangGraph agent: decide -> (web_search?) -> retrieve -> generate.

    Uses a text-decision router instead of native tool-calling because
    Nova Lite via Bedrock Converse does not support tool use.
    """

    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id.replace('bedrock/', ''),
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.7, "max_tokens": 1024}
        )
        self.graph = self._build_graph()

    @staticmethod
    def _get_db(config) -> Optional[Session]:
        if config is None:
            return None
        return config.get("configurable", {}).get("db")

    def _decide(self, state: AgentState, config=None) -> dict:
        """Router node: pick SKIP, a web search, or a registered tool call."""
        template = """You are routing a question for an agent. Available tools:

{tools}

Question: {question}

Reply with EXACTLY one line, one of:
SEARCH: <short google search query>   (if current/external web info is needed)
TOOL: <tool_name> :: <key=value, key=value>   (if a registered tool should run, e.g. TOOL: servicenow_open_incidents :: limit=10)
SKIP   (if the internal incident context alone is enough)"""
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        response = chain.invoke({
            "tools": registry.to_prompt_block(),
            "question": state["query"],
        })
        decision = (response.content or "").strip().splitlines()[0].strip() if response.content else "SKIP"

        if decision.upper().startswith("SEARCH:"):
            search_query = decision.split(":", 1)[1].strip() or state["query"]
            return {"web_context": "", "messages": [AIMessage(content=decision)],
                    "_search_query": search_query, "_tool_name": "", "_tool_args": {}}
        if decision.upper().startswith("TOOL:"):
            try:
                rest = decision.split(":", 1)[1].strip()
                name, _, args_str = rest.partition("::")
                args = {}
                for pair in args_str.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        args[k.strip()] = v.strip()
                return {"web_context": "", "messages": [AIMessage(content=decision)],
                        "_search_query": "", "_tool_name": name.strip(), "_tool_args": args}
            except Exception:
                pass
        return {"web_context": "", "messages": [], "_search_query": "", "_tool_name": "", "_tool_args": {}}

    def _tool_call(self, state: AgentState) -> dict:
        name = state.get("_tool_name", "")
        args = state.get("_tool_args", {}) or {}
        try:
            result = registry.run(name, **args)
            return {"tool_result": str(result), "messages": [AIMessage(content=f"{name}({args})")]}
        except Exception as e:
            return {"tool_result": f"[tool {name} failed: {e}]", "messages": []}

    def _web_search(self, state: AgentState) -> dict:
        search_query = state.get("_search_query") or state["query"]
        try:
            context = registry.run("web_search", query=search_query, num_results=5)
            return {"web_context": context, "messages": [AIMessage(content=f"web_search({search_query})")]}
        except Exception as e:
            return {"web_context": f"[web search unavailable: {e}]", "messages": []}

    def _retrieve_context(self, state: AgentState, config=None) -> dict:
        db = self._get_db(config)
        if db is None:
            return {"context": "", "sources": []}
        try:
            similar_incidents = rag_service.search_similar(db, state["query"])
        except Exception as e:
            return {"context": f"[vector retrieval unavailable: {e}]", "sources": []}

        context = "\n\n".join([
            f"Incident: {inc.incident_number}\n"
            f"Description: {inc.short_description}\n"
            f"Details: {inc.description}\n"
            f"Resolution: {inc.resolution_notes or 'N/A'}"
            for inc in similar_incidents
        ])
        sources = [
            {"incident_number": inc.incident_number, "short_description": inc.short_description, "category": inc.category}
            for inc in similar_incidents
        ]
        return {"context": context, "sources": sources}

    def _generate_answer(self, state: AgentState) -> dict:
        template = """You are an intelligent ServiceNow incidents agent. Answer using the context below.

Internal incident history:
{context}

Tool output (servicenow / other tools, may be empty):
{tool_result}

Web search results (may be empty):
{web_context}

User Question: {question}

Provide a clear, actionable answer. Cite incident numbers from internal history when relevant.
If web results are used, mention that as external reference."""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        response = chain.invoke({
            "context": state.get("context", ""),
            "tool_result": state.get("tool_result", ""),
            "web_context": state.get("web_context", ""),
            "question": state["query"],
        })
        return {"answer": response.content, "messages": [AIMessage(content=response.content)]}

    def _route_after_decide(self, state: AgentState) -> str:
        if state.get("_tool_name"):
            return "tool_call"
        if state.get("_search_query"):
            return "web_search"
        return "retrieve"

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("decide", self._decide)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("tool_call", self._tool_call)
        workflow.add_node("retrieve", self._retrieve_context)
        workflow.add_node("generate", self._generate_answer)

        workflow.add_edge(START, "decide")
        workflow.add_conditional_edges(
            "decide",
            self._route_after_decide,
            {"web_search": "web_search", "tool_call": "tool_call", "retrieve": "retrieve"},
        )
        workflow.add_edge("web_search", "retrieve")
        workflow.add_edge("tool_call", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        return workflow.compile()

    def run(self, query: str, db: Session):
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "context": "",
            "web_context": "",
            "sources": [],
            "answer": "",
            "_search_query": "",
            "_tool_name": "",
            "_tool_args": {},
            "tool_result": "",
        }
        result = self.graph.invoke(initial_state, {"configurable": {"db": db}})
        return {"answer": result["answer"], "sources": result.get("sources", [])}


rag_agent = ServiceNowRAGAgent()
