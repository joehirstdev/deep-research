"""Tests for SynthesizerAgent."""

from unittest.mock import Mock

from src.agents.synthesizer import SynthesizerAgent


def test_synthesizer_combines_sub_results():
    """Test that synthesizer combines sub-question answers into comprehensive answer."""
    # Mock the OpenAI client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = (
        "Photosynthesis is the process by which plants convert light energy into chemical energy. "
        "It occurs in two main stages: light-dependent reactions and light-independent reactions (Calvin cycle). "
        "Photosynthesis is crucial for life on Earth as it produces oxygen and serves as the foundation of food chains."
    )
    mock_client.chat.completions.create.return_value = mock_response

    # Create synthesizer with mock client
    synthesizer = SynthesizerAgent(llm_client=mock_client, model="test-model")

    # Test data
    sub_results = [
        {"question": "What is photosynthesis?", "answer": "A process where plants convert light to energy."},
        {"question": "What are the stages?", "answer": "Light-dependent and light-independent reactions."},
        {"question": "Why is it important?", "answer": "Produces oxygen and supports food chains."},
    ]

    # Test
    result = synthesizer.synthesize("Explain photosynthesis", sub_results)

    # Assertions
    assert isinstance(result, str)
    assert len(result) > 0
    assert "photosynthesis" in result.lower()
    mock_client.chat.completions.create.assert_called_once()
