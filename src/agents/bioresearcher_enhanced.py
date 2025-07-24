# Enhanced BioResearcher with proper paper parsing
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
from src.utils.paper_parser import parse_papers_from_tool_response
from prompts import BIORESEARCHER_PROMPT

logger = logging.getLogger(__name__)

class EnhancedBioResearcher:
    """Enhanced BioResearcher with proper paper parsing and detailed tracking"""
    
    def __init__(self):
        # Azure OpenAI setup
        endpoint = os.getenv("ENDPOINT_URL")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")
        
        if not endpoint:
            raise RuntimeError("ENDPOINT_URL environment variable is required for BioResearcher.")
        if not api_key:
            raise RuntimeError("AZURE_OPENAI_API_KEY environment variable is required for BioResearcher.")
        if not deployment:
            raise RuntimeError("DEPLOYMENT_NAME environment variable is required for BioResearcher.")
        
        logger.info(f"EnhancedBioResearcher initializing with endpoint: {endpoint}, deployment: {deployment}")
        
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
        """Execute comprehensive search with proper paper parsing"""
        logger.info(f"EnhancedBioResearcher: Starting search for '{query}'")
        
        # Initialize conversation with the query
        messages = [
            {"role": "system", "content": BIORESEARCHER_PROMPT},
            {"role": "user", "content": f"Search comprehensively for: {query}"}
        ]
        
        # Results collection with enhanced tracking
        all_results = {
            "papers": [],
            "raw_searches": {},
            "tool_calls": [],  # Detailed tool call tracking
            "analysis": "",
            "reasoning_trace": [],  # Reasoning for each round
            "conversation_history": [],  # Full conversation
            "tool_responses": [],  # All tool responses
            "paper_sources": {}  # Track which papers came from which tools
        }
        
        # Track unique papers by title to avoid duplicates
        seen_titles = set()
        
        # Allow up to 3 rounds of tool calls
        for round in range(3):
            try:
                logger.info(f"Round {round + 1}: Making API call...")
                
                # Make API call with function calling
                response = await self.client.chat.completions.create(
                    model=self.deployment,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=1.0,
                    max_completion_tokens=800
                )
                
                message = response.choices[0].message
                
                # Add assistant's response to conversation
                messages.append(message.model_dump())
                all_results["conversation_history"].append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": len(message.tool_calls) if message.tool_calls else 0,
                    "round": round + 1
                })
                
                # Store reasoning for this round
                if message.content:
                    all_results["reasoning_trace"].append({
                        "round": round + 1,
                        "reasoning": message.content,
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.info(f"Round {round + 1} reasoning: {message.content[:200]}...")
                
                # Check if there are tool calls
                if not message.tool_calls:
                    logger.info(f"Round {round + 1}: No more tool calls, search complete")
                    if message.content:
                        all_results["analysis"] = message.content
                    break
                
                # Process tool calls
                logger.info(f"Round {round + 1}: Processing {len(message.tool_calls)} tool calls")
                
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Calling tool: {function_name} with args: {function_args}")
                    
                    # Track the tool call
                    tool_call_record = {
                        "round": round + 1,
                        "tool": function_name,
                        "arguments": function_args,
                        "timestamp": datetime.now().isoformat(),
                        "call_id": tool_call.id
                    }
                    
                    # Execute the tool function
                    if function_name in self.tool_functions:
                        try:
                            # Call the actual tool function
                            tool_result = await self.tool_functions[function_name](**function_args)
                            
                            # Store raw results
                            all_results["raw_searches"][f"{function_name}_{round}_{tool_call.id}"] = tool_result
                            
                            # Parse papers using the enhanced parser
                            papers = parse_papers_from_tool_response(tool_result, function_name)
                            logger.info(f"Tool {function_name} returned {len(papers)} parsed papers")
                            
                            # Add unique papers to results
                            new_papers_count = 0
                            for paper in papers:
                                if paper.title not in seen_titles:
                                    seen_titles.add(paper.title)
                                    all_results["papers"].append(paper)
                                    
                                    # Track source
                                    if function_name not in all_results["paper_sources"]:
                                        all_results["paper_sources"][function_name] = []
                                    all_results["paper_sources"][function_name].append(paper.title)
                                    new_papers_count += 1
                            
                            logger.info(f"Added {new_papers_count} new unique papers from {function_name}")
                            
                            # Create tool response message
                            tool_response = {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps({
                                    "papers_found": len(papers),
                                    "new_papers_added": new_papers_count,
                                    "total_papers_now": len(all_results["papers"])
                                })
                            }
                            
                            # Track the response
                            tool_call_record["response_summary"] = {
                                "papers_found": len(papers),
                                "new_papers_added": new_papers_count,
                                "sample_titles": [p.title[:100] for p in papers[:3]]
                            }
                            
                        except Exception as e:
                            logger.error(f"Error calling {function_name}: {e}")
                            import traceback
                            traceback.print_exc()
                            
                            tool_response = {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": f"Error: {str(e)}"
                            }
                            tool_call_record["error"] = str(e)
                    else:
                        tool_response = {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": f"Error: Unknown function {function_name}"
                        }
                        tool_call_record["error"] = f"Unknown function {function_name}"
                    
                    # Add to tracking
                    all_results["tool_calls"].append(tool_call_record)
                    all_results["tool_responses"].append(tool_response)
                    
                    # Add tool response to messages
                    messages.append(tool_response)
                
                logger.info(f"Round {round + 1} complete. Total papers so far: {len(all_results['papers'])}")
                
            except Exception as e:
                logger.error(f"Error in round {round + 1}: {e}")
                all_results["reasoning_trace"].append({
                    "round": round + 1,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                break
        
        # Final summary
        logger.info(f"Search complete. Total unique papers found: {len(all_results['papers'])}")
        logger.info(f"Total tool calls made: {len(all_results['tool_calls'])}")
        logger.info(f"Papers by source: {json.dumps({k: len(v) for k, v in all_results['paper_sources'].items()})}")
        
        return all_results