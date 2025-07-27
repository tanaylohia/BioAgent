# Bio Agent Backend

A biomedical research agent system built with OpenAI Agents SDK for comprehensive literature search and analysis.

## Overview

The Bio Agent Backend provides AI-powered biomedical research capabilities through a multi-agent system:

- **BioResearcher**: Performs comprehensive searches across multiple databases (PubMed, Semantic Scholar, bioRxiv, etc.)
- **BioAnalyser**: Analyzes search results and identifies knowledge gaps
- **Summarizer**: Creates structured scientific summaries and recommendations

## Architecture

### Current Implementation (OpenAI Agents SDK)
- **Location**: `src/agents_sdk/`
- **Server**: `src/orchestrator/main_sdk.py`
- **Runner**: `run_sdk_server.py`
- **Port**: 6001

### Legacy Implementation (Manual Orchestration)
- **Location**: `src/agents/`
- **Server**: `src/orchestrator/main.py`
- **Port**: 6000

## Quick Start

### Prerequisites
```bash
pip install openai-agents
```

### Environment Variables
```env
ENDPOINT_URL=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME=o4-mini
```

### Run SDK Server
```bash
python run_sdk_server.py
```

Server starts on `http://localhost:6001`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/search` | POST | Start search task |
| `/ws/{task_id}` | WebSocket | Real-time progress |
| `/health` | GET | Health check |

### Example Request
```json
POST /search
{
    "query": "How to build salt tolerance in IR64 rice variety in India?",
    "toggles": {"search": true}
}
```

### Example Response
```json
{
    "task_id": "uuid-here",
    "status": "started",
    "message": "Search initiated. Connect to WebSocket for real-time updates."
}
```

## Key Features

### OpenAI Agents SDK Implementation
- **Auto Tool Calling**: Uses `@function_tool` decorator for automatic schema generation
- **Agent Handoffs**: Structured workflow between BioResearcher → BioAnalyser → Summarizer
- **Mandatory Feedback Loop**: BioAnalyser always identifies gaps and requests additional research
- **Multi-Model Support**: GPT-4.1 for research, o4-mini for analysis

### Search Tools
- PubMed/PubTator3 integration
- Semantic Scholar API
- bioRxiv preprint search
- Clinical trials database
- Genetic variant databases
- Google Scholar academic search

### Research Workflow
1. **BioResearcher** performs comprehensive multi-database searches
2. **BioAnalyser** evaluates results and identifies knowledge gaps
3. **Feedback loop** ensures thorough coverage via additional searches
4. **Summarizer** creates final structured scientific summary

## File Structure

```
src/
├── agents_sdk/           # OpenAI Agents SDK implementation
│   ├── bio_agents.py     # Agent definitions with handoffs
│   ├── simple_runner.py  # Workflow execution
│   ├── sdk_tools.py      # Tool implementations
│   └── azure_config.py   # Azure OpenAI client setup
├── orchestrator/
│   ├── main_sdk.py       # FastAPI server (current)
│   ├── main.py           # Legacy server
│   └── sdk_search.py     # SDK integration layer
├── tools/                # Search tool implementations
├── models/               # Data models
└── utils/                # Utilities and logging

prompts.py               # Agent prompts and instructions
run_sdk_server.py        # Main server launcher
CLAUDE.md               # Development guidelines
```

## Development

### Adding New Search Tools
1. Implement tool in `src/tools/`
2. Add `@function_tool` decorator in `src/agents_sdk/sdk_tools.py`
3. Include in agent tool list in `src/agents_sdk/bio_agents.py`

### Modifying Agent Behavior
- Update prompts in `prompts.py`
- Adjust handoff logic in `src/agents_sdk/bio_agents.py`
- Modify output types in `src/agents_sdk/research_output.py`

### Debugging
- Raw logs available via `src/utils/raw_logger.py`
- WebSocket progress tracking in real-time
- Structured agent communication via SDK