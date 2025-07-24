# AIDEV-SECTION: Search Models
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from .paper import Paper

class SearchRequest(BaseModel):
    """User search request"""
    query: str
    toggles: Dict[str, bool] = {"search": True}  # Default search is on
    
class SearchResult(BaseModel):
    """Complete search result"""
    query: str
    papers: List[Paper]
    analysis: str
    raw_data: Dict[str, Any]  # For caching
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Track which tools were called
    reasoning_trace: Optional[List[Dict[str, Any]]] = None  # Agent reasoning for each round
    
class AnalysisCache(BaseModel):
    """Cache for analysis feedback loop"""
    user_query: str
    previous_output: str
    missing_analysis: str
    updated_results: Optional[Dict[str, Any]] = None