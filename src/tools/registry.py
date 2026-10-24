"""Tool registry — register tools once, reuse across agents/runtimes.

    from src.tools.registry import registry
    from src.tools.serper_search import serper_search

    registry.register(
        name="web_search",
        description="Search Google for current/external information",
        fn=serper_search.search_as_context,
        input_keys=["query"],
    )
    output = registry.run("web_search", query="aws bedrock quotas")
"""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    fn: Callable[..., Any]
    input_keys: list = field(default_factory=list)

    def run(self, **kwargs) -> Any:
        return self.fn(**kwargs)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, description: str, fn: Callable, input_keys: list | None = None) -> ToolSpec:
        spec = ToolSpec(name=name, description=description, fn=fn, input_keys=input_keys or [])
        self._tools[name] = spec
        return spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}. Available: {list(self._tools)}")
        return self._tools[name]

    def run(self, name: str, **kwargs) -> Any:
        return self.get(name).run(**kwargs)

    def list_tools(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "inputs": t.input_keys} for t in self._tools.values()]

    def to_prompt_block(self) -> str:
        """Describe available tools for an LLM system prompt (no native tool-calling needed)."""
        if not self._tools:
            return ""
        lines = ["Available tools (decide if one would improve your answer):"]
        for t in self._tools.values():
            lines.append(f"- {t.name}: {t.description} (inputs: {', '.join(t.input_keys)})")
        return "\n".join(lines)


registry = ToolRegistry()

# Register the Serper search tool by default
from src.tools.serper_search import serper_search

registry.register(
    name="web_search",
    description="Search Google via Serper for current/external info not in the incident knowledge base",
    fn=serper_search.search_as_context,
    input_keys=["query", "num_results"],
)

# ServiceNow API tools
from src.tools.servicenow_api import servicenow

registry.register(
    name="servicenow_open_incidents",
    description="Get open (active) incidents from ServiceNow. input: limit (int, optional), query (encoded query, optional)",
    fn=lambda limit=10, query="": servicenow.get_open_incidents(int(limit), str(query)),
    input_keys=["limit", "query"],
)

registry.register(
    name="servicenow_change_records",
    description="Get open change records from ServiceNow. input: limit (int, optional), query (encoded query, optional)",
    fn=lambda limit=10, query="": servicenow.get_change_records(int(limit), str(query)),
    input_keys=["limit", "query"],
)

registry.register(
    name="servicenow_user_email",
    description="Look up a user's email id in ServiceNow by name or username. input: name (str, required)",
    fn=lambda name="": servicenow.get_user_email(str(name)),
    input_keys=["name"],
)
