# AIDEV-SECTION: Paper Metadata Models
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class Paper(BaseModel):
    """Paper metadata for frontend display"""
    title: str
    abstract: str
    authors: List[str]
    citations: int = 0
    publication_date: Optional[datetime] = None
    hyperlink: str
    source: str  # PubMed, bioRxiv, etc.
    doi: Optional[str] = None
    journal: Optional[str] = None  # Journal or venue name
    
    class Config:
        # AIDEV-NOTE: Use Pydantic's built-in JSON encoders for datetime
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }