# OpenAI Agents SDK implementation for Bio Agent Backend
"""
This module contains the OpenAI Agents SDK implementation of the Bio Agent system.
It replaces the manual orchestration with SDK's built-in agent handoffs and tool management.
"""

from .bio_agents import bioresearcher, bioanalyser, summarizer
from .simple_runner import run_bio_agent_workflow_simple
from .sdk_tools import (
    search_pubmed,
    search_papers,
    search_by_topic,
    google_academic_search,
    search_preprints,
    search_clinical_trials,
    search_variants
)

__all__ = [
    "bioresearcher",
    "bioanalyser", 
    "summarizer",
    "run_bio_agent_workflow_simple",
    "search_pubmed",
    "search_papers",
    "search_by_topic",
    "google_academic_search",
    "search_preprints",
    "search_clinical_trials",
    "search_variants"
]