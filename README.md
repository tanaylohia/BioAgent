# Bio Agent Backend - Clean Implementation

Simple, clean implementation of Bio Agent with BioResearcher and BioAnalyser agents using OpenAI function calling.

## Architecture

```
User Query → Orchestrator → Search Agent
                               ├── BioResearcher (GPT-4.1)
                               │     └── OpenAI Function Calling
                               │           ├── search_papers (Semantic Scholar + CrossRef)
                               │           ├── search_pubmed (PubMed/Europe PMC)
                               │           ├── search_preprints (bioRxiv/medRxiv)
                               │           ├── search_clinical_trials (ClinicalTrials.gov)
                               │           ├── search_variants (MyVariant.info)
                               │           └── web_search (OpenAI built-in)
                               └── BioAnalyser (GPT-4o-mini)
                                     └── Feedback Loop (1x max)
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Add your Azure OpenAI API key
   ```

3. Run the service:
   ```bash
   python -m src.orchestrator.main
   ```

## API Usage

```bash
POST /search
{
  "query": "BRCA1 mutations in breast cancer",
  "toggles": {"search": true}
}
```

## Key Features

- Simple orchestrator for routing based on toggles
- BioResearcher agent with OpenAI function calling
- Direct API integration (no MCP overhead)
- Intelligent tool selection by GPT-4
- Parallel tool execution for efficiency
- BioAnalyser agent with single feedback loop
- Paper metadata extraction for frontend
- In-memory caching for feedback loop

## Available Search Tools

1. **search_papers** - Academic papers from Semantic Scholar and CrossRef
2. **search_pubmed** - Peer-reviewed biomedical literature from PubMed
3. **search_preprints** - Latest research from bioRxiv and medRxiv
4. **search_clinical_trials** - Clinical trials from ClinicalTrials.gov
5. **search_variants** - Genetic variant data from MyVariant.info
6. **web_search** - General web search via OpenAI