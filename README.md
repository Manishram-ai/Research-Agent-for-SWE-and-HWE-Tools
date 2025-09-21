## Research Agent for SWE and HWE Tools

A CLI agent that researches developer tools for a given query. It:
- Extracts relevant tools from recent web content
- Finds official websites and scrapes content via Firecrawl
- Analyzes each tool using an LLM (structured output)
- Prints concise, developer-focused recommendations

## Features
- **Tool extraction**: Pulls concrete products/services from articles and pages.
- **Web research**: Uses Firecrawl to search and scrape official sources.
- **Structured analysis**: Pricing model, open-source status, API availability, tech stack, language support, integrations.
- **Actionable output**: Clear CLI results plus short recommendations.

## Requirements
- **Python**: 3.11+
- **API keys**:
  - `FIRECRAWL_API_KEY` (required)
  - `GROQ_API_KEY` (required for `langchain_groq.ChatGroq`)

## Quickstart

### 1) Clone
```bash
git clone <your-repo-url> Dev_Research_agent
cd Dev_Research_agent
```

### 2) Environment variables
Create a `.env` file in the project root:
```bash
# .env
FIRECRAWL_API_KEY=your_firecrawl_key
GROQ_API_KEY=your_groq_key
```

### 3) Install

- With uv (recommended; uses `pyproject.toml` + `uv.lock`):
```bash
# Install uv if needed: https://docs.astral.sh/uv/
uv sync
```

- Or with pip (fallback):
```bash
python -m venv .venv
source .venv/bin/activate
pip install firecrawl-py langchain langchain-groq langchain-openai langgraph pydantic python-dotenv
```

### 4) Run
```bash
# Using uv
uv run python main.py

# Or with python
python main.py
```

## Usage
When prompted, enter a developer-tools query (type `quit` or `exit` to stop). Example queries:
- "API monitoring tools"
- "feature flag platforms"
- "error tracking for JS"
- "vector databases"
- "CI/CD for monorepos"

### Sample output (truncated)
```text
Developer Tools Research Agent

🔍 Developer Tools Query: vector databases

📊 Results for: vector databases
============================================================

1. 🏢 Pinecone
   🌐 Website: https://www.pinecone.io/
   💰 Pricing: Freemium
   📖 Open Source: False
   🛠️  Tech Stack: Python, JavaScript, REST
   💻 Language Support: Python, JavaScript
   🔌 API: ✅ Available
   🔗 Integrations: LangChain, LlamaIndex
   📝 Description: Managed vector database for semantic search and AI apps.

2. 🏢 Weaviate
   ...

Developer Recommendations:
----------------------------------------
For most teams, start with Pinecone for simplicity and managed ops; choose Weaviate if you need open-source control and on-prem. Pinecone’s API and ecosystem are strong and the free tier covers prototyping. Weaviate’s modular architecture is a win if you need hybrid search and extensibility.
```

## How it works

- **CLI entrypoint**: `main.py`
  - Loads `.env`, runs an interactive loop, calls `Workflow.run(query)`, prints results and recommendations.

  
- **Workflow**: `src/workflow.py`
  - Builds a `langgraph` state machine:
    - `extract_tools`: Searches/scrapes and asks the LLM to extract tool names.
    - `research`: Finds official sites; scrapes with Firecrawl; analyzes each using structured LLM output.
    - `recommendation`: Generates a brief, actionable summary.
  - Uses `ChatGroq(model="openai/gpt-oss-20b", temperature=0.4)`.


- **Firecrawl client**: `src/firecrawl_client.py`
  - `search_companies(query, num_results)`: Firecrawl Search API
  - `scrape_company_pages(url)`: Firecrawl Scrape API (markdown)
  - Requires `FIRECRAWL_API_KEY`.

- **Models**: `src/models.py`
  - `CompanyAnalysis`, `CompanyInfo`, `ResearchState` (Pydantic).
- **Prompts**: `src/prompts.py`
  - System and user prompts for extraction, analysis, and recommendations.

## Project layout
- `main.py`: CLI runner
- `src/workflow.py`: Orchestrates the research graph and LLM calls
- `src/firecrawl_client.py`: Firecrawl search/scrape integration
- `src/models.py`: Pydantic schemas for state and results
- `src/prompts.py`: Prompt templates
- `pyproject.toml`: Dependencies and metadata
- `uv.lock`: Locked dependency resolution for uv

## Configuration
- **Model**: `openai/gpt-oss-20b` via `ChatGroq` (needs `GROQ_API_KEY`)
- **Search/scrape**: Firecrawl (needs `FIRECRAWL_API_KEY`)
- **Env loading**: `python-dotenv` via `.env`

## Troubleshooting
- **Missing FIRECRAWL_API_KEY**: You’ll see "Missing FIRECRAWL_API_KEY environment variable". Add it to `.env`.
- **GROQ auth errors**: Ensure `GROQ_API_KEY` is set and valid.
- **Sparse/empty results**: The extractor falls back gracefully, but better queries (specific domain/feature) yield better tool lists.
- **Rate limits/network**: Retry after a minute; Firecrawl/LLM providers may throttle.

## Notes
- You can swap models or providers by adjusting `ChatGroq` in `src/workflow.py`.
