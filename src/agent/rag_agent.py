from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
from sqlalchemy.orm import Session
from src.services.rag import rag_service
from config.config import settings

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    query: str
    context: str
    sources: list
    answer: str

class ServiceNowRAGAgent:
    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id.replace('bedrock/', ''),
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.7, "max_tokens": 1024}
        )
        self.graph = self._build_graph()
    
    def _retrieve_context(self, state: AgentState, db: Session):
        query = state["query"]
        similar_incidents = rag_service.search_similar(db, query)
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
    
    def _generate_answer(self, state: AgentState):
        template = """You are an intelligent ServiceNow incidents agent. Analyze the context from past incidents and provide a comprehensive answer.

Context from past incidents:
{context}

User Question: {question}

Provide a clear, actionable answer based on the incident history."""
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        response = chain.invoke({"context": state["context"], "question": state["query"]})
        return {"answer": response.content, "messages": [AIMessage(content=response.content)]}
    
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("retrieve", self._retrieve_context)
        workflow.add_node("generate", self._generate_answer)
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        return workflow.compile()
    
    def run(self, query: str, db: Session):
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "context": "",
            "sources": [],
            "answer": ""
        }
        result = self.graph.invoke(initial_state, {"configurable": {"db": db}})
        return {"answer": result["answer"], "sources": result["sources"]}

rag_agent = ServiceNowRAGAgent()
