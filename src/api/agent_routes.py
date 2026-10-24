from fastapi import APIRouter, HTTPException
from src.agent.rag_agent import rag_agent
from src.api.metrics import metrics_store, record_invocation, estimate_tokens
from pydantic import BaseModel
import time

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list

@router.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    from src.api import agentcore_proxy
    if agentcore_proxy.enabled():
        return await agentcore_proxy.query(request.question)

    from src.db.connection import SessionLocal
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not configured")
    db = SessionLocal()
    start = time.time()
    try:
        result = rag_agent.run(request.question, db)
        latency = time.time() - start
        answer = result["answer"]
        usage = result.get("usage") or {}
        in_tok = usage.get("input_tokens") or estimate_tokens(request.question)
        out_tok = usage.get("output_tokens") or estimate_tokens(answer)
        record_invocation("success", request.question, in_tok, latency, out_tok)
        return {"answer": result["answer"], "sources": result.get("sources", [])}
    except HTTPException:
        raise
    except Exception as e:
        record_invocation("error", request.question, 0, time.time() - start, 0)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
