from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from src.api.routes import router
from src.api.agent_routes import router as agent_router
from src.api.metrics import router as metrics_router
try:
    from src.db.connection import init_db
    DB_AVAILABLE = True
except Exception as e:
    print(f"DB init unavailable: {e}")
    DB_AVAILABLE = False
import os

app = FastAPI(title="ServiceNow Incidents RAG Agent", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(router, prefix="/api")
app.include_router(agent_router, prefix="/agent")
app.include_router(metrics_router, prefix="/api/monitor")


@app.on_event("startup")
async def startup_event():
    if DB_AVAILABLE:
        try:
            init_db()
        except Exception as e:
            print(f"Warning: {e}")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    from config.config import settings
    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_page": "dashboard",
        "agentcore_endpoint": settings.agentcore_runtime_arn or "",
        "use_agentcore": "true" if settings.agentcore_runtime_arn else "false",
    })


@app.get("/dashboard")
async def dashboard():
    return RedirectResponse(url="/", status_code=302)


@app.get("/chat")
async def chat_page():
    return RedirectResponse(url="/", status_code=302)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/ping")
async def ping():
    return {"status": "Healthy"}


@app.get("/config")
async def get_config():
    from config.config import settings
    return {
        "agentcore_endpoint": settings.agentcore_runtime_arn or "",
        "use_agentcore": bool(settings.agentcore_runtime_arn),
    }


@app.post("/invocations")
async def invocations(request: Request):
    try:
        body = await request.json()
        question = body.get("inputText") or body.get("question") or body.get("input") or body.get("prompt") or body.get("query") or ""

        if not DB_AVAILABLE:
            return {"error": "Database not configured"}

        from src.db.connection import SessionLocal
        from src.agent.rag_agent import rag_agent

        db = SessionLocal()
        try:
            result = rag_agent.run(question, db)
            return {"response": result["answer"], "sources": result["sources"]}
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
