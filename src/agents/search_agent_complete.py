# Complete Search Agent with proper feedback loop
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from src.agents.bioresearcher_enhanced import EnhancedBioResearcher
from src.agents.bioanalyser import BioAnalyser
from src.models.search import SearchResult, AnalysisCache
from src.models.paper import Paper

logger = logging.getLogger(__name__)

class CompleteSearchAgent:
    """Complete search agent with BioResearcher-BioAnalyser feedback loop"""
    
    def __init__(self):
        self.bioresearcher = EnhancedBioResearcher()
        self.bioanalyser = BioAnalyser()
        self.max_iterations = 2  # Maximum feedback loops to prevent infinite searching
        
    async def execute(self, query: str, progress_callback: Optional[Callable] = None) -> SearchResult:
        """
        Execute complete search with feedback loop
        
        Args:
            query: User's search query
            progress_callback: Optional callback for progress updates
            
        Returns:
            SearchResult with papers and final analysis
        """
        logger.info(f"Starting complete search for: {query}")
        
        # Track all iterations
        all_papers = []
        all_tool_calls = []
        iteration_history = []
        
        # Initial search
        if progress_callback:
            await progress_callback("Starting initial search...", 10)
            
        iteration = 1
        current_query = query
        previous_analysis = None
        
        while iteration <= self.max_iterations:
            logger.info(f"Iteration {iteration}: Searching with query: {current_query}")
            
            # Phase 1: BioResearcher searches
            iteration_data = {
                "iteration": iteration,
                "query": current_query,
                "start_time": datetime.now().isoformat()
            }
            
            if progress_callback:
                await progress_callback(f"Iteration {iteration}: BioResearcher searching...", 20 + (iteration-1) * 30)
            
            research_results = await self.bioresearcher.search(current_query)
            
            # Aggregate results
            new_papers = [p for p in research_results['papers'] if p not in all_papers]
            all_papers.extend(new_papers)
            all_tool_calls.extend(research_results['tool_calls'])
            
            iteration_data["papers_found"] = len(research_results['papers'])
            iteration_data["new_papers"] = len(new_papers)
            iteration_data["tool_calls"] = len(research_results['tool_calls'])
            
            logger.info(f"Iteration {iteration}: Found {len(new_papers)} new papers (total: {len(all_papers)})")
            
            # Phase 2: BioAnalyser analyzes
            if progress_callback:
                await progress_callback(f"Iteration {iteration}: BioAnalyser analyzing {len(all_papers)} papers...", 30 + (iteration-1) * 30)
            
            analysis_input = {
                "papers": all_papers,
                "raw_searches": research_results.get('raw_searches', {})
            }
            
            if previous_analysis and iteration > 1:
                # Use cache for subsequent iterations
                cache = AnalysisCache(
                    user_query=query,
                    previous_output=previous_analysis.get('analysis', ''),
                    missing_analysis=previous_analysis.get('missing_info', ''),
                    updated_results=analysis_input
                )
                analysis_result = await self.bioanalyser.analyze_with_cache(cache)
            else:
                # First analysis
                analysis_result = await self.bioanalyser.analyze(query, analysis_input)
            
            iteration_data["analysis_satisfied"] = analysis_result.get('satisfied', False)
            iteration_data["end_time"] = datetime.now().isoformat()
            iteration_history.append(iteration_data)
            
            # Check if satisfied
            if analysis_result.get('satisfied', False):
                logger.info(f"Query satisfied after {iteration} iteration(s)")
                if progress_callback:
                    await progress_callback("Analysis complete - query satisfied!", 90)
                break
            
            # Not satisfied - prepare for next iteration
            if iteration < self.max_iterations:
                missing_info = analysis_result.get('missing_info', '')
                if not missing_info:
                    logger.warning("Query not satisfied but no missing info provided")
                    break
                
                # Create refined query for next iteration
                logger.info(f"Iteration {iteration}: Query not satisfied. Refining search...")
                logger.info(f"Missing info: {missing_info[:200]}...")
                
                # Construct new query based on missing information
                current_query = self._refine_query(query, missing_info, analysis_result.get('analysis', ''))
                previous_analysis = analysis_result
                iteration += 1
            else:
                logger.info(f"Reached maximum iterations ({self.max_iterations})")
                break
        
        # Final progress update
        if progress_callback:
            await progress_callback("Preparing final results...", 95)
        
        # Create final result
        result = SearchResult(
            query=query,
            papers=all_papers,
            analysis=analysis_result.get('analysis', ''),
            raw_data={
                "iterations": iteration_history,
                "total_tool_calls": len(all_tool_calls),
                "final_satisfied": analysis_result.get('satisfied', False)
            },
            tool_calls=all_tool_calls,
            reasoning_trace=[{
                "iteration": i+1,
                "papers_found": hist["papers_found"],
                "new_papers": hist["new_papers"],
                "satisfied": hist["analysis_satisfied"]
            } for i, hist in enumerate(iteration_history)]
        )
        
        if progress_callback:
            await progress_callback("Search complete!", 100)
        
        return result
    
    def _refine_query(self, original_query: str, missing_info: str, previous_analysis: str) -> str:
        """
        Refine the search query based on missing information
        
        Args:
            original_query: Original user query
            missing_info: Missing information identified by BioAnalyser
            previous_analysis: Previous analysis results
            
        Returns:
            Refined query for next search iteration
        """
        # Extract key missing elements from the missing_info
        refined_parts = []
        
        # Look for specific patterns in missing_info
        if "Punjab Agricultural University" in missing_info or "PAU" in missing_info:
            refined_parts.append("Punjab Agricultural University rice breeding")
        
        if "QTL" in missing_info or "marker" in missing_info:
            refined_parts.append("QTL mapping marker assisted selection rice Punjab")
        
        if "agronomic" in missing_info or "sowing date" in missing_info:
            refined_parts.append("agronomic management sowing date rice Punjab")
        
        if "ICAR" in missing_info:
            refined_parts.append("ICAR rice research Punjab early maturity")
        
        if "photoperiod" in missing_info or "temperature" in missing_info:
            refined_parts.append("photoperiod temperature response rice Punjab")
        
        if "germplasm" in missing_info:
            refined_parts.append("rice germplasm characterization Punjab early maturity")
        
        # If we found specific refinements, use them
        if refined_parts:
            refined_query = " OR ".join(refined_parts)
            logger.info(f"Refined query: {refined_query}")
            return refined_query
        
        # Fallback: add more specific terms to original query
        return f"{original_query} site:pau.edu OR site:icar.org.in OR Punjab Agricultural University OR PAU Ludhiana"