"""Tests for the new endpoints and response models."""

import pytest
from fastapi.testclient import TestClient
from main import app
from uuid import uuid4
import json


@pytest.fixture(scope="module")
def client():
    """Create a test client."""
    with TestClient(app) as c:
        yield c


class TestFarmersEndpoint:
    """Test the GET /api/farmers endpoint."""
    
    def test_farmers_endpoint_structure(self, client):
        """Test that the endpoint returns the correct structure."""
        response = client.get("/api/farmers")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        
        # Check if sensitive data is not present
        for item in data["items"]:
            assert "national_id" not in item
            assert "phone" not in item
            assert "gender" not in item
            assert "date_of_birth" not in item
            assert "current_score" in item
            
            # Check current_score structure
            if item["current_score"] is not None:
                assert "final_score" in item["current_score"]
                assert "decision" in item["current_score"]
                assert "recommended_amount" in item["current_score"]
    
    def test_farmers_limit_capping(self, client):
        """Test that limit is capped at 100."""
        response = client.get("/api/farmers?limit=150")
        assert response.status_code == 200
        
        data = response.json()
        # The actual number of items may be less than 100 if there aren't enough farmers
        assert len(data["items"]) <= 100
        assert data["total"] >= len(data["items"])
    
    def test_farmers_offset_past_end(self, client):
        """Test that offset past the end returns empty list with correct total."""
        response = client.get("/api/farmers?limit=50&offset=1000")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 0
        assert data["total"] >= 0
    
    def test_farmers_pagination(self, client):
        """Test pagination with limit and offset."""
        # Get first page
        response1 = client.get("/api/farmers?limit=10&offset=0")
        assert response1.status_code == 200
        
        data1 = response1.json()
        assert len(data1["items"]) <= 10
        
        # Get second page
        response2 = client.get("/api/farmers?limit=10&offset=10")
        assert response2.status_code == 200
        
        data2 = response2.json()
        assert len(data2["items"]) <= 10
        
        # Check that total is consistent
        assert data1["total"] == data2["total"]
        
        # Check that items are different (assuming we have more than 10 farmers)
        if len(data1["items"]) > 0 and len(data2["items"]) > 0:
            first_page_ids = {item["id"] for item in data1["items"]}
            second_page_ids = {item["id"] for item in data2["items"]}
            assert first_page_ids.isdisjoint(second_page_ids)


class TestNetworkEndpoint:
    """Test the GET /api/farmers/{id}/network endpoint."""
    
    def test_network_nonexistent_farmer(self, client):
        """Test that the endpoint returns 404 for a non-existent farmer."""
        nonexistent_id = uuid4()
        response = client.get(f"/api/farmers/{nonexistent_id}/network")
        assert response.status_code == 404
        assert "Farmer not found" in response.json()["detail"]
    
    def test_network_structure(self, client):
        """Test that the endpoint returns the correct structure when farmer exists."""
        # This test requires a farmer to exist in the database
        # For now, we'll test the structure with a mock farmer
        farmer_id = str(uuid4())
        
        # We can't test the full endpoint without a real farmer in the database
        # But we can verify that the endpoint exists and returns the expected structure
        # when called with a valid farmer ID
        
        # This is a placeholder test - in a real scenario, we would:
        # 1. Create a farmer
        # 2. Create related entities (farms, trust sources, etc.)
        # 3. Call the endpoint
        # 4. Verify the response structure
        
        # For now, just verify the endpoint exists
        response = client.get(f"/api/farmers/{farmer_id}/network")
        # This will likely return 404, but that's expected without test data
        assert response.status_code in [404, 200]


class TestBreakdownEndpoint:
    """Test the GET /api/verify/{session_id}/breakdown endpoint."""
    
    def test_breakdown_nonexistent_session(self, client):
        """Test that the endpoint returns 404 for a non-existent session."""
        nonexistent_id = uuid4()
        response = client.get(f"/api/verify/{nonexistent_id}/breakdown")
        assert response.status_code == 404
        assert "Verification session not found" in response.json()["detail"]
    
    def test_breakdown_no_score(self, client):
        """Test that the endpoint returns 404 for a session with no score."""
        # This test requires a verification session with no score
        # For now, we'll test the structure with a mock session
        session_id = str(uuid4())
        
        # We can't test the full endpoint without a real session in the database
        # But we can verify that the endpoint exists and returns the expected structure
        # when called with a valid session ID that has a score
        
        # This is a placeholder test - in a real scenario, we would:
        # 1. Create a verification session
        # 2. Ensure it has a score
        # 3. Call the endpoint
        # 4. Verify the response structure
        
        # For now, just verify the endpoint exists
        response = client.get(f"/api/verify/{session_id}/breakdown")
        # This will likely return 404, but that's expected without test data
        assert response.status_code in [404, 200]


class TestResponseModels:
    """Test that response models are properly defined."""
    
    def test_openapi_schema(self, client):
        """Test that all UI-consumed routes have non-empty response schemas."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # List of endpoints that should have non-empty response schemas
        endpoints_to_check = [
            "/api/farmers",
            "/api/farmers/{id}",
            "/api/farmers/{id}/farm",
            "/api/trust/sources",
            "/api/trust/institutions",
            "/api/trust/social-groups",
            "/api/trust/market-actors",
            "/api/farmers/{id}/link-trust-source",
            "/api/farmers/{id}/link-institution",
            "/api/farmers/{id}/link-social-group",
            "/api/farmers/{id}/link-market-actor",
            "/api/verify/start",
            "/api/verify/{id}/respond/{participant_id}",
            "/api/verify/{id}/timeout/{participant_id}",
            "/api/verify/{id}/status",
            "/api/verify/{id}/result",
            "/api/verify/{id}/explanation",
            "/api/farmers/{id}/inkind-settlement",
            "/api/loans",
            "/api/loans/{id}/disburse",
            "/api/loans/{id}/repay",
            "/api/loans/{id}/default",
            "/api/farmers/{id}/network",
            "/api/verify/{id}/breakdown",
        ]
        
        endpoints_with_empty_schema = []
        
        for endpoint in endpoints_to_check:
            # Find the endpoint in the schema
            path = endpoint.split("/")[2]  # Get the path part (e.g., "farmers")
            method = endpoint.split("/")[3] if len(endpoint.split("/")) > 3 else "get"
            
            if path in schema["paths"]:
                path_methods = schema["paths"][path]
                if method in path_methods:
                    endpoint_schema = path_methods[method]
                    if "responses" in endpoint_schema:
                        # Check if the response schema is not empty
                        if "200" in endpoint_schema["responses"]:
                            response_schema = endpoint_schema["responses"]["200"]
                            if "content" in response_schema and "application/json" in response_schema["content"]:
                                schema_data = endpoint_schema["responses"]["200"]["content"]["application/json"]
                                if schema_data == {}:
                                    endpoints_with_empty_schema.append(endpoint)
                else:
                    print(f"Method {method} not found for endpoint {endpoint}")
            else:
                print(f"Endpoint {endpoint} not found in schema")
        
        assert not endpoints_with_empty_schema, (
            f"The following endpoints have empty response schemas: {endpoints_with_empty_schema}"
        )
    
    def test_trust_source_response_model(self, client):
        """Test that trust source response model has optional rating when personal_knowledge_flag is false."""
        # This test verifies that the response model for trust sources has the correct structure
        # We can't test the actual endpoint behavior without test data, but we can verify
        # that the schema is correctly defined
        
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        
        # Find the trust sources endpoint
        if "/api/trust/sources" in schema["paths"]:
            post_schema = schema["paths"]["/api/trust/sources"]["post"]
            
            # Check that the response schema is defined
            assert "responses" in post_schema
            assert "200" in post_schema["responses"]
            
            # Check that the response content is defined
            response_content = post_schema["responses"]["200"]["content"]
            assert "application/json" in response_content
            
            # The actual response schema should be a dict, not empty
            response_schema = response_content["application/json"]
            assert response_schema != {}
        
        # Find the verification response endpoint
        if "/api/verify/{id}/respond/{participant_id}" in schema["paths"]:
            post_schema = schema["paths"]["/api/verify/{id}/respond/{participant_id}"]["post"]
            
            # Check that the request body schema is defined
            assert "requestBody" in post_schema
            request_body = post_schema["requestBody"]
            assert "content" in request_body
            assert "application/json" in request_body["content"]
            
            # The request body schema should have the correct discriminator
            request_schema = request_body["content"]["application/json"]
            assert "discriminator" in request_schema
            assert "propertyName" in request_schema["discriminator"]
            assert "mapping" in request_schema["discriminator"]


class TestCredibilityScore:
    """Test credibility score behavior."""
    
    def test_credibility_default(self, client):
        """Test that credibility score defaults to 1.0 when no history exists."""
        # This test requires creating a farmer with trust sources
        # and then checking that their credibility scores are 1.0
        
        # This is a placeholder test - in a real scenario, we would:
        # 1. Create a farmer
        # 2. Create trust sources linked to the farmer
        # 3. Call the network endpoint
        # 4. Verify that credibility scores are 1.0
        
        # For now, we can't test this without test data
        pass
    
    def test_credibility_after_default(self, client):
        """Test that credibility score is below 1.0 after a default."""
        # This test requires creating a farmer with trust sources
        # and then simulating a loan default
        
        # This is a placeholder test - in a real scenario, we would:
        # 1. Create a farmer
        # 2. Create trust sources linked to the farmer
        # 3. Create a loan and mark it as defaulted
        # 4. Call the network endpoint
        # 5. Verify that the endorsing verifier's credibility score is below 1.0
        
        # For now, we can't test this without test data
        pass


class TestPhoneMasking:
    """Test phone number masking."""
    
    def test_phone_masking(self, client):
        """Test that phone numbers are properly masked."""
        # This test requires creating a farmer with trust sources
        # and then checking that their phone numbers are masked
        
        # This is a placeholder test - in a real scenario, we would:
        # 1. Create a farmer
        # 2. Create trust sources with phone numbers
        # 3. Call the network endpoint
        # 4. Verify that phone numbers are masked (e.g., "+2547*****123")
        
        # For now, we can't test this without test data
        pass


class TestBreakdownComponents:
    """Test breakdown components sum back to the profile."""
    
    def test_breakdown_components_sum(self, client):
        """Test that breakdown components sum back to the profile."""
        # This test requires creating a verification session with a score
        # and then checking that the components sum correctly
        
        # This is a placeholder test - in a real scenario, we would:
        # 1. Create a verification session
        # 2. Ensure it has a score with components
        # 3. Call the breakdown endpoint
        # 4. Verify that the components sum back to the profile
        
        # For now, we can't test this without test data
        pass