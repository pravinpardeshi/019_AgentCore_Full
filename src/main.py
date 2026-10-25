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

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.mount("/static", StaticFiles(directory=os.path.join(_BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(_BASE_DIR, "templates"))

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
        "api_base": settings.ui_api_base or "",
    })


@app.get("/dashboard")
async def dashboard(request: Request):
    from config.config import settings
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "monitoring",
        "agentcore_endpoint": settings.agentcore_runtime_arn or "",
        "use_agentcore": "true" if settings.agentcore_runtime_arn else "false",
        "api_base": settings.ui_api_base or "",
    })


@app.get("/chat")
async def chat_page(request: Request):
    from config.config import settings
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "active_page": "chat",
        "agentcore_endpoint": settings.agentcore_runtime_arn or "",
        "use_agentcore": "true" if settings.agentcore_runtime_arn else "false",
        "api_base": settings.ui_api_base or "",
    })


@app.get("/health")
async def health():
    from src.api import agentcore_proxy
    if agentcore_proxy.enabled():
        return await agentcore_proxy.remote_health()
    return {"status": "healthy"}


@app.get("/ping")
async def ping():
    from src.api import agentcore_proxy
    if agentcore_proxy.enabled():
        return await agentcore_proxy.remote_health()
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
    import time as _time
    from src.api.metrics import record_invocation, estimate_tokens
    start = _time.time()
    try:
        body = await request.json()
        question = body.get("inputText") or body.get("question") or body.get("input") or body.get("prompt") or body.get("query") or ""

        from src.db.connection import SessionLocal
        if SessionLocal is None:
            return {"error": "Database connection not established. Please check DATABASE_URL or Secrets Manager permissions."}

        from src.agent.rag_agent import rag_agent

        db = SessionLocal()
        try:
            result = rag_agent.run(question, db)
            latency = _time.time() - start
            usage = result.get("usage") or {}
            in_tok = usage.get("input_tokens") or estimate_tokens(question)
            out_tok = usage.get("output_tokens") or estimate_tokens(result["answer"])
            record_invocation("success", question, in_tok, latency, out_tok)
            return {"response": result["answer"], "sources": result["sources"],
                    "usage": result.get("usage", {"input_tokens": in_tok, "output_tokens": out_tok})}
        finally:
            db.close()
    except Exception as e:
        latency = _time.time() - start
        try:
            record_invocation("error", locals().get("question", ""), 0, latency, 0)
        except Exception:
            pass
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
