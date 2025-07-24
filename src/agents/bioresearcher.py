# Required environment variables:
#   ENDPOINT_URL
#   AZURE_OPENAI_API_KEY
#   DEPLOYMENT_NAME (should be 'gpt-4.1' for GPT-4.1)

# AIDEV-SECTION: BioResearcher Agent with OpenAI Function Calling
import os
import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.tools.tool_definitions import TOOL_DEFINITIONS
from src.tools import search_tools
from src.models.paper import Paper
from prompts import BIORESEARCHER_PROMPT

logger = logging.getLogger(__name__)

class BioResearcher:
    """Agent that performs comprehensive biomedical searches using OpenAI function calling"""
    
    def __init__(self):
        # Azure OpenAI setup
        endpoint = os.getenv("ENDPOINT_URL")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        # Use 'gpt-4.1' as the deployment name for GPT-4.1
        deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")
        if not endpoint:
            raise RuntimeError("ENDPOINT_URL environment variable is required for BioResearcher.")
        if not api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY environment variable is required for BioResearcher.")
        if not deployment:
            raise RuntimeError("DEPLOYMENT_NAME environment variable is required for BioResearcher.")
        
        logger.info(f"BioResearcher initializing with endpoint: {endpoint}, deployment: {deployment}")
        
        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2025-01-01-preview"
        )
        self.deployment = deployment
        
        # Map function names to actual implementations
        self.tool_functions = {
            "google_academic_search": search_tools.google_academic_search,
            "search_papers": search_tools.search_papers,
            "fetch_paper_details": search_tools.fetch_paper_details,
            "search_by_topic": search_tools.search_by_topic,
            "search_pubmed": search_tools.search_pubmed,
            "search_preprints": search_tools.search_preprints,
            "search_clinical_trials": search_tools.search_clinical_trials,
            "search_variants": search_tools.search_variants,
        }
    
    async def search(self, query: str) -> Dict[str, Any]:
        """Execute comprehensive search using OpenAI function calling"""
        logger.info(f"BioResearcher: Starting search for '{query}'")
        
        # Initialize conversation with the query
        messages = [
            {"role": "system", "content": BIORESEARCHER_PROMPT},
            {"role": "user", "content": f"Search comprehensively for: {query}"}
        ]
        
        # Results collection
        all_results = {
            "papers": [],
            "raw_searches": {},
            "tool_calls": [],
            "analysis": "",
            "reasoning_trace": []  # Store reasoning for each round
        }
        
        # Allow up to 3 rounds of tool calls (reduced from 5)
        for round in range(3):
            try:
                # Make API call with function calling
                # AIDEV-NOTE: Fixed to use async client to prevent event loop blocking
                response = await self.client.chat.completions.create(
                    model=self.deployment,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",  # Let GPT decide which tools to use
                    temperature=1.0,  # gpt-4.1 only supports default temperature
                    max_completion_tokens=800  # As per Azure guide for gpt-4.1
                )
                
                message = response.choices[0].message
                
                # Add assistant's response to conversation
                messages.append(message.model_dump())
                
                # Store reasoning for this round
                if message.content:
                    all_results["reasoning_trace"].append({
                        "round": round,
                        "reasoning": message.content,
                        "tools_called": len(message.tool_calls) if message.tool_calls else 0
                    })
                
                # Check if assistant wants to call tools
                if message.tool_calls:
                    logger.info(f"\n=== Round {round} Tool Calls ===")
                    logger.info(f"Assistant reasoning: {message.content if message.content else 'No explicit reasoning'}")
                    logger.info(f"Number of tools to call: {len(message.tool_calls)}")
                    
                    # Execute all tool calls in parallel
                    tool_results = await self._execute_tool_calls(message.tool_calls)
                    
                    # Add tool results to conversation
                    for tool_call, result in zip(message.tool_calls, tool_results):
                        # Store raw results
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        logger.info(f"Tool: {tool_name}, Args: {tool_args}")
                        
                        all_results["raw_searches"][f"{tool_name}_{round}"] = result
                        all_results["tool_calls"].append({
                            "tool": tool_name,
                            "arguments": tool_args,
                            "round": round
                        })
                        
                        # Extract papers from results
                        papers = self._extract_papers_from_result(result, tool_name)
                        all_results["papers"].extend(papers)
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)[:5000]  # Limit size
                        })
                else:
                    # No more tool calls, get final analysis
                    if message.content:
                        all_results["analysis"] = message.content
                    break
                    
            except Exception as e:
                logger.error(f"Error in function calling round {round}: {e}")
                break
        
        # Deduplicate papers
        all_results["papers"] = self._deduplicate_papers(all_results["papers"])
        
        return all_results
    
    async def search_specific(self, missing_info: str) -> Dict[str, Any]:
        """Search for specific missing information"""
        logger.info(f"BioResearcher: Searching for missing info: {missing_info}")
        
        messages = [
            {"role": "system", "content": BIORESEARCHER_PROMPT},
            {"role": "user", "content": f"Find specific information about: {missing_info}"}
        ]
        
        # Similar process but focused on missing info
        return await self.search(missing_info)
    
    async def _execute_tool_calls(self, tool_calls) -> List[Dict[str, Any]]:
        """Execute multiple tool calls in parallel"""
        import asyncio
        
        async def execute_single_tool(tool_call):
            try:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                logger.info(f"Executing {function_name} with args: {arguments}")
                
                # Handle web_search specially (it's built into OpenAI)
                if function_name == "web_search":
                    # Web search is handled by OpenAI internally
                    return {"info": "Web search executed by OpenAI"}
                
                # Execute our custom tools
                if function_name in self.tool_functions:
                    result = await self.tool_functions[function_name](**arguments)
                    return result
                else:
                    return {"error": f"Unknown tool: {function_name}"}
                    
            except Exception as e:
                logger.error(f"Error executing {tool_call.function.name}: {e}")
                return {"error": str(e)}
        
        # Execute all tools in parallel using asyncio.gather
        # AIDEV-NOTE: Running all tools in parallel as per user request
        logger.info(f"Executing {len(tool_calls)} tools in parallel")
        results = await asyncio.gather(*[execute_single_tool(tc) for tc in tool_calls])
        
        return results
    
    def _extract_papers_from_result(self, result: Dict[str, Any], tool_name: str) -> List[Paper]:
        """Extract paper metadata from tool results"""
        papers = []
        
        try:
            # Handle different result formats
            if "results" in result:
                # Most tools return results in this format
                for item in result.get("results", []):
                    paper = self._create_paper_from_item(item, tool_name)
                    if paper:
                        papers.append(paper)
            
            elif "semantic_scholar" in result:
                # search_papers returns separated sources
                for item in result.get("semantic_scholar", []):
                    paper = self._create_paper_from_item(item, "Semantic Scholar")
                    if paper:
                        papers.append(paper)
                        
                for item in result.get("crossref", []):
                    paper = self._create_paper_from_item(item, "CrossRef")
                    if paper:
                        papers.append(paper)
            
            elif "biorxiv" in result:
                # Preprints return separated servers
                for item in result.get("biorxiv", []):
                    paper = self._create_paper_from_item(item, "bioRxiv")
                    if paper:
                        papers.append(paper)
                        
                for item in result.get("medrxiv", []):
                    paper = self._create_paper_from_item(item, "medRxiv")
                    if paper:
                        papers.append(paper)
                        
        except Exception as e:
            logger.error(f"Error extracting papers from {tool_name}: {e}")
        
        return papers
    
    def _create_paper_from_item(self, item: Dict[str, Any], source: str) -> Optional[Paper]:
        """Create a Paper object from a result item"""
        try:
            # Handle different field names
            title = item.get("title") or item.get("briefTitle") or ""
            
            # Handle authors - could be string or list
            authors = item.get("authors", [])
            if isinstance(authors, str):
                authors = [authors]
            elif not isinstance(authors, list):
                authors = []
            
            # Handle Google search results
            abstract = item.get("abstract") or item.get("summary") or item.get("snippet") or ""
            url = item.get("url") or item.get("link") or item.get("doi") or ""
            publication_date = item.get("year") or item.get("date") or item.get("pubYear") or item.get("publication_date")
            
            # Create Paper object
            paper = Paper(
                title=title,
                abstract=abstract,
                authors=authors[:10],  # Limit authors
                citations=item.get("citations", 0),
                publication_date=self._parse_date(publication_date),
                hyperlink=url,
                source=source,
                doi=item.get("doi"),
                journal=item.get("journal") or item.get("venue") or item.get("source")
            )
            
            return paper
            
        except Exception as e:
            logger.error(f"Error creating paper: {e}")
            return None
    
    def _parse_date(self, date_value):
        """Parse various date formats"""
        if not date_value:
            return None
            
        try:
            if isinstance(date_value, int):
                return datetime(date_value, 1, 1)
            elif isinstance(date_value, str):
                # Try to extract year
                import re
                year_match = re.search(r'\d{4}', str(date_value))
                if year_match:
                    return datetime(int(year_match.group()), 1, 1)
        except:
            pass
            
        return None
    
    def _deduplicate_papers(self, papers: List[Paper]) -> List[Paper]:
        """Remove duplicate papers based on title and DOI"""
        seen = set()
        unique_papers = []
        
        for paper in papers:
            # Create unique key
            key = (paper.title.lower(), paper.doi) if paper.doi else paper.title.lower()
            
            if key not in seen:
                seen.add(key)
                unique_papers.append(paper)
        
        return unique_papers