from fastapi import APIRouter, HTTPException
from src.services.rag import rag_service
from src.api.metrics import record_invocation, estimate_tokens
from src.api import agentcore_proxy
from pydantic import BaseModel
import time

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list

@router.post("/query", response_model=QueryResponse)
async def query_incidents(request: QueryRequest):
    if agentcore_proxy.enabled():
        return await agentcore_proxy.query(request.question)

    from src.db.connection import SessionLocal
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not configured")
    db = SessionLocal()
    try:
        start = time.time()
        result = rag_service.generate_answer(db, request.question)
        latency = time.time() - start
        usage = result.get("usage") or {}
        in_tok = usage.get("input_tokens") or estimate_tokens(request.question)
        out_tok = usage.get("output_tokens") or estimate_tokens(result.get("answer", ""))
        record_invocation("success", request.question, in_tok, latency, out_tok)
        return {"answer": result["answer"], "sources": result["sources"]}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        db.close()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
