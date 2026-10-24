from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.config import settings
import boto3
import json

Base = declarative_base()

def get_database_url():
    db_url = settings.database_url
    # If using Secrets Manager ARN
    if db_url.startswith('arn:aws:secretsmanager'):
        try:
            client = boto3.client('secretsmanager', region_name=settings.aws_region)
            response = client.get_secret_value(SecretId=db_url)
            secret = json.loads(response['SecretString'])
            # Handle different secret formats
            if 'engine' in secret and secret['engine'] == 'postgres':
                host = secret.get('host')
                port = secret.get('port', 5432)
                username = secret.get('username')
                password = secret.get('password')
                dbname = secret.get('dbname') or secret.get('database')
                return f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
            elif 'username' in secret:
                return secret.get('connectionString') or secret.get('url')
        except Exception as e:
            print(f"Error fetching secret: {e}")
            raise
    return db_url

try:
    engine = create_engine(get_database_url(), pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"DB connection setup failed: {e}")
    engine = None
    SessionLocal = None

def get_db():
    if not SessionLocal:
        raise Exception("Database not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    if not engine:
        raise Exception("Database not configured")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
