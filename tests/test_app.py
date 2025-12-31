"""
Tests for the Mergington High School Activities API
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to known state before each test"""
    # Store original state
    original = {
        "Basketball Team": {
            "description": "Join the school basketball team and compete in local leagues",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 6:00 PM",
            "max_participants": 15,
            "participants": ["alex@mergington.edu", "jordan@mergington.edu"]
        },
        "Soccer Club": {
            "description": "Practice soccer skills and play friendly matches",
            "schedule": "Wednesdays, 3:30 PM - 5:30 PM",
            "max_participants": 18,
            "participants": ["lucas@mergington.edu", "mia@mergington.edu"]
        },
        "Art Club": {
            "description": "Explore painting, drawing, and other visual arts",
            "schedule": "Mondays, 3:30 PM - 5:00 PM",
            "max_participants": 16,
            "participants": ["ava@mergington.edu", "liam@mergington.edu"]
        },
    }
    
    # Clear current activities
    activities.clear()
    # Restore original
    activities.update(original)
    
    yield
    
    # Cleanup after test
    activities.clear()
    activities.update(original)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_list(self, client):
        """Test that /activities returns the activities list"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
    
    def test_get_activities_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
    
    def test_get_activities_contains_known_activity(self, client):
        """Test that activities include Basketball Team"""
        response = client.get("/activities")
        data = response.json()
        assert "Basketball Team" in data
        assert len(data["Basketball Team"]["participants"]) == 2


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant"""
        email = "testuser@mergington.edu"
        client.post(f"/activities/Basketball%20Team/signup?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball Team"]["participants"]
    
    def test_signup_nonexistent_activity_returns_404(self, client):
        """Test that signing up for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_returns_400(self, client):
        """Test that signing up twice returns error"""
        email = "alex@mergington.edu"  # Already signed up
        response = client.post(
            f"/activities/Basketball%20Team/signup?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_increments_participant_count(self, client):
        """Test that participant count increases after signup"""
        response1 = client.get("/activities")
        count_before = len(response1.json()["Soccer Club"]["participants"])
        
        client.post("/activities/Soccer%20Club/signup?email=newperson@mergington.edu")
        
        response2 = client.get("/activities")
        count_after = len(response2.json()["Soccer Club"]["participants"])
        
        assert count_after == count_before + 1


class TestUnregister:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "alex@mergington.edu"
        response = client.post(
            f"/activities/Basketball%20Team/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "jordan@mergington.edu"
        client.post(f"/activities/Basketball%20Team/unregister?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Basketball Team"]["participants"]
    
    def test_unregister_nonexistent_activity_returns_404(self, client):
        """Test that unregistering from non-existent activity returns 404"""
        response = client.post(
            "/activities/Fake%20Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_not_registered_returns_400(self, client):
        """Test that unregistering non-registered student returns error"""
        response = client.post(
            "/activities/Basketball%20Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_decrements_participant_count(self, client):
        """Test that participant count decreases after unregister"""
        email = "ava@mergington.edu"  # In Art Club
        
        response1 = client.get("/activities")
        count_before = len(response1.json()["Art Club"]["participants"])
        
        client.post(f"/activities/Art%20Club/unregister?email={email}")
        
        response2 = client.get("/activities")
        count_after = len(response2.json()["Art Club"]["participants"])
        
        assert count_after == count_before - 1


class TestIntegration:
    """Integration tests for signup and unregister flows"""
    
    def test_signup_then_unregister(self, client):
        """Test signing up and then unregistering"""
        email = "integrationtest@mergington.edu"
        activity = "Art%20Club"
        
        # Verify not signed up
        response = client.get("/activities")
        assert email not in response.json()["Art Club"]["participants"]
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signed up
        response = client.get("/activities")
        assert email in response.json()["Art Club"]["participants"]
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistered
        response = client.get("/activities")
        assert email not in response.json()["Art Club"]["participants"]
    
    def test_multiple_users_signup(self, client):
        """Test multiple different users signing up"""
        users = [
            "user1@mergington.edu",
            "user2@mergington.edu",
            "user3@mergington.edu"
        ]
        
        for user in users:
            response = client.post(
                f"/activities/Soccer%20Club/signup?email={user}"
            )
            assert response.status_code == 200
        
        response = client.get("/activities")
        participants = response.json()["Soccer Club"]["participants"]
        
        for user in users:
            assert user in participants
