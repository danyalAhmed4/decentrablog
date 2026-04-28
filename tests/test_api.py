"""
Tests for Flask REST API endpoints
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
import app as app_module
from models import DIDRecord, BlogPost, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client():
    """Create a test client with a temporary database"""
    # Use in-memory SQLite for tests
    app = app_module.app
    app.config["TESTING"] = True

    # Create engine and session
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Override get_db to use test engine
    SessionLocal = sessionmaker(bind=engine)

    def get_test_db():
        return SessionLocal()

    original_get_db = app_module.get_db
    app_module.get_db = get_test_db

    with app.test_client() as client:
        yield client

    app_module.get_db = original_get_db


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Test that health endpoint returns ok"""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestDIDGeneration:
    def test_generate_keypair_endpoint(self, client):
        """Test POST /api/did/generate"""
        response = client.post("/api/did/generate")
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "private_key" in data
        assert "public_key" in data
        assert "address" in data
        assert "did" in data
        
        # Verify format
        assert data["address"].startswith("0x")
        assert len(data["address"]) == 42
        assert data["did"].startswith("did:eth:")


class TestStatsEndpoint:
    def test_stats_empty_database(self, client):
        """Test stats endpoint with empty database"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data["total_dids"] == 0
        assert data["active_dids"] == 0
        assert data["total_posts"] == 0
        assert data["verified_posts"] == 0


class TestDIDRegistration:
    def test_register_did(self, client):
        """Test DID registration endpoint"""
        # First generate keypair
        gen_response = client.post("/api/did/generate")
        gen_data = json.loads(gen_response.data)
        
        # Register DID
        response = client.post("/api/did/register", json={
            "did": gen_data["did"],
            "public_key": gen_data["public_key"],
            "address": gen_data["address"],
            "display_name": "Test User",
            "bio": "A test user",
            "private_key": gen_data["private_key"]
        })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["success"] == True
        assert data["did"] == gen_data["did"]
        assert data["address"] == gen_data["address"]
        assert "did_document" in data
    
    def test_register_duplicate_did(self, client):
        """Test that duplicate DID registration fails"""
        # Generate and register first DID
        gen_response = client.post("/api/did/generate")
        gen_data = json.loads(gen_response.data)
        
        client.post("/api/did/register", json={
            "did": gen_data["did"],
            "public_key": gen_data["public_key"],
            "address": gen_data["address"],
            "display_name": "Test User",
            "private_key": gen_data["private_key"]
        })
        
        # Try to register again with same DID
        response = client.post("/api/did/register", json={
            "did": gen_data["did"],
            "public_key": gen_data["public_key"],
            "address": gen_data["address"],
            "display_name": "Test User 2",
            "private_key": gen_data["private_key"]
        })
        
        assert response.status_code == 409
    
    def test_register_missing_fields(self, client):
        """Test that registration fails with missing fields"""
        response = client.post("/api/did/register", json={
            "did": "did:eth:0x123",
            "address": "0x123"
            # Missing required fields
        })
        
        assert response.status_code == 400


class TestDIDResolution:
    def test_resolve_did_by_address(self, client):
        """Test resolving DID by address"""
        # First register a DID
        gen_response = client.post("/api/did/generate")
        gen_data = json.loads(gen_response.data)
        
        client.post("/api/did/register", json={
            "did": gen_data["did"],
            "public_key": gen_data["public_key"],
            "address": gen_data["address"],
            "display_name": "Test User",
            "private_key": gen_data["private_key"]
        })
        
        # Resolve by address
        response = client.get(f"/api/did/resolve/{gen_data['address']}")
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data["did"] == gen_data["did"]
        assert data["address"] == gen_data["address"]
        assert data["display_name"] == "Test User"
        assert "did_document" in data
    
    def test_resolve_nonexistent_did(self, client):
        """Test resolving nonexistent DID"""
        response = client.get("/api/did/resolve/0x0000000000000000000000000000000000000000")
        assert response.status_code == 404


class TestBlogPosts:
    def test_get_posts_empty(self, client):
        """Test getting posts from empty database"""
        response = client.get("/api/posts")
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data["posts"] == []
        assert data["total"] == 0
    
    def test_publish_post_without_did(self, client):
        """Test that publishing fails without registered DID"""
        response = client.post("/api/posts/publish", json={
            "title": "Test Post",
            "body": "Test body",
            "author_did": "did:eth:0x123",
            "author_address": "0x123",
            "private_key": "0x123"
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_publish_post_missing_fields(self, client):
        """Test that publishing fails with missing fields"""
        response = client.post("/api/posts/publish", json={
            "title": "Test Post"
            # Missing required fields
        })
        
        assert response.status_code == 400


class TestErrorHandling:
    def test_404_not_found(self, client):
        """Test 404 error handling"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
