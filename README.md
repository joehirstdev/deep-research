# Multi-Agent Research System

A deep research system powered by multiple specialized AI agents that decompose complex queries, conduct parallel research, and synthesize comprehensive answers with source citations.

## Features

- **Multi-Agent Architecture**: Coordinated agents (Planner, Searcher, Synthesizer) work together to answer complex queries
- **Deep Research**: Automatically decomposes queries into sub-questions for thorough investigation
- **Real-Time Streaming**: SSE (Server-Sent Events) streams progress updates and results as research happens
- **Source Citations**: Tracks and provides clickable citations for all research sources
- **Clean API**: FastAPI backend with both standard and streaming endpoints
- **Interactive Demo**: Browser-based UI to visualize the research process in real-time

## Architecture

### Multi-Agent Flow

```
User Query
    ↓
┌─────────────────┐
│ Planner Agent   │  Decomposes query into 2-5 focused sub-questions
└─────────────────┘
    ↓
┌─────────────────┐
│ Searcher Agent  │  Researches each sub-question (Tavily + LLM)
└─────────────────┘  Runs in parallel for all sub-questions
    ↓
┌─────────────────┐
│ Synthesizer     │  Combines findings into comprehensive answer
└─────────────────┘
    ↓
Final Answer + Sources
```

### Agent Responsibilities

1. **Planner Agent** (`src/agents/planner.py`)
   - Analyzes user queries and breaks them into answerable sub-questions
   - Orders questions logically (foundational → specific)
   - Provides reasoning for decomposition strategy

2. **Searcher Agent** (`src/agents/searcher.py`)
   - Executes web searches via Tavily API
   - Retrieves relevant content and context
   - Synthesizes findings with LLM
   - Tracks source URLs for citations

3. **Synthesizer** (Final LLM call in `/research` endpoints)
   - Combines all sub-question answers
   - Creates coherent, comprehensive response
   - Maintains source attribution

## Tech Stack

- **FastAPI**: Async web framework with SSE support
- **OpenAI SDK**: LLM integration (configured for Google Gemini)
- **Tavily AI**: Web search API optimized for AI agents
- **Pydantic**: Type-safe data validation and settings
- **Python 3.13+**: Modern async/await patterns

## Setup

### Prerequisites

- Python 3.13+
- API Keys:
  - [Gemini API](https://aistudio.google.com/app/apikey) (free tier available)
  - [Tavily API](https://tavily.com/) (free 1000 searches/month)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd deep-research
   ```

2. **Install dependencies**
   ```bash
   pip install -e .
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

   Required variables:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   TAVILY_API_KEY=your_tavily_api_key
   GEMINI_MODEL=gemini-2.5-flash
   ```

4. **Run the server**
   ```bash
   fastapi dev src/main.py
   ```

   Server will start at: http://localhost:8000

## Usage

### Interactive Demo (Recommended)

Open http://localhost:8000/static/demo.html in your browser.

1. Enter a research query (e.g., "How does RAG improve LLM accuracy?")
2. Click "Research"
3. Watch real-time progress as agents work:
   - Planning phase
   - Research sub-questions
   - Final synthesis

### API Endpoints

#### 1. Streaming Research (Primary)

```bash
POST /research/stream
```

Real-time SSE stream with progress updates.

**Example:**
```bash
curl -N -X POST http://localhost:8000/research/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG and how does it improve LLM outputs?"}'
```

**SSE Events:**
- `progress`: Status updates ("Planning...", "Researching 1/3...")
- `plan`: Research plan with sub-questions
- `sub_result`: Each answered sub-question with sources
- `final`: Synthesized final answer
- `complete`: Summary with all unique sources

#### 2. Standard Research

```bash
POST /research
```

Returns complete results after all processing finishes.

**Example:**
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain photosynthesis and its importance"}'
```

**Response:**
```json
{
  "query": "...",
  "plan": {
    "original_query": "...",
    "sub_questions": ["...", "..."],
    "reasoning": "..."
  },
  "sub_results": [
    {
      "question": "...",
      "answer": "...",
      "sources": ["url1", "url2"]
    }
  ],
  "final_answer": "...",
  "all_sources": ["unique_url1", "unique_url2", ...]
}
```

#### 3. Simple Search (Fast)

```bash
GET /test/{query}
```

Single-agent search without decomposition (faster, less comprehensive).

## Design Decisions

### Why Tavily?

Tavily was chosen over alternatives (SerpAPI, DuckDuckGo, Brave) because:
- Purpose-built for AI agents with structured responses
- Includes content snippets (not just links)
- Clean API with good free tier
- Shows awareness of specialized AI tooling ecosystem

### Why Streaming?

The multi-agent flow involves multiple LLM calls and searches (10-20+ seconds). SSE streaming:
- Provides real-time progress feedback
- Improves perceived performance
- Demonstrates production UX thinking
- Shows understanding of async architectures

### Why Gemini?

Using Gemini 2.5 Flash via OpenAI-compatible endpoint:
- Fast inference for quick iteration
- Cost-effective for development
- Supports structured output (JSON mode)
- Easy to swap for other providers

## Project Structure

```
deep-research/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── planner.py          # Planner agent - query decomposition
│   │   ├── searcher.py         # Searcher agent - research with LLM synthesis
│   │   └── search.py           # Web search tool (Tavily integration)
│   ├── main.py                  # FastAPI app and endpoints
│   ├── settings.py              # Pydantic settings
│   └── utils.py                 # Retry logic and utilities
├── static/
│   └── demo.html                # Interactive demo UI
├── pyproject.toml               # Dependencies and config
├── .env.example                 # Environment template
└── README.md
```

## Testing

Run tests:
```bash
pytest
```

(Note: Test suite under development)

## Future Improvements

- **Caching**: Cache search results and LLM responses to reduce API costs
- **Parallel Search**: Run sub-question searches concurrently for faster research
- **Source Ranking**: Prioritize authoritative sources
- **Fact Verification**: Cross-reference claims across multiple sources
- **Citation Formatting**: Structured citations (APA, MLA, etc.)
- **Query Refinement**: Iterative follow-up questions based on initial findings
- **Export Options**: PDF, Markdown, JSON exports
- **Analytics**: Track research quality metrics

## Interview Discussion Points

1. **Multi-Agent Coordination**: How agents communicate and maintain state
2. **Trade-offs**: Simple vs. multi-agent endpoints for different use cases
3. **Production Readiness**: Error handling, retry logic, rate limiting
4. **Scalability**: Async patterns, parallel execution, caching strategies
5. **Cost Optimization**: Token usage, search API costs, caching decisions

## License

MIT

## Author

Built for Akro AI Technical Assessment
