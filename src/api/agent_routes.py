from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.connection import get_db
from src.agent.rag_agent import rag_agent
from pydantic import BaseModel

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: list

@router.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        result = rag_agent.run(request.question, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
