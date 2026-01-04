"""Tests for ResearcherAgent."""

from unittest.mock import Mock, patch

from src.agents.researcher import ResearcherAgent
from src.agents.search import SearchResult


def test_researcher_returns_answer_and_links():
    """Test that researcher synthesizes answer from search results and returns links."""
    # Mock the OpenAI client
    mock_llm_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = (
        "Photosynthesis is the process by which plants convert light energy into chemical energy, "
        "occurring in chloroplasts and producing oxygen as a byproduct."
    )
    mock_llm_client.chat.completions.create.return_value = mock_response

    # Mock search results
    mock_search_results = [
        SearchResult(
            url="https://example.com/photo1",
            title="Photosynthesis Basics",
            content="Plants use light to make food...",
            score=0.95,
        ),
        SearchResult(
            url="https://example.com/photo2",
            title="Plant Biology",
            content="Chloroplasts are the site of photosynthesis...",
            score=0.88,
        ),
    ]

    # Patch web_search to return mock results
    with patch("src.agents.researcher.web_search", return_value=mock_search_results):
        # Create researcher with mock client
        researcher = ResearcherAgent(llm_client=mock_llm_client, search_api_key="test-key", model="test-model")

        # Test
        answer, links = researcher.research("What is photosynthesis?")

        # Assertions
        assert isinstance(answer, str)
        assert len(answer) > 0
        assert "photosynthesis" in answer.lower()
        assert isinstance(links, list)
        assert len(links) == 2
        assert links[0] == "https://example.com/photo1"
        assert links[1] == "https://example.com/photo2"
        mock_llm_client.chat.completions.create.assert_called_once()
