# AIDEV-SECTION: Bio Agents Definition for SDK
"""
Agent definitions for the Bio Agent system using OpenAI Agents SDK.
Implements BioResearcher, BioAnalyser, and Summarizer with handoffs.
"""
import logging
from agents import Agent, ModelSettings
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from src.agents_sdk.azure_config import (
    gpt4_client, 
    o4mini_client, 
    GPT4_DEPLOYMENT, 
    O4MINI_DEPLOYMENT
)
from src.agents_sdk.sdk_tools import (
    search_pubmed,
    search_papers,
    search_by_topic,
    google_academic_search,
    search_preprints,
    search_clinical_trials,
    search_variants
)
from prompts import BIORESEARCHER_PROMPT, BIOANALYSER_PROMPT, SUMMARIZER_PROMPT
from src.agents_sdk.research_output import ResearchComplete, AnalysisResult, SynthesisReport

logger = logging.getLogger(__name__)

# AIDEV-NOTE: Define agents without handoffs first, then add handoffs after all are created
# This avoids circular reference issues

# BioResearcher Agent - Uses GPT-4.1 for comprehensive search
bioresearcher = Agent(
    name="BioResearcher",
    instructions=BIORESEARCHER_PROMPT,
    tools=[
        search_pubmed,
        search_papers,
        search_by_topic,
        google_academic_search,
        search_preprints,
        search_clinical_trials,
        search_variants
    ],
    model=OpenAIChatCompletionsModel(
        model=GPT4_DEPLOYMENT,
        openai_client=gpt4_client
    ),
    model_settings=ModelSettings(
        temperature=0.7,  # Default temperature for gpt-4.1
        max_completion_tokens=100000  # Maximum tokens for comprehensive output
    ),
    output_type=ResearchComplete  # Forces multiple searches before handoff
)

# BioAnalyser Agent - Uses o4-mini for analysis
bioanalyser = Agent(
    name="BioAnalyser",
    instructions=BIOANALYSER_PROMPT,
    model=OpenAIChatCompletionsModel(
        model=O4MINI_DEPLOYMENT,
        openai_client=o4mini_client
    ),
    model_settings=ModelSettings(
        temperature=0.7,
        max_completion_tokens=100000  # o4-mini supports large outputs
    ),
    output_type=AnalysisResult  # Structured analysis output
)

# Summarizer Agent - Uses o4-mini for final synthesis
summarizer = Agent(
    name="Summarizer",
    instructions=SUMMARIZER_PROMPT,
    model=OpenAIChatCompletionsModel(
        model=O4MINI_DEPLOYMENT,
        openai_client=o4mini_client
    ),
    model_settings=ModelSettings(
        temperature=0.7,  # Slightly lower for more consistent summaries
        max_completion_tokens=100000  # Maximum tokens for detailed synthesis
    )
    # No output_type - produces markdown text as final output
)

# Now set up handoffs to implement the feedback loop
# BioResearcher can hand off to BioAnalyser
bioresearcher.handoffs = [bioanalyser]

# BioAnalyser can hand off to either BioResearcher (for more search) or Summarizer (when satisfied)
bioanalyser.handoffs = [bioresearcher, summarizer]

# Summarizer is the final agent, no handoffs
summarizer.handoffs = []

logger.info("Bio agents initialized with handoffs:")
logger.info(f"  BioResearcher -> {[a.name for a in bioresearcher.handoffs]}")
logger.info(f"  BioAnalyser -> {[a.name for a in bioanalyser.handoffs]}")
logger.info(f"  Summarizer -> {[a.name for a in summarizer.handoffs]}")

# AIDEV-NOTE: The mandatory feedback loop is implemented via handoffs:
# 1. BioResearcher searches and hands off to BioAnalyser
# 2. BioAnalyser analyzes and ALWAYS suggests additional searches
# 3. BioAnalyser hands back to BioResearcher for more search
# 4. After second round, BioAnalyser hands off to Summarizer
# 5. Summarizer creates the final comprehensive response

# AIDEV-NOTE: Feedback loop is enforced via the updated BioAnalyser prompt
# which instructs it to always identify gaps on first analysis