#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test the agent
from src.agent.rag_agent import rag_agent
from src.db.connection import SessionLocal

def test_agent():
    db = SessionLocal()
    try:
        # Test query
        result = rag_agent.run("What are common network issues?", db)
        print("Answer:", result["answer"][:100] + "...")
        print("Sources:", len(result["sources"]))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_agent()
