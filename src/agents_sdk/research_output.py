# AIDEV-SECTION: Structured Output Types for Agents
"""
Pydantic models for structured agent outputs.
These ensure agents complete their work before handoffs.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ResearchComplete(BaseModel):
    """
    Output type for BioResearcher to indicate research is complete.
    Forces the agent to make multiple tool calls before producing this output.
    """
    search_rounds_completed: int = Field(
        description="Number of search rounds completed"
    )
    total_papers_found: int = Field(
        description="Total number of papers found across all searches"
    )
    tools_used: List[str] = Field(
        description="List of search tools used"
    )
    research_summary: str = Field(
        description="Brief summary of what was found during research"
    )
    ready_for_analysis: bool = Field(
        default=True,
        description="Indicates research is complete and ready for analysis"
    )


class AnalysisResult(BaseModel):
    """
    Output type for BioAnalyser to structure its analysis.
    """
    query_satisfied: bool = Field(
        description="Whether the current evidence satisfies the query"
    )
    analysis: str = Field(
        description="Thorough scientific critique of findings"
    )
    missing_info: Optional[str] = Field(
        default=None,
        description="Specific searches needed if query not satisfied"
    )
    confidence_level: str = Field(
        description="Confidence in the analysis: High/Moderate/Low"
    )


class SynthesisReport(BaseModel):
    """
    Output type for Summarizer to produce final report.
    """
    executive_summary: str = Field(
        description="2-3 paragraph synthesis answering the query"
    )
    key_findings: List[str] = Field(
        description="List of primary findings"
    )
    evidence_quality: str = Field(
        description="Overall quality assessment of evidence"
    )
    recommendations: List[str] = Field(
        description="Actionable recommendations based on evidence"
    )
    citations_count: int = Field(
        description="Number of papers cited"
    )