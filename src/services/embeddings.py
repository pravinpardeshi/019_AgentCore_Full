import boto3
import json
from config.config import settings
from typing import List

class EmbeddingService:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name=settings.aws_region)
        self.model_id = settings.embedding_model_id
    
    def get_embedding(self, text: str) -> List[float]:
        try:
            body = json.dumps({
                "inputText": text
            })
            response = self.bedrock.invoke_model(
                body=body,
                modelId=self.model_id,
                accept='application/json',
                contentType='application/json'
            )
            response_body = json.loads(response['body'].read())
            return response_body.get('embedding', [])
        except Exception as e:
            print(f"Error getting embedding: {e}")
            raise

embedding_service = EmbeddingService()
