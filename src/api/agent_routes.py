from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.connection import get_db
from src.agent.rag_agent import rag_agent
from src.api.metrics import metrics_store, record_invocation
from pydantic import BaseModel
import time

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list

@router.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest, db: Session = Depends(get_db)):
    start = time.time()
    try:
        result = rag_agent.run(request.question, db)
        latency = time.time() - start
        answer = result["answer"]
        tokens = len(request.question.split()) + len(answer.split())
        record_invocation("success", request.question, tokens, latency)
        return result
    except Exception as e:
        latency = time.time() - start
        record_invocation("error", request.question, 0, latency)
        raise HTTPException(status_code=500, detail=str(e))
