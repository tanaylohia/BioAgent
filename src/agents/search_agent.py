# AIDEV-SECTION: Search Agent - Coordinates BioResearcher, BioAnalyser, and Summarizer
import logging
from typing import Dict, Any, List

from src.models.search import SearchResult, AnalysisCache
from src.models.paper import Paper
from src.agents.bioresearcher import BioResearcher
from src.agents.bioanalyser import BioAnalyser
from src.agents.summarizer import SummarizerAgent
from src.utils.raw_logger import log_method_call, log_method_result, log_raw

logger = logging.getLogger(__name__)

class SearchAgent:
    """Manages the search workflow between BioResearcher and BioAnalyser"""
    
    def __init__(self):
        # Initialize agents directly
        logger.info("Initializing SearchAgent with raw logging")
        self.researcher = BioResearcher()
        self.analyser = BioAnalyser()
        self.summarizer = SummarizerAgent()
        
        self.cache = {}  # Simple in-memory cache
    
    async def execute(self, query: str, progress_callback=None, paper_callback=None, stream_callback=None) -> SearchResult:
        """Execute search with MANDATORY feedback loop"""
        # Log workflow start
        log_raw({
            "type": "WORKFLOW_START",
            "agent": "SearchAgent",
            "query": query
        })
        
        # Step 1: Initial research
        logger.info(f"Starting research for: {query}")
        if progress_callback:
            await progress_callback("Starting initial research phase", 20)
        
        research_data = await self.researcher.search(query)
        
        # Stream papers immediately after initial research
        if paper_callback and research_data.get('papers'):
            await paper_callback(research_data['papers'], "initial")
        
        if progress_callback:
            await progress_callback(f"Found {len(research_data.get('papers', []))} papers, analyzing results", 40)
        
        # Step 2: Analysis - ALWAYS get suggestions for additional searches
        analysis_result = await self.analyser.analyze(query, research_data)
        
        # Step 3: MANDATORY feedback loop - analyser always suggests additional searches
        logger.info("Executing mandatory feedback loop with analyser suggestions")
        missing_info = analysis_result.get("missing_info", analysis_result.get("suggested_searches", ""))
        
        if progress_callback:
            await progress_callback("Searching based on analyser suggestions", 60)
        
        # Cache the state including full research output
        cache_key = f"search_{hash(query)}"
        self.cache[cache_key] = AnalysisCache(
            user_query=query,
            previous_output=analysis_result["analysis"],
            missing_analysis=missing_info,
            initial_research_output=research_data.get("researcher_output", "")
        )
        
        # Step 4: Execute additional research based on analyser suggestions
        additional_data = await self.researcher.search_specific(missing_info)
        
        # Stream additional papers as they're found
        if paper_callback and additional_data.get('papers'):
            await paper_callback(additional_data['papers'], "additional")
        
        if progress_callback:
            await progress_callback("Finalizing comprehensive analysis", 80)
        
        # Step 5: Final analysis with all data
        cache_data = self.cache[cache_key]
        cache_data.updated_results = additional_data
        
        final_analysis = await self.analyser.analyze_with_cache(cache_data)
        
        # Combine all papers from both searches and deduplicate
        combined_papers = research_data["papers"] + additional_data.get("papers", [])
        all_papers = self._deduplicate_papers(combined_papers)
        
        if progress_callback:
            await progress_callback("Creating comprehensive scientific summary", 90)
        
        # Step 6: ALWAYS use SummarizerAgent for final comprehensive response after feedback loop
        # AIDEV-NOTE: Mandatory feedback loop ensures comprehensive coverage
        final_summary = await self.summarizer.summarize(
            query=query,
            papers=all_papers,
            initial_analysis=analysis_result["analysis"],
            feedback_analysis=final_analysis["analysis"],
            tool_calls=research_data.get("tool_calls", []) + additional_data.get("tool_calls", []),
            stream_callback=stream_callback
        )
        
        if progress_callback:
            await progress_callback("Search complete", 100)
        
        # Log workflow completion
        log_raw({
            "type": "WORKFLOW_COMPLETE",
            "agent": "SearchAgent",
            "query": query,
            "total_papers": len(all_papers),
            "total_tool_calls": len(research_data.get("tool_calls", []) + additional_data.get("tool_calls", []))
        })
        
        return SearchResult(
            query=query,
            papers=all_papers,
            analysis=final_summary,
            raw_data={**research_data, **additional_data},
            tool_calls=research_data.get("tool_calls", []) + additional_data.get("tool_calls", []),
            reasoning_trace=research_data.get("reasoning_trace", []) + additional_data.get("reasoning_trace", [])
        )
    
    def _deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """Remove duplicate papers based on title and DOI"""
        seen = set()
        unique_papers = []
        
        for paper in papers:
            # Create unique key - use lowercase title and DOI if available
            key = (paper.title.lower(), paper.doi) if paper.doi else paper.title.lower()
            
            if key not in seen:
                seen.add(key)
                unique_papers.append(paper)
        
        return unique_papers