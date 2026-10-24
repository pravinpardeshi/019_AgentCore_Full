#!/usr/bin/env python3
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    print(response.status_code, response.json())
    assert response.status_code == 200

def test_ping():
    response = client.get("/ping")
    print(response.status_code, response.json())
    assert response.status_code == 200

def test_invocations():
    response = client.post("/invocations", json={"question": "test"})
    print(response.status_code)

if __name__ == "__main__":
    test_health()
    test_ping()
    test_invocations()
