#!/usr/bin/env python3
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from src.agent.rag_agent import rag_agent
from src.db.connection import SessionLocal

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context):
    try:
        question = payload.get("inputText") or payload.get("question") or payload.get("prompt") or payload.get("query") or ""
        db = SessionLocal()
        try:
            result = rag_agent.run(question, db)
            return {"response": result["answer"], "sources": result["sources"]}
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    app.run()
