"""Tests for web search functionality."""

from unittest.mock import Mock, patch

from src.agents.search import SearchResult, web_search


def test_web_search_returns_results():
    """Test that web_search returns SearchResult objects from Tavily API."""
    # Mock the Tavily client
    with patch("src.agents.search.TavilyClient") as mock_tavily:
        mock_client_instance = Mock()
        mock_tavily.return_value = mock_client_instance

        # Mock response from Tavily
        mock_client_instance.search.return_value = {
            "results": [
                {
                    "url": "https://example.com/article1",
                    "title": "Understanding Photosynthesis",
                    "content": "Photosynthesis is a process used by plants...",
                    "score": 0.95,
                },
                {
                    "url": "https://example.com/article2",
                    "title": "How Plants Make Food",
                    "content": "Plants use sunlight to create energy...",
                    "score": 0.88,
                },
            ]
        }

        # Test
        results = web_search("photosynthesis", api_key="test-key", max_results=3)

        # Assertions
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].url == "https://example.com/article1"
        assert results[0].title == "Understanding Photosynthesis"
        assert results[0].score == 0.95
        assert results[1].url == "https://example.com/article2"
        mock_client_instance.search.assert_called_once_with(query="photosynthesis", max_results=3)
