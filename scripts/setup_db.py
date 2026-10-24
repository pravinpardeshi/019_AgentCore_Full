import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.db.connection import Base
from src.models.incident import Incident
from src.services.embeddings import embedding_service
from config.config import settings

def setup_rds_database():
    # Use settings.database_url which already handles .env loading via pydantic-settings
    db_url = settings.database_url
    if not db_url:
        print("❌ Error: DATABASE_URL not configured in .env or environment variables.")
        return

    print(f"Connecting to database at: {db_url.split('@')[-1] if '@' in db_url else 'specified endpoint'}...")
    
    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        
        with engine.connect() as conn:
            # 2. Enable pgvector
            print("==> Enabling pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            
            # 3. Create tables using SQLAlchemy Base
            print("==> Creating incidents table...")
            Base.metadata.create_all(engine)
            
        print("✅ Database schema initialized successfully!")

    except Exception as e:
        print(f"❌ Database setup failed: {e}")

if __name__ == "__main__":
    setup_rds_database()
