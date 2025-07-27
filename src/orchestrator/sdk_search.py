# AIDEV-SECTION: SDK Search Integration
"""
Integration layer between the OpenAI Agents SDK implementation and the existing API.
This replaces the manual SearchAgent with SDK-based workflow.
"""
import logging
from typing import Dict, Any, Optional, Callable
from src.agents_sdk.simple_runner import run_bio_agent_workflow_simple
from src.models.search import SearchResult
from src.utils.raw_logger import log_raw

logger = logging.getLogger(__name__)


async def execute_sdk_search(
    query: str,
    progress_callback: Optional[Callable] = None
) -> SearchResult:
    """
    Execute search using the OpenAI Agents SDK implementation.
    
    This is a drop-in replacement for SearchAgent.execute() that uses
    the SDK's agent handoffs and automatic orchestration.
    
    Args:
        query: The research query
        progress_callback: Optional callback for WebSocket progress updates
        
    Returns:
        SearchResult with papers, analysis, and metadata
    """
    logger.info(f"Executing SDK search for: {query}")
    
    # Log the search start
    log_raw({
        "type": "SDK_SEARCH_START",
        "query": query,
        "implementation": "OpenAI Agents SDK"
    })
    
    try:
        # Run the SDK workflow with simple runner
        result = await run_bio_agent_workflow_simple(
            query=query,
            progress_callback=progress_callback
        )
        
        # Log completion
        log_raw({
            "type": "SDK_SEARCH_COMPLETE",
            "query": query,
            "papers_found": len(result.papers),
            "tool_calls": len(result.tool_calls)
        })
        
        logger.info(f"SDK search complete. Found {len(result.papers)} papers")
        
        return result
        
    except Exception as e:
        logger.error(f"SDK search error: {e}", exc_info=True)
        
        # Log error
        log_raw({
            "type": "SDK_SEARCH_ERROR",
            "query": query,
            "error": str(e)
        })
        
        # Return empty result on error
        return SearchResult(
            query=query,
            papers=[],
            analysis=f"Search failed due to an error: {str(e)}",
            raw_data={"error": str(e)},
            tool_calls=[],
            reasoning_trace=["Error occurred during search"]
        )


# Optional: Function to toggle between SDK and legacy implementation
USE_SDK_IMPLEMENTATION = True  # Set via environment variable in production

async def execute_search(
    query: str,
    progress_callback: Optional[Callable] = None
) -> SearchResult:
    """
    Execute search using either SDK or legacy implementation.
    
    This allows gradual migration and A/B testing.
    """
    if USE_SDK_IMPLEMENTATION:
        return await execute_sdk_search(query, progress_callback)
    else:
        # Fall back to legacy SearchAgent
        from src.agents.search_agent import SearchAgent
        agent = SearchAgent()
        return await agent.execute(query, progress_callback)