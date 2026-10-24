from bedrock_agentcore.runtime import BedrockAgentCoreApp
from src.agent.rag_agent import rag_agent
from src.db.connection import SessionLocal

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(event, context):
    try:
        payload = event if isinstance(event, dict) else {}
        question = payload.get("inputText") or payload.get("question") or payload.get("input") or payload.get("prompt") or ""
        db = SessionLocal()
        try:
            result = rag_agent.run(question, db)
            return {"output": result["answer"], "sources": result["sources"]}
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    app.run()
