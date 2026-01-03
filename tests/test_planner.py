"""Tests for PlannerAgent."""

from unittest.mock import Mock
from src.agents.planner import PlannerAgent, ResearchPlan


def test_planner_decomposes_query():
    """Test that planner decomposes a query into sub-questions."""
    # Mock the OpenAI client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = """{
        "sub_questions": [
            "What is photosynthesis?",
            "What are the stages of photosynthesis?",
            "Why is photosynthesis important?"
        ],
        "reasoning": "These questions cover the definition, process, and significance."
    }"""
    mock_client.chat.completions.create.return_value = mock_response

    # Create planner with mock client
    planner = PlannerAgent(llm_client=mock_client)

    # Test
    result = planner.plan("Explain photosynthesis and its importance")

    # Assertions
    assert isinstance(result, ResearchPlan)
    assert len(result.sub_questions) == 3
    assert result.sub_questions[0] == "What is photosynthesis?"
    assert result.reasoning == "These questions cover the definition, process, and significance."
    assert result.original_query == "Explain photosynthesis and its importance"
