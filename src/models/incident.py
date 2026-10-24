from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from pgvector.sqlalchemy import Vector
from src.db.connection import Base
from datetime import datetime

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_number = Column(String, unique=True, index=True)
    short_description = Column(Text)
    description = Column(Text)
    category = Column(String)
    priority = Column(String)
    state = Column(String)
    assigned_to = Column(String)
    opened_at = Column(DateTime)
    closed_at = Column(DateTime)
    resolution_notes = Column(Text)
    incident_metadata = Column(JSON)
    embedding = Column(Vector(1024))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
