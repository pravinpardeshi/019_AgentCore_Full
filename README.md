# ServiceNow Incidents RAG — Agentic AI on AWS AgentCore

An agentic RAG application built with **LangGraph** + **FastAPI**, deployed to **AWS AgentCore Runtime**. A modern HTML/CSS/JavaScript UI (Google Inter font, dark/light themes, ChatGPT-style chat, Datadog-style dashboard) talks to an agent backend that answers questions from ServiceNow incident history using PostgreSQL + pgvector on AWS RDS, Amazon Nova Lite, and reusable tools (Google Serper web search, ServiceNow Table API).

## Architecture

| Layer | Technology |
|-------|-----------|
| UI | HTML/CSS/JS (Inter font), dark/light theme, collapsible sidenav — served locally |
| Backend | FastAPI, AgentCore-compatible endpoints (`/ping`, `/invocations`) |
| Agent | LangGraph multi-node agent (`decide → web_search \| tool_call → retrieve → generate`) |
| LLM | AWS Bedrock — `bedrock/us.amazon.nova-lite-v1:0` (Nova Lite) |
| Embeddings | AWS Bedrock — `amazon.titan-embed-text-v2:0` (1024 dims) |
| Vector DB | PostgreSQL + pgvector on AWS RDS |
| Tools | Google Serper search, ServiceNow Table API (registry-based, reusable) |
| Data source | ServiceNow — `https://dev389543.service-now.com/` |

### Agent graph (LangGraph)

```
START → decide ──┬─ "SEARCH: …"   → web_search ──┐
                 ├─ "TOOL: name :: k=v" → tool_call ┤→ retrieve → generate → END
                 └─ "SKIP"          → retrieve ────┘
```

- **decide** — LLM text-router (Nova Lite via Converse does not support native tool use, so routing is done with plain-text decisions instead of tool-calling)
- **web_search** — runs the Serper tool from the registry
- **tool_call** — runs any registered tool by name (e.g. ServiceNow open incidents)
- **retrieve** — pgvector similarity search over the `incidents` table
- **generate** — final answer combining incident history + tool output + web results

## Project Structure

```
033_AgentCore_LangGraph/
├── config/config.py            # pydantic-settings, reads .env
├── src/
│   ├── main.py                 # FastAPI app: /, /chat, /dashboard, /ping, /invocations, /config
│   ├── agent/rag_agent.py      # LangGraph agent
│   ├── api/                    # routes, agent_routes (records metrics), metrics (monitoring API)
│   ├── db/connection.py        # SQLAlchemy + Secrets Manager ARN support
│   ├── models/incident.py      # incidents table (embedding VECTOR(1024))
│   ├── services/               # embeddings (Titan v2), rag (pgvector + Bedrock)
│   └── tools/                  # REUSABLE TOOLS
│       ├── registry.py         # ToolRegistry — register/run/list tools
│       ├── serper_search.py    # Google Serper web search
│       └── servicenow_api.py   # ServiceNow Table API
├── templates/                  # index.html (dashboard landing), chatgpt_style.html
├── static/                     # sidenav/chat/dashboard css+js, favicon
├── scripts/                    # init_db.py, ingest_servicenow.py
├── runtime.py / agentcore_app.py / src/runtime_entrypoint.py  # AgentCore entry points (@app.entrypoint)
├── AWS_SECRETS_MANAGER_SETUP.txt   # Secrets Manager step-by-step
├── AGENTCORE_DEPLOYMENT.txt        # Deployment guide (no Docker / no CDK)
├── test_api.py / test_local.py     # Local tests
└── requirements.txt / .env.example
```

## UI Pages (Single-Page App)

Everything runs at **`/`** — the sidenav switches views client-side so the URL never changes to `/chat` or `/dashboard` (`/chat` and `/dashboard` redirect to `/` for old links; `/#chat` deep links work too):

| View | Content |
|------|---------|
| Dashboard (landing) | Metrics cards, request/token charts, recent invocations, agent config |
| Chat | ChatGPT-style chat — suggestion cards, typing indicator, New chat in topbar |
| Monitoring | Live `/health` + `/ping` checks with latency, KPIs, latency/token charts, 50-row invocation log |

- **Collapsible sidenav** (state persisted in localStorage), **dark/light theme toggle** (persisted, charts recolor), **favicon**
- **Refresh button** pulls live data from `/api/monitor/metrics` and `/api/monitor/invocations`; spin animation while loading
- Every `/agent/query` call is recorded (status, tokens, latency) so the dashboard shows real usage

## Setup

### 1. Environment & dependencies
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in values
```

### 2. `.env` entries

| Variable | Purpose |
|----------|---------|
| `AWS_REGION` | AWS region for Bedrock |
| `BEDROCK_MODEL_ID` | default `bedrock/us.amazon.nova-lite-v1:0` |
| `EMBEDDING_MODEL_ID` | default `amazon.titan-embed-text-v2:0` |
| `DATABASE_URL` | direct `postgresql://…` **or** Secrets Manager ARN (see below) |
| `SERVICENOW_URL` | `https://dev389543.service-now.com/` |
| `SERVICENOW_USER` / `SERVICENOW_PASSWORD` | ServiceNow API basic auth |
| `SERVICENOW_TOKEN` | OAuth bearer token (optional, overrides basic auth) |
| `SERPER_API_KEY` | Google Serper key (google.serper.dev) for web search tool |
| `AGENTCORE_RUNTIME_ARN` / `AGENTCORE_ENDPOINT_URL` | optional: UI can call AgentCore directly |

### 3. Database
```bash
python scripts/init_db.py       # creates vector extension + incidents table
```
Table: **`incidents`** — columns include `incident_number`, `short_description`, `description`, `resolution_notes`, `incident_metadata`, and `embedding VECTOR(1024)`.

### 4. Ingest ServiceNow data
```bash
python scripts/ingest_servicenow.py
```

### 5. Run locally
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```
Open http://localhost:8080 — tests: `python test_api.py`, `python test_local.py`.

## Reusable Tools

Register once, use anywhere (`src/tools/registry.py`):

```python
from src.tools.registry import registry

registry.list_tools()                                  # discover
registry.run("web_search", query="AWS Bedrock quotas") # execute
registry.to_prompt_block()                             # describe for prompts
```

| Tool | Source | Inputs |
|------|--------|--------|
| `web_search` | Google Serper | `query`, `num_results` |
| `servicenow_open_incidents` | ServiceNow Table API (`incident`, active=true) | `limit`, `query` (encoded query) |
| `servicenow_change_records` | ServiceNow Table API (`change_request`, active=true) | `limit`, `query` |
| `servicenow_user_email` | ServiceNow Table API (`sys_user`) | `name` (partial name/username → returns **email id**) |

Direct usage:
```python
from src.tools.serper_search import serper_search
serper_search.search("python 3.13 release", num_results=5)

from src.tools.servicenow_api import servicenow
servicenow.get_open_incidents(limit=10)
servicenow.get_change_records(limit=5)
servicenow.get_user_email("John Smith")
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ping` | GET | AgentCore health check (`{"status":"Healthy"}`) |
| `/invocations` | POST | AgentCore invocation (`{question\|input\|inputText}` → answer + sources) |
| `/health` | GET | Health |
| `/config` | GET | AgentCore endpoint config for UI |
| `/agent/query` | POST | Chat endpoint (records metrics) |
| `/api/query` | POST | Direct RAG endpoint |
| `/api/monitor/metrics` | GET | Requests, tokens, latency, error rate, sessions |
| `/api/monitor/invocations` | GET | Recent invocation log |

### AgentCore entry points (all use `@app.entrypoint`)
- `runtime.py` (recommended), `agentcore_app.py`, `src/runtime_entrypoint.py`

## PostgreSQL via AWS Secrets Manager

Set the secret ARN directly in `.env` — credentials are fetched automatically:

```bash
DATABASE_URL=arn:aws:secretsmanager:us-east-1:123456789012:secret:my-rds-secret-abc123
```

Secret JSON (standard RDS format):
```json
{
  "username": "postgres",
  "password": "…",
  "engine": "postgres",
  "host": "xxx.us-east-1.rds.amazonaws.com",
  "port": 5432,
  "dbname": "incidents_db"
}
```

IAM: execution role needs `secretsmanager:GetSecretValue` on the secret + `bedrock:InvokeModel`. Full steps in **`AWS_SECRETS_MANAGER_SETUP.txt`**.

## Deployment to AWS AgentCore (no Docker, no CDK)

Full guide in **`AGENTCORE_DEPLOYMENT.txt`** — three options:
1. **AgentCore CLI** — `agentcore init` → `configure` → `deploy`
2. **AWS Console** — create Runtime (HTTP protocol, port 8080, health `/ping`, entry point `runtime.py`), upload zipped source
3. **AWS CLI** — `bedrock-agentcore-control create-agent-runtime` + `create-agent-runtime-endpoint`

Verify:
```bash
curl https://<endpoint>/ping
curl -X POST https://<endpoint>/invocations -H "Content-Type: application/json" -d '{"question":"common network issues"}'
```
