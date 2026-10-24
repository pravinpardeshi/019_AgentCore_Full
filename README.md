# ServiceNow Incidents RAG with AWS AgentCore

A FastAPI-based RAG application that uses AWS Bedrock (Nova Lite for chat, Titan Embed v2 for embeddings) and PostgreSQL with pgvector to answer questions about ServiceNow incidents. The backend is designed to be deployed on AWS AgentCore, with a local HTML/CSS/JS frontend.

## Architecture

- **Frontend**: HTML, CSS (Inter font), JavaScript - runs locally
- **Backend**: FastAPI - designed for AWS AgentCore Runtime (HTTP protocol)
- **LLM**: AWS Bedrock - `bedrock/ca.amazon.nova-lite-v1:0` (Nova Lite)
- **Embeddings**: AWS Bedrock - `amazon.titan-embed-text-v2:0` (1024 dimensions)
- **Vector DB**: PostgreSQL with pgvector extension on AWS RDS
- **Data Source**: ServiceNow Incidents from https://dev389543.service-now.com/

## Setup

### 1. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

Required:
- `DATABASE_URL`: PostgreSQL connection string with pgvector enabled
- AWS credentials configured (via AWS CLI or IAM role)
- ServiceNow access if scraping data

### 3. Initialize database
```bash
python scripts/init_db.py
```

### 4. Ingest ServiceNow incidents
```bash
python scripts/ingest_servicenow.py
```

### 5. Run locally
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

Open http://localhost:8080 in your browser.

## AWS AgentCore Deployment

The app is configured for AgentCore Runtime with HTTP protocol (port 8080, `/health` endpoint).

### Without Docker/CDK (as requested)

Use AWS CLI or AgentCore CLI if available. The app follows the AgentCore HTTP contract:
- Health check: `GET /health`
- Invocations: Can be accessed via FastAPI routes

Note: Since Docker and CDK are not available, you can deploy using:
1. AWS App Runner (alternative)
2. AWS Lambda with API Gateway (if adapted)
3. Manual deployment via AWS Console
4. AgentCore CLI with source deployment if supported

## Project Structure

```
033_AgentCore_LangGraph/
├── config/           # Configuration
├── src/              # Application source
│   ├── api/          # API routes
│   ├── core/         # Core utilities
│   ├── db/           # Database connection
│   ├── models/       # SQLAlchemy models
│   └── services/     # Business logic (RAG, embeddings)
├── static/           # CSS, JS
├── templates/        # HTML templates
├── scripts/          # Utility scripts
└── requirements.txt
```

## Using PostgreSQL with Secrets Manager

If your RDS credentials are in AWS Secrets Manager, you can use the secret ARN in your `.env`:

```bash
DATABASE_URL=arn:aws:secretsmanager:us-east-1:123456789012:secret:my-rds-secret-abc123
```

The code will automatically fetch credentials from Secrets Manager.
