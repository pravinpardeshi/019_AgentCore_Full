from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "bedrock/ca.amazon.nova-lite-v1:0")
    embedding_model_id: str = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    database_url: str = os.getenv("DATABASE_URL", "")
    servicenow_url: str = os.getenv("SERVICENOW_URL", "https://dev389543.service-now.com/")
    agentcore_runtime_arn: str = os.getenv("AGENTCORE_RUNTIME_ARN", "")
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
