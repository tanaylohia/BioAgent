# AIDEV-SECTION: OpenAI Function Calling Tool Definitions
"""
Tool definitions in OpenAI function calling format
These define the schema for each tool that the BioResearcher agent can use
"""

TOOL_DEFINITIONS = [
    # Google Academic Search
    {
        "type": "function",
        "function": {
            "name": "google_academic_search",
            "description": "Search Google for academic papers, scholarly articles, and research publications. Best for finding recent papers, PDFs, and content from academic websites like Nature, Science, Cell, NEJM, arXiv, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for academic content"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (max 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    
    # Academic Literature Tools
    {
        "type": "function",
        "function": {
            "name": "search_papers",
            "description": "Search for academic papers using Semantic Scholar and CrossRef databases. Returns papers from both sources with title, authors, abstract, DOI, and other metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for finding relevant papers"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results per source",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_paper_details",
            "description": "Get detailed information about a specific paper including full abstract, citations, and metadata",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper identifier (DOI or Semantic Scholar ID)"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["semantic_scholar", "crossref"],
                        "description": "Source database to fetch from",
                        "default": "semantic_scholar"
                    }
                },
                "required": ["paper_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_by_topic",
            "description": "Search papers by topic with optional date range filtering. Useful for finding papers within specific time periods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Search topic (max 300 characters)"
                    },
                    "year_start": {
                        "type": "integer",
                        "description": "Start year for date range filter"
                    },
                    "year_end": {
                        "type": "integer",
                        "description": "End year for date range filter"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["topic"]
            }
        }
    },
    
    # PubMed and Preprint Tools
    {
        "type": "function",
        "function": {
            "name": "search_pubmed",
            "description": "Search PubMed/PubTator3 for peer-reviewed biomedical literature. Can filter by genes and diseases.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Main search query"
                    },
                    "genes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of gene names to filter results"
                    },
                    "diseases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of diseases to filter results"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_preprints",
            "description": "Search bioRxiv and medRxiv preprint servers for latest research not yet peer-reviewed",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "include_biorxiv": {
                        "type": "boolean",
                        "description": "Include bioRxiv results",
                        "default": True
                    },
                    "include_medrxiv": {
                        "type": "boolean",
                        "description": "Include medRxiv results",
                        "default": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        }
    },
    
    # Clinical Trials Tool
    {
        "type": "function",
        "function": {
            "name": "search_clinical_trials",
            "description": "Search ClinicalTrials.gov for ongoing and completed clinical trials",
            "parameters": {
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "description": "Medical condition being studied"
                    },
                    "intervention": {
                        "type": "string",
                        "description": "Treatment intervention (drug, procedure, etc.)"
                    },
                    "phase": {
                        "type": "string",
                        "description": "Trial phase (e.g., '3' or '2|3')"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED", "TERMINATED"],
                        "description": "Trial recruitment status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 20
                    }
                }
            }
        }
    },
    
    # Variant Search Tool
    {
        "type": "function",
        "function": {
            "name": "search_variants",
            "description": "Search for genetic variants and mutations using MyVariant.info database",
            "parameters": {
                "type": "object",
                "properties": {
                    "gene": {
                        "type": "string",
                        "description": "Gene symbol (e.g., 'BRCA1', 'TP53')"
                    },
                    "variant_type": {
                        "type": "string",
                        "description": "Type of variant (e.g., 'SNP', 'deletion', 'insertion')"
                    },
                    "clinical_significance": {
                        "type": "string",
                        "enum": ["pathogenic", "likely_pathogenic", "benign", "likely_benign", "uncertain_significance"],
                        "description": "Clinical significance of the variant"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 20
                    }
                },
                "required": ["gene"]
            }
        }
    }
    
    # Note: Web search is not a built-in tool for Azure OpenAI
    # We need to implement it as a function
]

# AIDEV-NOTE: Function to get tool by name
def get_tool_definition(tool_name: str):
    """Get a specific tool definition by name"""
    for tool in TOOL_DEFINITIONS:
        if tool.get("type") == "function" and tool["function"]["name"] == tool_name:
            return tool
    return None

# AIDEV-NOTE: Function to get all function names
def get_all_tool_names():
    """Get list of all available tool names"""
    names = []
    for tool in TOOL_DEFINITIONS:
        if tool.get("type") == "function":
            names.append(tool["function"]["name"])
        elif tool.get("type") == "web_search":
            names.append("web_search")
    return names