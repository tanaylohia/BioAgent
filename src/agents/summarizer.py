# AIDEV-SECTION: Summarizer Agent - Creates structured scientific responses
import os
import logging
from typing import Dict, Any, List
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

from src.models.paper import Paper
from prompts import SUMMARIZER_PROMPT
from src.utils.raw_logger import log_method_call, log_method_result, log_openai_request, log_openai_response

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SummarizerAgent:
    """Agent that creates structured scientific responses from search results"""
    
    def __init__(self):
        # Azure OpenAI setup - using o4-mini for summarization
        endpoint = os.getenv("ENDPOINT_URL")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME", "o4-mini")
        
        if not endpoint:
            raise ValueError("ENDPOINT_URL not set")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not set")
            
        logger.info(f"SummarizerAgent initializing with endpoint: {endpoint}, deployment: {deployment}")
        
        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            api_version="2025-01-01-preview",
            azure_endpoint=endpoint,
        )
        self.deployment = deployment
        
        # AIDEV-NOTE: Using centralized prompt from prompts.py
        self.system_prompt = SUMMARIZER_PROMPT
    
    async def summarize(self, 
                       query: str, 
                       papers: List[Paper], 
                       initial_analysis: str,
                       feedback_analysis: str = None,
                       tool_calls: List[Dict] = None,
                       stream_callback = None) -> str:
        """Create a structured scientific summary of all search results"""
        
        logger.info(f"Summarizing results for query: {query}")
        logger.info(f"Total papers to summarize: {len(papers)}")
        
        # Log method call
        log_method_call("SummarizerAgent", "summarize", {
            "query": query,
            "papers_count": len(papers),
            "has_initial_analysis": bool(initial_analysis),
            "has_feedback_analysis": bool(feedback_analysis),
            "tool_calls_count": len(tool_calls) if tool_calls else 0
        })
        
        # Create paper summaries
        paper_summaries = self._format_papers_for_summary(papers[:30])  # Top 30 papers
        
        # Create tool usage summary
        tool_summary = self._format_tool_summary(tool_calls or [])
        
        # Build the comprehensive context
        feedback_section = f"""Additional Analysis After Feedback:
{feedback_analysis}""" if feedback_analysis else ""
        
        context = f"""User Query: {query}

Initial Analysis Results:
{initial_analysis}

{feedback_section}

Total Papers Found: {len(papers)}

Tool Usage Summary:
{tool_summary}

Detailed Paper Summaries (Top 30):
{paper_summaries}

Based on ALL the above information, create a comprehensive scientific response that directly answers the user's query."""

        try:
            # Log OpenAI request
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": context}
            ]
            log_openai_request("SummarizerAgent", self.deployment, messages)
            
            # Use streaming if callback provided
            if stream_callback:
                response = await self.client.chat.completions.create(
                    model=self.deployment,
                    messages=messages,
                    temperature=1.0,  # Default temperature for this model
                    max_completion_tokens=100000,  # Increased for comprehensive analysis
                    stream=True
                )
                
                # Collect full response while streaming
                summary = ""
                async for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        if chunk.choices[0].delta.content:
                            chunk_content = chunk.choices[0].delta.content
                            summary += chunk_content
                            # Stream each chunk to frontend
                            await stream_callback(chunk_content)
                
                logger.info(f"Successfully created streamed summary, length: {len(summary)}")
            else:
                # Non-streaming response
                response = await self.client.chat.completions.create(
                    model=self.deployment,
                    messages=messages,
                    temperature=1.0,  # Default temperature for this model
                    max_completion_tokens=100000  # Increased for comprehensive analysis
                )
                
                # Log OpenAI response
                log_openai_response("SummarizerAgent", self.deployment, response)
                
                summary = response.choices[0].message.content
                logger.info(f"Successfully created summary, length: {len(summary)}")
            
            # Log method result
            log_method_result("SummarizerAgent", "summarize", {
                "summary_length": len(summary),
                "summary_preview": summary[:200] + "..." if len(summary) > 200 else summary
            })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}", exc_info=True)
            # Return a structured fallback
            return self._create_fallback_summary(query, papers, initial_analysis)
    
    def _format_papers_for_summary(self, papers: List[Paper]) -> str:
        """Format papers for inclusion in summary prompt"""
        if not papers:
            return "No papers found."
        
        summaries = []
        for i, paper in enumerate(papers, 1):
            authors_str = ", ".join(paper.authors[:3]) + " et al." if paper.authors else "Unknown"
            pub_date = paper.publication_date.strftime("%Y-%m") if paper.publication_date else "Unknown date"
            
            summary = f"""{i}. {paper.title}
   Authors: {authors_str}
   Source: {paper.source} | Published: {pub_date} | Citations: {paper.citations}
   Abstract: {paper.abstract[:500]}{"..." if len(paper.abstract) > 500 else ""}
   Link: {paper.hyperlink}
"""
            summaries.append(summary)
        
        return "\n".join(summaries)
    
    def _format_tool_summary(self, tool_calls: List[Dict]) -> str:
        """Format tool usage for summary"""
        if not tool_calls:
            return "No detailed tool information available."
        
        summary_lines = []
        for tc in tool_calls:
            summary_lines.append(
                f"- {tc.get('tool', 'Unknown tool')}: Found {tc.get('papers_found', 0)} papers "
                f"(Query: {tc.get('query', 'N/A')})"
            )
        
        return "\n".join(summary_lines)
    
    def _create_fallback_summary(self, query: str, papers: List[Paper], analysis: str) -> str:
        """Create a basic structured summary if API call fails"""
        return f"""## Executive Summary

Based on the search of {len(papers)} scientific papers, here is the analysis for your query: "{query}"

## Evidence Examined

- Total papers analyzed: {len(papers)}
- Sources: Various scientific databases
- Analysis provided by AI agents

## Key Findings

{analysis}

## Papers Found

Total of {len(papers)} relevant papers were identified. The most relevant papers include:

{self._format_top_papers_fallback(papers[:10])}

## Recommendations for Further Research

Based on the current findings, additional research may be needed to fully address all aspects of your query. 
Consider exploring the cited papers and their references for more detailed information.

---
*Note: This is a simplified summary. Some formatting features may be limited.*"""
    
    def _format_top_papers_fallback(self, papers: List[Paper]) -> str:
        """Format top papers for fallback summary"""
        lines = []
        for i, paper in enumerate(papers, 1):
            authors = ", ".join(paper.authors[:2]) + " et al." if len(paper.authors) > 2 else ", ".join(paper.authors)
            lines.append(f"{i}. {paper.title} - {authors} ({paper.source})")
        return "\n".join(lines)