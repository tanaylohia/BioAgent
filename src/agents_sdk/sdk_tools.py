# AIDEV-SECTION: SDK Tool Definitions
"""
Tool functions for the OpenAI Agents SDK implementation.
These are decorated versions of our existing search tools that return string outputs.
"""
import json
import logging
from typing import Optional
from agents import function_tool
from src.tools import search_tools

logger = logging.getLogger(__name__)

# Helper function to format tool results as strings
def format_tool_result(result: dict, tool_name: str) -> str:
    """Format tool results for SDK consumption - INCLUDE FULL ABSTRACTS"""
    try:
        # Extract key metrics
        total_results = 0
        sources = []
        
        if "results" in result:
            total_results = len(result.get("results", []))
            sources.append(tool_name)
        elif "semantic_scholar" in result:
            total_results += len(result.get("semantic_scholar", []))
            total_results += len(result.get("crossref", []))
            sources.extend(["Semantic Scholar", "CrossRef"])
        elif "biorxiv" in result:
            total_results += len(result.get("biorxiv", []))
            total_results += len(result.get("medrxiv", []))
            sources.extend(["bioRxiv", "medRxiv"])
        
        # Create detailed output with abstracts prominently displayed
        output = f"=== SEARCH RESULTS: {tool_name} ===\n"
        output += f"Total papers found: {total_results}\n"
        output += f"Sources: {', '.join(sources) if sources else tool_name}\n\n"
        
        # Add papers with full abstracts
        output += "=== DETAILED PAPER INFORMATION WITH ABSTRACTS ===\n\n"
        
        paper_count = 0
        # Handle different result formats
        if "results" in result:
            papers = result["results"]
        elif "semantic_scholar" in result:
            papers = result["semantic_scholar"] + result["crossref"]
        elif "biorxiv" in result:
            papers = result["biorxiv"] + result["medrxiv"]
        else:
            papers = []
        
        for paper in papers[:50]:  # Include up to 50 papers
            paper_count += 1
            output += f"\n--- PAPER {paper_count} ---\n"
            output += f"TITLE: {paper.get('title', 'No title')}\n"
            output += f"AUTHORS: {paper.get('authors', 'No authors')}\n"
            output += f"YEAR: {paper.get('year', paper.get('date', 'Unknown'))}\n"
            output += f"SOURCE: {paper.get('source', tool_name)}\n"
            
            # FULL ABSTRACT
            abstract = paper.get('abstract', 'No abstract available')
            output += f"\nFULL ABSTRACT:\n{abstract}\n"
            
            # If full text is available
            if paper.get('has_full_text'):
                output += f"\nFULL TEXT AVAILABLE: YES (PDF URL: {paper.get('pdf_url', 'N/A')})\n"
                full_text = paper.get('full_text', '')
                # Include first 1000 chars of full text
                output += f"FULL TEXT PREVIEW:\n{full_text[:1000]}...\n" if len(full_text) > 1000 else f"FULL TEXT:\n{full_text}\n"
            
            output += f"\nDOI: {paper.get('doi', 'N/A')}\n"
            output += "-" * 80 + "\n"
        
        # Also include the raw JSON for completeness
        output += "\n\n=== RAW JSON DATA ===\n"
        output += json.dumps(result, indent=2, ensure_ascii=False)
        
        return output
    except Exception as e:
        logger.error(f"Error formatting {tool_name} results: {e}")
        return f"Error processing {tool_name} results: {str(e)}"


@function_tool
async def search_pubmed(query: str, limit: int = 50) -> str:
    """Search PubMed/PubTator3 for peer-reviewed biomedical literature.
    
    Args:
        query: Main search query for biomedical literature
        limit: Maximum number of results to return
    """
    try:
        result = await search_tools.search_pubmed(query=query, limit=limit)
        return format_tool_result(result, "PubMed")
    except Exception as e:
        logger.error(f"PubMed search error: {e}")
        return f"PubMed search failed: {str(e)}"


@function_tool
async def search_papers(query: str, limit: int = 50) -> str:
    """Search academic papers using Semantic Scholar and CrossRef databases.
    
    Args:
        query: Search query for finding relevant papers
        limit: Maximum number of results per source
    """
    try:
        result = await search_tools.search_papers(query=query, limit=limit)
        return format_tool_result(result, "Academic Papers")
    except Exception as e:
        logger.error(f"Papers search error: {e}")
        return f"Papers search failed: {str(e)}"


@function_tool
async def search_by_topic(topic: str, year_start: Optional[int] = None, year_end: Optional[int] = None, limit: int = 50) -> str:
    """Search papers by topic with optional date range filtering.
    
    Args:
        topic: Search topic (max 300 characters)
        year_start: Start year for date range filter
        year_end: End year for date range filter
        limit: Maximum number of results
    """
    try:
        result = await search_tools.search_by_topic(
            topic=topic, 
            year_start=year_start, 
            year_end=year_end, 
            limit=limit
        )
        return format_tool_result(result, "Topic Search")
    except Exception as e:
        logger.error(f"Topic search error: {e}")
        return f"Topic search failed: {str(e)}"


@function_tool
async def google_academic_search(query: str, limit: int = 10) -> str:
    """Search Google for academic papers, scholarly articles, and research publications.
    
    Args:
        query: Search query for academic content
        limit: Maximum number of results (max 10)
    """
    try:
        result = await search_tools.google_academic_search(query=query, limit=limit)
        return format_tool_result(result, "Google Academic")
    except Exception as e:
        logger.error(f"Google academic search error: {e}")
        return f"Google academic search failed: {str(e)}"


@function_tool
async def search_preprints(query: str, include_biorxiv: bool = True, include_medrxiv: bool = True, limit: int = 50) -> str:
    """Search bioRxiv and medRxiv preprint servers for latest research not yet peer-reviewed.
    
    Args:
        query: Search query
        include_biorxiv: Include bioRxiv results
        include_medrxiv: Include medRxiv results
        limit: Maximum results
    """
    try:
        result = await search_tools.search_preprints(
            query=query,
            include_biorxiv=include_biorxiv,
            include_medrxiv=include_medrxiv,
            limit=limit
        )
        return format_tool_result(result, "Preprints")
    except Exception as e:
        logger.error(f"Preprints search error: {e}")
        return f"Preprints search failed: {str(e)}"


@function_tool
async def search_clinical_trials(condition: Optional[str] = None, intervention: Optional[str] = None, phase: Optional[str] = None, status: Optional[str] = None, limit: int = 20) -> str:
    """Search ClinicalTrials.gov for ongoing and completed clinical trials.
    
    Args:
        condition: Medical condition being studied
        intervention: Treatment intervention (drug, procedure, etc.)
        phase: Trial phase (e.g., '3' or '2|3')
        status: Trial recruitment status (RECRUITING, ACTIVE_NOT_RECRUITING, COMPLETED, TERMINATED)
        limit: Maximum results
    """
    try:
        # Build kwargs only with provided parameters
        kwargs = {"limit": limit}
        if condition:
            kwargs["condition"] = condition
        if intervention:
            kwargs["intervention"] = intervention
        if phase:
            kwargs["phase"] = phase
        if status:
            kwargs["status"] = status
            
        result = await search_tools.search_clinical_trials(**kwargs)
        return format_tool_result(result, "Clinical Trials")
    except Exception as e:
        logger.error(f"Clinical trials search error: {e}")
        return f"Clinical trials search failed: {str(e)}"


@function_tool
async def search_variants(gene: str, variant_type: Optional[str] = None, clinical_significance: Optional[str] = None, limit: int = 20) -> str:
    """Search for genetic variants and mutations using MyVariant.info database.
    
    Args:
        gene: Gene symbol (e.g., 'BRCA1', 'TP53')
        variant_type: Type of variant (e.g., 'SNP', 'deletion', 'insertion')
        clinical_significance: Clinical significance (pathogenic, likely_pathogenic, benign, likely_benign, uncertain_significance)
        limit: Maximum results
    """
    try:
        # Build kwargs only with provided parameters
        kwargs = {"gene": gene, "limit": limit}
        if variant_type:
            kwargs["variant_type"] = variant_type
        if clinical_significance:
            kwargs["clinical_significance"] = clinical_significance
            
        result = await search_tools.search_variants(**kwargs)
        return format_tool_result(result, "Genetic Variants")
    except Exception as e:
        logger.error(f"Variants search error: {e}")
        return f"Variants search failed: {str(e)}"


# AIDEV-NOTE: These tools return strings for SDK compatibility
# The actual paper extraction happens in paper_extractor.py