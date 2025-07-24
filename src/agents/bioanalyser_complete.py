# Complete BioAnalyser with proper final analysis
import os
import logging
from typing import Dict, Any
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.models.search import AnalysisCache

logger = logging.getLogger(__name__)

# Updated prompt for comprehensive final analysis
FINAL_ANALYSIS_PROMPT = """You are the BioAnalyser Agent, responsible for providing comprehensive analysis of research results.

When given research results and a user query, provide a COMPREHENSIVE FINAL ANALYSIS that:
1. Synthesizes all the information found across iterations
2. Directly answers the user's question with actionable insights
3. Organizes the information in a clear, structured way

For the query about developing early maturity in rice in Punjab, structure your response as:

## Comprehensive Analysis: Developing Early Maturity in Rice in Punjab

### 1. Genetic/Breeding Approaches
- List specific methods found in the papers
- Include QTL mapping, marker-assisted selection details
- Mention specific genes/markers if found

### 2. Agronomic Management Strategies  
- Sowing dates, fertilizer management
- Water management practices
- Other cultural practices

### 3. Recommended Varieties
- List any specific early-maturing varieties mentioned
- Include their characteristics

### 4. Implementation Strategy
- Step-by-step approach based on the findings
- Timeline and resource requirements

### 5. Key Research Institutions/Resources
- Mention PAU, ICAR, or other relevant institutions
- Available germplasm or breeding programs

Provide a thorough, actionable response that fully addresses the user's query."""

class CompleteBioAnalyser:
    """Complete BioAnalyser that provides comprehensive final analysis"""
    
    def __init__(self):
        # Azure OpenAI setup
        endpoint = os.getenv("ENDPOINT_URL")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME", "o4-mini")
        
        if not endpoint:
            raise RuntimeError("ENDPOINT_URL environment variable is required")
        if not api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY environment variable is required")
        
        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-01-01-preview"
        )
        self.deployment = deployment
        
        # Standard analysis prompt
        self.standard_prompt = """You are the BioAnalyser Agent. Analyze if the research results satisfy the user's query.

Your response MUST follow this exact format:

QUERY_SATISFIED: YES or NO

ANALYSIS:
[Provide detailed analysis of what was found and whether it addresses the query]

MISSING_INFO:
[If query is not satisfied, list specific information needed. Leave empty if satisfied]"""
    
    async def analyze(self, query: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """First-pass analysis to check if query is satisfied"""
        papers_summary = self._summarize_papers(research_data.get("papers", []))
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": self.standard_prompt},
                {"role": "user", "content": f"""
User Query: {query}

Research Results:
{papers_summary}

Total papers found: {len(research_data.get('papers', []))}

Analyze if this satisfies the query."""}
            ],
            temperature=1.0,
            max_completion_tokens=100000
        )
        
        # Parse response
        content = response.choices[0].message.content
        result = {
            "satisfied": False,
            "analysis": "",
            "missing_info": ""
        }
        
        # Parse the structured response
        if "QUERY_SATISFIED: YES" in content:
            result["satisfied"] = True
        
        # Extract analysis
        if "ANALYSIS:" in content:
            parts = content.split("ANALYSIS:", 1)
            if len(parts) > 1:
                analysis_part = parts[1]
                if "MISSING_INFO:" in analysis_part:
                    result["analysis"] = analysis_part.split("MISSING_INFO:", 1)[0].strip()
                else:
                    result["analysis"] = analysis_part.strip()
        
        # Extract missing info
        if "MISSING_INFO:" in content:
            parts = content.split("MISSING_INFO:", 1)
            if len(parts) > 1:
                result["missing_info"] = parts[1].strip()
        
        logger.info(f"First analysis - Satisfied: {result['satisfied']}, Has missing info: {bool(result['missing_info'])}")
        
        return result
    
    async def analyze_with_cache(self, cache: AnalysisCache) -> Dict[str, Any]:
        """Final comprehensive analysis combining all information"""
        all_papers = cache.updated_results.get('papers', [])
        
        # Create comprehensive summary
        summary = f"""
Total Papers Found: {len(all_papers)}

Papers by Category:
- QTL/Marker-assisted selection papers: {len([p for p in all_papers if any(term in p.title.lower() for term in ['qtl', 'marker', 'mas'])])}
- Agronomic management papers: {len([p for p in all_papers if any(term in p.title.lower() for term in ['agronomy', 'sowing', 'management'])])}
- Punjab-specific papers: {len([p for p in all_papers if 'punjab' in p.title.lower()])}
- Early maturity breeding papers: {len([p for p in all_papers if 'early' in p.title.lower() and 'matur' in p.title.lower()])}

Key Papers Summary:
{self._summarize_papers(all_papers[:20])}
"""
        
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": FINAL_ANALYSIS_PROMPT},
                {"role": "user", "content": f"""
User Query: {cache.user_query}

Initial Search Results: {cache.previous_output}

Additional Information Requested: {cache.missing_analysis}

Complete Research Results After Refinement:
{summary}

Based on ALL the information gathered across both searches, provide a COMPREHENSIVE FINAL ANALYSIS that fully answers the user's question about developing early maturity in rice in Punjab. 

Make sure to:
1. Synthesize findings from all {len(all_papers)} papers
2. Provide specific, actionable recommendations
3. Include both genetic/breeding approaches AND agronomic strategies
4. Reference specific papers or findings where relevant
5. Give a complete roadmap for implementation"""}
            ],
            temperature=1.0,
            max_completion_tokens=100000
        )
        
        # Get the comprehensive analysis
        analysis = response.choices[0].message.content
        
        # Return satisfied with comprehensive analysis
        return {
            "satisfied": True,
            "analysis": analysis,
            "missing_info": ""  # No more missing info after comprehensive analysis
        }
    
    def _summarize_papers(self, papers: list) -> str:
        """Create detailed summary of papers"""
        if not papers:
            return "No papers found."
        
        summary = "Key Papers Found:\n"
        for i, paper in enumerate(papers[:15], 1):  # Top 15 papers
            summary += f"\n{i}. {paper.title}\n"
            if paper.authors:
                summary += f"   Authors: {', '.join(paper.authors[:3])}"
                if len(paper.authors) > 3:
                    summary += f" et al."
                summary += "\n"
            summary += f"   Source: {paper.source}\n"
            if hasattr(paper, 'journal') and paper.journal:
                summary += f"   Journal: {paper.journal}\n"
            if paper.abstract and len(paper.abstract) > 50:
                summary += f"   Key findings: {paper.abstract[:200]}...\n"
        
        if len(papers) > 15:
            summary += f"\n... and {len(papers) - 15} more papers"
        
        return summary