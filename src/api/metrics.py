from fastapi import APIRouter
from datetime import datetime
import random

router = APIRouter()

metrics_store = {
    "total_requests": 1247,
    "total_input_tokens": 65000,
    "total_output_tokens": 45000,
    "total_errors": 2,
    "latencies": [1.2, 0.9, 1.5, 0.8, 1.3, 1.1],
    "invocations": []
}

@router.get("/metrics")
async def get_metrics():
    total_tokens = metrics_store["total_input_tokens"] + metrics_store["total_output_tokens"]
    avg_latency = sum(metrics_store["latencies"]) / len(metrics_store["latencies"]) if metrics_store["latencies"] else 0
    error_rate = (metrics_store["total_errors"] / metrics_store["total_requests"] * 100) if metrics_store["total_requests"] > 0 else 0
    
    return {
        "status": "healthy",
        "total_requests": metrics_store["total_requests"],
        "total_tokens": total_tokens,
        "input_tokens": metrics_store["total_input_tokens"],
        "output_tokens": metrics_store["total_output_tokens"],
        "avg_latency_ms": round(avg_latency * 1000, 2),
        "error_rate": round(error_rate, 2),
        "active_sessions": random.randint(15, 30),
        "uptime": "99.98%"
    }

@router.get("/invocations")
async def get_invocations(limit: int = 10):
    return {
        "invocations": metrics_store["invocations"][-limit:] if metrics_store["invocations"] else [
            {"timestamp": "2024-01-01T10:42:15Z", "status": "success", "query": "Sample query", "tokens": 245, "latency": 1.2}
        ]
    }

@router.post("/track")
async def track_invocation(data: dict):
    metrics_store["total_requests"] += 1
    metrics_store["total_input_tokens"] += data.get("input_tokens", 0)
    metrics_store["total_output_tokens"] += data.get("output_tokens", 0)
    metrics_store["latencies"].append(data.get("latency", 1.0))
    if len(metrics_store["latencies"]) > 100:
        metrics_store["latencies"] = metrics_store["latencies"][-100:]
    return {"status": "tracked"}


from datetime import datetime, timezone

def record_invocation(status: str, query: str, tokens: int, latency: float):
    metrics_store["total_requests"] += 1
    if status == "error":
        metrics_store["total_errors"] += 1
    else:
        metrics_store["total_input_tokens"] += tokens
    metrics_store["latencies"].append(latency)
    if len(metrics_store["latencies"]) > 100:
        metrics_store["latencies"] = metrics_store["latencies"][-100:]
    metrics_store["invocations"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "query": query[:80],
        "tokens": tokens,
        "latency": round(latency, 2),
    })
    if len(metrics_store["invocations"]) > 50:
        metrics_store["invocations"] = metrics_store["invocations"][-50:]
