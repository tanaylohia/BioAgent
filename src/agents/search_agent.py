# AIDEV-SECTION: Search Agent - Coordinates BioResearcher and BioAnalyser
import logging
from typing import Dict, Any

from src.models.search import SearchResult, AnalysisCache
from src.agents.bioresearcher import BioResearcher
from src.agents.bioanalyser import BioAnalyser

logger = logging.getLogger(__name__)

class SearchAgent:
    """Manages the search workflow between BioResearcher and BioAnalyser"""
    
    def __init__(self):
        self.researcher = BioResearcher()
        self.analyser = BioAnalyser()
        self.cache = {}  # Simple in-memory cache
    
    async def execute(self, query: str, progress_callback=None) -> SearchResult:
        """Execute search with feedback loop (max 1 iteration)"""
        # Step 1: Initial research
        logger.info(f"Starting research for: {query}")
        if progress_callback:
            await progress_callback("Starting research phase", 20)
        
        research_data = await self.researcher.search(query)
        
        if progress_callback:
            await progress_callback(f"Found {len(research_data.get('papers', []))} papers, analyzing results", 60)
        
        # Step 2: Analysis
        analysis_result = await self.analyser.analyze(query, research_data)
        
        # Step 3: Check if satisfied
        if analysis_result["satisfied"]:
            if progress_callback:
                await progress_callback("Analysis complete", 100)
            return SearchResult(
                query=query,
                papers=research_data["papers"],
                analysis=analysis_result["analysis"],
                raw_data=research_data,
                tool_calls=research_data.get("tool_calls", []),
                reasoning_trace=research_data.get("reasoning_trace", [])
            )
        
        # Step 4: One feedback loop if needed
        logger.info("Query not satisfied, executing feedback loop")
        missing_info = analysis_result["missing_info"]
        
        if progress_callback:
            await progress_callback("Searching for missing information", 75)
        
        # Cache the state
        cache_key = f"search_{hash(query)}"
        self.cache[cache_key] = AnalysisCache(
            user_query=query,
            previous_output=analysis_result["analysis"],
            missing_analysis=missing_info
        )
        
        # Get additional research
        additional_data = await self.researcher.search_specific(missing_info)
        
        if progress_callback:
            await progress_callback("Finalizing comprehensive analysis", 90)
        
        # Final analysis with all data
        cache_data = self.cache[cache_key]
        cache_data.updated_results = additional_data
        
        final_analysis = await self.analyser.analyze_with_cache(cache_data)
        
        # Combine all papers
        all_papers = research_data["papers"] + additional_data.get("papers", [])
        
        if progress_callback:
            await progress_callback("Search complete", 100)
        
        return SearchResult(
            query=query,
            papers=all_papers,
            analysis=final_analysis["analysis"],
            raw_data={**research_data, **additional_data},
            tool_calls=research_data.get("tool_calls", []) + additional_data.get("tool_calls", []),
            reasoning_trace=research_data.get("reasoning_trace", []) + additional_data.get("reasoning_trace", [])
        )