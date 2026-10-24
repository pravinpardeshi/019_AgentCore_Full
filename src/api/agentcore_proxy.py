"""Server-side proxy for split topology: local UI host -> AgentCore runtime.

The AgentCore gateway only routes POST /invocations and GET /ping (other
paths return 404), so the browser must never call the endpoint directly.
All browser calls stay same-origin and are forwarded here server-side;
invocations are recorded locally so dashboard/monitoring show real data.
"""
import time
import httpx
from fastapi import HTTPException
from config.config import settings
from src.api.metrics import record_invocation, estimate_tokens


def enabled() -> bool:
    return bool(settings.use_agentcore and settings.agentcore_endpoint_url)


def _url(path: str) -> str:
    return settings.agentcore_endpoint_url.rstrip("/") + path


async def query(question: str) -> dict:
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                _url("/invocations"),
                json={"inputText": question, "question": question},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json() or {}
        latency = time.time() - start
        if data.get("error"):
            raise RuntimeError(data["error"])
        answer = data.get("response") or data.get("answer") or ""
        usage = data.get("usage") or {}
        in_tok = usage.get("input_tokens") or estimate_tokens(question)
        out_tok = usage.get("output_tokens") or estimate_tokens(answer)
        record_invocation("success", question, in_tok, latency, out_tok)
        return {"answer": answer, "sources": data.get("sources", [])}
    except Exception as e:
        try:
            record_invocation("error", question, 0, time.time() - start, 0)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"AgentCore invoke failed: {e}")


async def remote_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_url("/ping"))
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AgentCore health check failed: {e}")
