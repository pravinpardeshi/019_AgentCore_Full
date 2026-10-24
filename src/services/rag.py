from sqlalchemy.orm import Session
from sqlalchemy import text
from src.models.incident import Incident
from src.services.embeddings import embedding_service
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config.config import settings
from typing import List, Dict

class RAGService:
    def __init__(self):
        self.llm = ChatBedrock(
            model_id=settings.bedrock_model_id.replace('bedrock/', ''),
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
        chain = prompt | self.llm | StrOutputParser()
        
        answer = chain.invoke({
            "context": context,
            "question": query
        })
        
        return {
            "answer": answer,
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
