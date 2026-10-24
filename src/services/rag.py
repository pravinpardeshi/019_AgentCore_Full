from sqlalchemy.orm import Session
from sqlalchemy import text
from src.models.incident import Incident
from src.services.embeddings import embedding_service
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from config.config import settings
from typing import List, Dict

def extract_usage(message) -> Dict:
    """Pull real token counts from a Bedrock AIMessage (usage_metadata or response_metadata)."""
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict):
        return {
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
        }
    meta = getattr(message, "response_metadata", None) or {}
    if isinstance(meta, dict):
        tok = meta.get("usage") or meta.get("token_usage") or {}
        if isinstance(tok, dict):
            return {
                "input_tokens": int(tok.get("input_tokens") or tok.get("prompt_tokens") or 0),
                "output_tokens": int(tok.get("output_tokens") or tok.get("completion_tokens") or 0),
            }
    return {"input_tokens": 0, "output_tokens": 0}


def merge_usage(*usages: Dict) -> Dict:
    """Sum token counts across multiple LLM calls in one agent run."""
    total = {"input_tokens": 0, "output_tokens": 0}
    for u in usages:
        if isinstance(u, dict):
            total["input_tokens"] += int(u.get("input_tokens") or 0)
            total["output_tokens"] += int(u.get("output_tokens") or 0)
    return total


class RAGService:
    def __init__(self):
        # Ensure model_id is cleaned of 'bedrock/' prefix and whitespace
        model_id = settings.bedrock_model_id.strip()
        if model_id.startswith('bedrock/'):
            model_id = model_id.replace('bedrock/', '', 1)

        self.llm = ChatBedrock(
            model_id=model_id,
            region_name=settings.aws_region,
            model_kwargs={"temperature": 0.7, "max_tokens": 1024}
        )
    
    def search_similar(self, db: Session, query: str, limit: int = 5) -> List[Incident]:
        query_embedding = embedding_service.get_embedding(query)
        # Use pgvector cosine similarity
        result = db.execute(
            text("""
                SELECT *, embedding <-> :query_embedding as distance
                FROM incidents
                ORDER BY embedding <-> :query_embedding
                LIMIT :limit
            """),
            {"query_embedding": str(query_embedding), "limit": limit}
        )
        incidents = []
        for row in result:
            incident = db.query(Incident).filter(Incident.id == row.id).first()
            if incident:
                incidents.append(incident)
        return incidents
    
    def generate_answer(self, db: Session, query: str) -> Dict:
        similar_incidents = self.search_similar(db, query)
        
        context = "\n\n".join([
            f"Incident: {inc.incident_number}\n"
            f"Description: {inc.short_description}\n"
            f"Details: {inc.description}\n"
            f"Resolution: {inc.resolution_notes or 'N/A'}\n"
            f"Category: {inc.category}\n"
            f"State: {inc.state}"
            for inc in similar_incidents
        ])
        
        template = """You are a helpful ServiceNow incidents assistant. Use the following context from past incidents to answer the user's question accurately and helpfully.

Context:
{context}

Question: {question}

Answer:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        response = chain.invoke({
            "context": context,
            "question": query
        })
        answer = response.content if hasattr(response, "content") else str(response)
        usage = extract_usage(response)

        return {
            "answer": answer,
            "usage": usage,
            "sources": [
                {
                    "incident_number": inc.incident_number,
                    "short_description": inc.short_description,
                    "category": inc.category
                }
                for inc in similar_incidents
            ]
        }

rag_service = RAGService()
