"""Integration tests for FastAPI endpoints."""

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.agents.planner import ResearchPlan
from src.main import app


def test_login_success():
    """Test successful login with correct credentials."""
    with patch("src.main.settings") as mock_settings:
        mock_settings.basic_auth_username = "testuser"
        mock_settings.basic_auth_password = "testpass"

        client = TestClient(app)
        response = client.post("/login", auth=("testuser", "testpass"))

        assert response.status_code == 200
        assert response.json()["message"] == "Login successful"
        assert response.json()["username"] == "testuser"


def test_login_failure():
    """Test login failure with incorrect credentials."""
    with patch("src.main.settings") as mock_settings:
        mock_settings.basic_auth_username = "testuser"
        mock_settings.basic_auth_password = "testpass"

        client = TestClient(app)
        response = client.post("/login", auth=("wronguser", "wrongpass"))

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]


def test_research_stream_requires_auth():
    """Test that research endpoint requires authentication."""
    client = TestClient(app)
    response = client.post("/research/stream", json={"query": "What is photosynthesis?"})

    assert response.status_code == 401


def test_research_stream_full_flow():
    """Test complete research streaming flow with mocked agents."""
    # Mock settings
    with patch("src.main.settings") as mock_settings:
        mock_settings.basic_auth_username = "testuser"
        mock_settings.basic_auth_password = "testpass"

        # Mock planner
        mock_plan = ResearchPlan(
            original_query="What is photosynthesis?",
            sub_questions=["What is photosynthesis?", "What are the stages of photosynthesis?"],
            reasoning="These questions cover the basics.",
        )

        # Mock the agents in the main module
        with (
            patch("src.main.planner") as mock_planner,
            patch("src.main.researcher") as mock_researcher,
            patch("src.main.synthesizer") as mock_synthesizer,
        ):
            mock_planner.plan.return_value = mock_plan
            mock_researcher.get_sources.return_value = ["https://example.com/photo1", "https://example.com/photo2"]
            mock_researcher.research.return_value = (
                "Photosynthesis is the process by which plants convert light to energy.",
                ["https://example.com/photo1"],
            )
            mock_synthesizer.synthesize.return_value = (
                "Photosynthesis is the process by which plants convert light energy into "
                "chemical energy through two main stages."
            )

            client = TestClient(app)
            response = client.post(
                "/research/stream", json={"query": "What is photosynthesis?"}, auth=("testuser", "testpass")
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            # Parse SSE events from response
            events = []
            for line in response.text.strip().split("\n\n"):
                if line.startswith("data: "):
                    event_data = json.loads(line[6:])
                    events.append(event_data)

            # Verify event sequence
            event_types = [e["type"] for e in events]

            # Should have: progress, plan, question(s), sources, answer(s), all_sources, progress, final, complete
            assert "progress" in event_types
            assert "plan" in event_types
            assert "question" in event_types
            assert "sources" in event_types
            assert "answer" in event_types
            assert "all_sources" in event_types
            assert "final" in event_types
            assert "complete" in event_types

            # Verify plan event contains sub_questions
            plan_event = next(e for e in events if e["type"] == "plan")
            assert len(plan_event["sub_questions"]) == 2
            assert plan_event["total"] == 2

            # Verify final answer is present
            final_event = next(e for e in events if e["type"] == "final")
            assert "Photosynthesis" in final_event["answer"]

            # Verify agents were called
            mock_planner.plan.assert_called_once_with("What is photosynthesis?")
            assert mock_researcher.get_sources.call_count == 2
            assert mock_researcher.research.call_count == 2
            mock_synthesizer.synthesize.assert_called_once()


def test_research_stream_invalid_query():
    """Test research endpoint with invalid (empty) query."""
    with patch("src.main.settings") as mock_settings:
        mock_settings.basic_auth_username = "testuser"
        mock_settings.basic_auth_password = "testpass"

        client = TestClient(app)
        response = client.post("/research/stream", json={"query": ""}, auth=("testuser", "testpass"))

        assert response.status_code == 422  # Validation error
