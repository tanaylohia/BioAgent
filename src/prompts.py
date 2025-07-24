"""
Central prompts configuration for Bio Agent
All prompts are managed here for easy modification and consistency
"""

# AIDEV-SECTION: Search Agent Prompts

SEARCH_PROMPTS = {
    "research_planning": {
        "system": """You are a biomedical research assistant specializing in academic literature search.
Your role is to help researchers find relevant papers, analyze research questions, and provide comprehensive search strategies.""",
        
        "user_template": """Research Query: {query}

Please analyze this biomedical research question and provide:
1. Key concepts and search terms
2. Relevant synonyms and related terms
3. Suggested search strategies
4. Types of papers that would be most relevant""",
    },
    
    "search_query_expansion": {
        "system": """You are an expert in biomedical terminology and search query optimization.
Your task is to expand search queries with relevant synonyms, abbreviations, and related terms.""",
        
        "user_template": """Original Query: {query}

Expand this query with:
1. Medical/scientific synonyms
2. Common abbreviations
3. Related protein/gene names
4. Disease variations
5. Relevant pathways or mechanisms

Format as a list of search terms.""",
    },
    
    "search_result_analysis": {
        "system": """You are a biomedical literature analyst. Your role is to analyze search results 
and provide structured summaries highlighting the most relevant findings.""",
        
        "user_template": """Query: {query}
Search Results: {results}

Please analyze these search results and provide:
1. Key findings relevant to the query
2. Most important papers (ranked by relevance)
3. Common themes across papers
4. Gaps in current research
5. Suggested follow-up searches""",
    },
    
    "deep_research_planning": {
        "system": """You are a senior biomedical researcher planning comprehensive literature reviews.
Create detailed research plans that explore topics systematically and thoroughly.""",
        
        "user_template": """Research Topic: {topic}
Depth Level: {depth}
Time Constraint: {time_limit}

Create a comprehensive research plan including:
1. Primary research questions
2. Sub-topics to explore
3. Search strategy for each sub-topic
4. Expected types of evidence
5. Hypothesis generation approach
6. Validation criteria""",
    },
}

# AIDEV-SECTION: Tool Selection Prompts

TOOL_PROMPTS = {
    "tool_selection": {
        "system": """You are a biomedical tool selection expert. Based on the research query and context,
determine which biological tools and databases would be most useful.""",
        
        "user_template": """Query: {query}
Available Tool Categories: {tool_categories}
Search Results Context: {search_context}

Recommend which tool categories to use and why:
1. Essential tools for this query
2. Optional but helpful tools
3. Tools to avoid for this query
4. Suggested order of tool execution""",
    },
    
    "tool_parameter_extraction": {
        "system": """You extract specific parameters needed for biological tool queries from natural language.""",
        
        "user_template": """User Query: {query}
Target Tool: {tool_name}
Required Parameters: {required_params}

Extract the following parameters from the query:
{param_descriptions}

Return as JSON.""",
    },
}

# AIDEV-SECTION: Analysis and Synthesis Prompts

ANALYSIS_PROMPTS = {
    "evidence_synthesis": {
        "system": """You are a biomedical evidence synthesis expert. Your role is to integrate findings
from multiple sources into coherent, actionable insights.""",
        
        "user_template": """Research Question: {question}
Literature Findings: {literature_findings}
Tool Results: {tool_results}

Synthesize these findings into:
1. Supported conclusions (high confidence)
2. Tentative findings (medium confidence)
3. Conflicting evidence
4. Knowledge gaps
5. Recommended next steps""",
    },
    
    "confidence_scoring": {
        "system": """You evaluate the confidence level of biomedical findings based on evidence quality,
consistency, and source reliability.""",
        
        "user_template": """Finding: {finding}
Supporting Evidence: {evidence}
Source Quality: {sources}

Provide:
1. Confidence score (0-100)
2. Strength of evidence assessment
3. Potential limitations
4. Factors affecting confidence""",
    },
}

# AIDEV-SECTION: Response Formatting Prompts

RESPONSE_PROMPTS = {
    "user_response": {
        "system": """You format biomedical research findings for researchers in a clear, 
actionable format with proper citations.""",
        
        "user_template": """Query: {original_query}
Analysis Results: {analysis}
Tool Insights: {tool_insights}
Citations: {citations}

Format a comprehensive response including:
1. Executive summary
2. Key findings
3. Detailed analysis
4. Tool-specific insights
5. Citations and references
6. Suggested next steps""",
    },
    
    "citation_formatting": {
        "system": """You format academic citations in standard biomedical formats.""",
        
        "user_template": """Papers: {papers}
Format: {citation_format}

Format these papers as proper citations.""",
    },
}

# AIDEV-SECTION: Web Search Specific Prompts (for OpenAI web search)

WEB_SEARCH_PROMPTS = {
    "biomedical_web_search": {
        "system": """You are conducting biomedical web searches. Focus on reputable sources like:
- PubMed, bioRxiv, medRxiv
- Nature, Science, Cell journals
- Clinical trial databases
- Protein and gene databases
- Medical institution websites""",
        
        "user_template": """Research Query: {query}
Search Type: {search_type}

Conduct a web search focusing on:
1. Recent research papers
2. Clinical trial updates
3. Protein/gene information
4. Disease mechanisms
5. Treatment options

Prioritize peer-reviewed sources.""",
    },
}

# AIDEV-NOTE: Helper function to get prompts with formatting
def get_prompt(category: str, prompt_name: str, **kwargs) -> dict:
    """
    Get a formatted prompt from the central configuration
    
    Args:
        category: The prompt category (e.g., 'SEARCH_PROMPTS', 'TOOL_PROMPTS')
        prompt_name: The specific prompt name
        **kwargs: Variables to format into the prompt
        
    Returns:
        Dict with 'system' and 'user' keys containing formatted prompts
    """
    prompt_dict = globals().get(category, {}).get(prompt_name, {})
    if not prompt_dict:
        raise ValueError(f"Prompt {prompt_name} not found in {category}")
    
    return {
        "system": prompt_dict.get("system", ""),
        "user": prompt_dict.get("user_template", "").format(**kwargs)
    }