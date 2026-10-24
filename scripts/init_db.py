#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import init_db, engine
from src.models.incident import Base

def main():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Initializing pgvector extension...")
    init_db()
    print("Database initialized successfully!")

if __name__ == "__main__":
    main()
