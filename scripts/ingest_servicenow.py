#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from src.db.connection import SessionLocal
from src.models.incident import Incident
from src.services.embeddings import embedding_service
from datetime import datetime

def fetch_servicenow_incidents():
    """
    Fetch incidents from ServiceNow
    Note: This may require authentication depending on instance settings
    """
    url = "https://dev389543.service-now.com/api/now/table/incident"
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = httpx.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get('result', [])
        else:
            print(f"Error: {response.status_code}")
            # Try scraping the UI if API is not accessible
            return scrape_servicenow_ui()
    except Exception as e:
        print(f"Error fetching from API: {e}")
        return scrape_servicenow_ui()

def scrape_servicenow_ui():
    try:
        url = "https://dev389543.service-now.com/incident_list.do"
        response = httpx.get(url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        # This is a basic scraper - may need adjustment based on actual page structure
        print("Scraping UI - may need authentication")
        return []
    except Exception as e:
        print(f"Error scraping: {e}")
        return []

def ingest_incidents(incidents_data):
    db = SessionLocal()
    try:
        for item in incidents_data:
            incident_number = item.get('number') or item.get('incident_number')
            if not incident_number:
                continue
            
            # Check if exists
            existing = db.query(Incident).filter(Incident.incident_number == incident_number).first()
            if existing:
                continue
            
            short_desc = item.get('short_description', '')
            description = item.get('description', '')
            resolution = item.get('close_notes') or item.get('resolution_notes', '')
            
            # Create text for embedding
            embed_text = f"{short_desc} {description} {resolution}"
            
            try:
                embedding = embedding_service.get_embedding(embed_text)
            except Exception as e:
                print(f"Error getting embedding for {incident_number}: {e}")
                continue
            
            incident = Incident(
                incident_number=incident_number,
                short_description=short_desc,
                description=description,
                category=item.get('category', ''),
                priority=item.get('priority', ''),
                state=item.get('state', ''),
                assigned_to=item.get('assigned_to', ''),
                resolution_notes=resolution,
                incident_metadata=item,
                embedding=embedding
            )
            db.add(incident)
            print(f"Ingested {incident_number}")
        
        db.commit()
        print("Ingestion complete!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    print("Fetching incidents from ServiceNow...")
    incidents = fetch_servicenow_incidents()
    if incidents:
        print(f"Found {len(incidents)} incidents")
        ingest_incidents(incidents)
    else:
        print("No incidents found. You may need to authenticate to the ServiceNow instance.")

if __name__ == "__main__":
    main()
