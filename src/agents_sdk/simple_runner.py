# AIDEV-SECTION: Simplified SDK Runner
"""
Simplified runner for the Bio Agent workflow without complex streaming.
This gets the basic SDK implementation working first.
"""
import logging
from typing import Optional, Callable
from agents import Runner
from src.agents_sdk.bio_agents import bioresearcher, bioanalyser, summarizer
from src.agents_sdk.paper_extractor import extract_papers_from_run_result
# Removed handoff_manager dependency
from src.models.search import SearchResult

logger = logging.getLogger(__name__)


async def run_bio_agent_workflow_simple(
    query: str,
    progress_callback: Optional[Callable] = None
) -> SearchResult:
    """
    Simple version of the bio agent workflow using SDK.
    
    Args:
        query: The research query
        progress_callback: Optional callback for progress updates
        
    Returns:
        SearchResult with papers, analysis, and metadata
    """
    logger.info(f"Starting simple SDK workflow for query: {query}")
    
    # SDK handles workflow automatically
    
    if progress_callback:
        await progress_callback("Starting research with SDK agents...", 10)
    
    try:
        # Run the SDK workflow
        # This will automatically handle:
        # 1. BioResearcher internal loop (multiple searches)
        # 2. Handoff to BioAnalyser
        # 3. Feedback loop if needed
        # 4. Final handoff to Summarizer
        
        result = await Runner.run(
            bioresearcher,  # Starting agent
            input=f"Search comprehensively for: {query}",
            agents=[bioresearcher, bioanalyser, summarizer],  # Available agents
            max_turns=50  # Prevent infinite loops
        )
        
        if progress_callback:
            await progress_callback("Extracting papers from results...", 80)
        
        # Extract papers from the run result
        papers = extract_papers_from_run_result(result)
        
        if progress_callback:
            await progress_callback("Formatting final results...", 90)
        
        # Get the final output (should be from Summarizer)
        final_analysis = str(result.final_output)
        
        # Create basic tool calls summary
        tool_calls = []
        tool_count = 0
        
        # Count items that look like tool calls
        for item in result.new_items:
            if hasattr(item, 'tool_name'):
                tool_count += 1
                tool_calls.append({
                    "tool": getattr(item, 'tool_name', 'unknown'),
                    "query": "SDK managed",
                    "papers_found": 0  # Will be calculated below
                })
        
        if progress_callback:
            await progress_callback("Research complete!", 100)
        
        logger.info(f"SDK workflow complete. Found {len(papers)} papers, {tool_count} tool calls")
        
        return SearchResult(
            query=query,
            papers=papers,
            analysis=final_analysis,
            raw_data={"sdk_result": "completed", "total_items": len(result.new_items)},
            tool_calls=tool_calls,
            reasoning_trace=[
                f"SDK workflow completed with {len(result.new_items)} total items",
                f"Final output from: {result.new_items[-1].__class__.__name__ if result.new_items else 'unknown'}"
            ]
        )
        
    except Exception as e:
        logger.error(f"SDK workflow error: {e}", exc_info=True)
        
        if progress_callback:
            await progress_callback(f"Error: {str(e)}", 100)
        
        # Return error result
        return SearchResult(
            query=query,
            papers=[],
            analysis=f"Search failed due to an error: {str(e)}",
            raw_data={"error": str(e)},
            tool_calls=[],
            reasoning_trace=[f"Error occurred: {str(e)}"]
        )