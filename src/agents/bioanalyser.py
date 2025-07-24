# Required environment variables:
#   ENDPOINT_URL
#   AZURE_OPENAI_API_KEY
#   AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME (should be 'o4-mini' for GPT-4o Mini)

# AIDEV-SECTION: BioAnalyser Agent
import os
import logging
from typing import Dict, Any
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.models.search import AnalysisCache
from prompts import BIOANALYSER_PROMPT

logger = logging.getLogger(__name__)

class BioAnalyser:
    """Agent that analyzes search results and determines satisfaction"""
    
    def __init__(self):
        # Azure OpenAI setup - using o4-mini for analysis
        endpoint = os.getenv("ENDPOINT_URL")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        # Use 'o4-mini' as the deployment name for GPT-4o Mini
        deployment = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME", "o4-mini")
        if not endpoint:
            raise RuntimeError("ENDPOINT_URL environment variable is required for BioAnalyser.")
        if not api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY environment variable is required for BioAnalyser.")
        if not deployment:
            raise RuntimeError("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME environment variable is required for BioAnalyser.")
        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-01-01-preview"
        )
        self.deployment = deployment
    
    async def analyze(self, query: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze if research satisfies the query"""
        # Prepare research summary
        papers_summary = self._summarize_papers(research_data.get("papers", []))
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": BIOANALYSER_PROMPT},
                {"role": "user", "content": f"""
User Query: {query}

Research Results:
{papers_summary}

Total papers found: {len(research_data.get('papers', []))}

Analyze if this satisfies the query. Follow the output format specified."""}
            ],
            temperature=1.0,  # Use default temperature
            max_completion_tokens=100000  # As per Azure guide for o4-mini
        )
        
        # Parse response
        content = response.choices[0].message.content
        lines = content.strip().split('\n')
        
        result = {
            "satisfied": False,
            "analysis": "",
            "missing_info": ""
        }
        
        for line in lines:
            if line.startswith("QUERY_SATISFIED:"):
                result["satisfied"] = "YES" in line
            elif line.startswith("ANALYSIS:"):
                result["analysis"] = line.replace("ANALYSIS:", "").strip()
            elif line.startswith("MISSING_INFO:"):
                result["missing_info"] = line.replace("MISSING_INFO:", "").strip()
        
        # Get full analysis text
        if "ANALYSIS:" in content:
            parts = content.split("ANALYSIS:")
            if len(parts) > 1:
                analysis_part = parts[1]
                # Check if MISSING_INFO exists before splitting
                if "MISSING_INFO:" in analysis_part:
                    result["analysis"] = analysis_part.split("MISSING_INFO:")[0].strip()
                else:
                    result["analysis"] = analysis_part.strip()
        
        return result
    
    async def analyze_with_cache(self, cache: AnalysisCache) -> Dict[str, Any]:
        """Final analysis with cached context and new results"""
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": BIOANALYSER_PROMPT},
                {"role": "user", "content": f"""
User Query: {cache.user_query}

Previous Analysis: {cache.previous_output}

Missing Information Requested: {cache.missing_analysis}

Additional Results Found:
{self._summarize_papers(cache.updated_results.get('papers', []))}

Provide final comprehensive analysis combining all information."""}
            ],
            temperature=1.0,  # Use default temperature
            max_completion_tokens=100000,  # As per Azure guide for o4-mini
            stream=True  # Stream the final output
        )
        
        # Collect streamed response
        analysis = ""
        async for chunk in response:
            # Check if choices exist and have content
            if chunk.choices and len(chunk.choices) > 0:
                if chunk.choices[0].delta.content:
                    analysis += chunk.choices[0].delta.content
        
        return {
            "satisfied": True,
            "analysis": analysis
        }
    
    def _summarize_papers(self, papers: list) -> str:
        """Create a summary of papers for analysis"""
        if not papers:
            return "No papers found."
        
        summary = "Key Papers Found:\n"
        for i, paper in enumerate(papers[:5], 1):  # Top 5 papers
            summary += f"\n{i}. {paper.title}\n"
            summary += f"   Authors: {', '.join(paper.authors[:3])}...\n" if paper.authors else ""
            summary += f"   Source: {paper.source}\n"
            if paper.abstract:
                summary += f"   Abstract: {paper.abstract[:200]}...\n"
        
        if len(papers) > 5:
            summary += f"\n... and {len(papers) - 5} more papers"
        
        return summary