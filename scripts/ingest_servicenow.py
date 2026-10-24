import os
import sys
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.db.connection import Base
from src.models.incident import Incident
from src.services.embeddings import embedding_service
from src.tools.servicenow_api import ServiceNowTool
from config.config import settings

def ingest_servicenow_incidents(limit: int = 100):
    # 1. Setup DB connection
    db_url = settings.database_url
    if not db_url:
        print("❌ Error: DATABASE_URL not configured in .env")
        return

    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        print(f"✅ Connected to RDS database.")

        # 2. Fetch raw data from ServiceNow
        print(f"==> Fetching up to {limit} incidents from ServiceNow...")
        sn = ServiceNowTool()
        # We use _get directly to get raw JSON result instead of the formatted string
        params = {
            "sysparm_query": "active=true^ORDERBYDESCsys_created_on",
            "sysparm_limit": limit,
            "sysparm_fields": "number,short_description,description,state,priority,category,assigned_to,opened_at,closed_at,resolution_notes",
        }
        data = sn._get("/api/now/table/incident", params)
        records = data.get("result", [])
        
        if not records:
            print("⚠️ No incidents found in ServiceNow.")
            return

        print(f"Found {len(records)} records. Generating embeddings and inserting...")

        # 3. Process and Insert
        count = 0
        for rec in records:
            num = rec.get("number")
            # Combine fields for a rich embedding
            text_to_embed = f"Incident {num}: {rec.get('short_description', '')}\nDetails: {rec.get('description', '')}"
            
            try:
                # Generate 1024-dim vector
                vector = embedding_service.get_embedding(text_to_embed)
                
                # Create DB model
                incident = Incident(
                    incident_number=num,
                    short_description=rec.get("short_description"),
                    description=rec.get("description"),
                    category=rec.get("category"),
                    priority=rec.get("priority"),
                    state=rec.get("state"),
                    assigned_to=rec.get("assigned_to"),
                    opened_at=rec.get("opened_at"),
                    closed_at=rec.get("closed_at"),
                    resolution_notes=rec.get("resolution_notes"),
                    embedding=vector
                )
                session.add(incident)
                count += 1
                if count % 10 == 0:
                    print(f"Processed {count}/{len(records)}...")
            except Exception as e:
                print(f"Skipping incident {num} due to error: {e}")

        session.commit()
        print(f"✅ Successfully ingested {count} incidents into RDS!")

    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    # You can change the limit here to fetch more data
    ingest_servicenow_incidents(limit=50)
