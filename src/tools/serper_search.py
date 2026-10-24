"""Reusable Google Serper search tool.

Usage:
    from src.tools.serper_search import serper_search
    results = serper_search("site outages today", num_results=5)

Or as a class with its own API key / timeout:
    from src.tools.serper_search import SerperSearchTool
    tool = SerperSearchTool(api_key="...", timeout=10)
    results = tool.search("python asyncio", num_results=5)
"""
import os
import httpx
from typing import Optional

SERPER_ENDPOINT = "https://google.serper.dev/search"


class SerperSearchTool:
    """Search Google via the Serper.dev API and return normalized results."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self._api_key = api_key
        self.timeout = timeout

    @property
    def api_key(self) -> str:
        if self._api_key:
            return self._api_key
        key = os.getenv("SERPER_API_KEY", "")
        if not key:
            try:
                from config.config import settings
                key = settings.serper_api_key
            except Exception:
                pass
        return key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """Run a search. Returns a list of {title, link, snippet} dicts."""
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY is not set")
        if not query or not query.strip():
            return []

        payload = {"q": query.strip(), "num": max(1, min(num_results, 20))}
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(SERPER_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position"),
            })

        answer_box = data.get("answerBox") or {}
        if answer_box.get("answer") or answer_box.get("snippet"):
            results.insert(0, {
                "title": answer_box.get("title", "Answer box"),
                "link": answer_box.get("link", ""),
                "snippet": answer_box.get("answer") or answer_box.get("snippet", ""),
                "position": 0,
            })
        return results

    def search_as_context(self, query: str, num_results: int = 5) -> str:
        """Search and format results as text for LLM prompt context."""
        results = self.search(query, num_results)
        if not results:
            return f"No web results found for: {query}"
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n   {r['link']}\n   {r['snippet']}")
        return "\n".join(lines)


# Module-level default instance (reads SERPER_API_KEY from environment/.env)
serper_search = SerperSearchTool()
