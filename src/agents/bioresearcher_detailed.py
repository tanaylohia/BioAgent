# Enhanced BioResearcher with detailed tool tracking
# Required environment variables:
#   ENDPOINT_URL
#   AZURE_OPENAI_API_KEY
#   DEPLOYMENT_NAME (should be 'gpt-4.1' for GPT-4.1)

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

class DetailedBioResearcher:
    """Enhanced BioResearcher that tracks all tool calls and responses"""
    
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
        
        logger.info(f"DetailedBioResearcher initializing with endpoint: {endpoint}, deployment: {deployment}")
        
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
        """Execute comprehensive search with detailed tracking"""
        logger.info(f"DetailedBioResearcher: Starting search for '{query}'")
        
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
            "tool_responses": []  # All tool responses
        }
        
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
                            
                            # Extract papers if present
                            if isinstance(tool_result, dict) and "papers" in tool_result:
                                papers = tool_result["papers"]
                                logger.info(f"Tool {function_name} returned {len(papers)} papers")
                                
                                # Convert to Paper objects and add to results
                                for paper_data in papers:
                                    if isinstance(paper_data, dict):
                                        paper = Paper(**paper_data)
                                        if paper not in all_results["papers"]:
                                            all_results["papers"].append(paper)
                            
                            # Create tool response message
                            tool_response = {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": function_name,
                                "content": json.dumps(tool_result, default=str)
                            }
                            
                            # Track the response
                            tool_call_record["response"] = tool_result
                            tool_call_record["papers_found"] = len(tool_result.get("papers", []))
                            
                        except Exception as e:
                            logger.error(f"Error calling {function_name}: {e}")
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
        
        # Store full conversation history
        all_results["conversation_history"] = messages
        
        logger.info(f"Search complete. Total papers found: {len(all_results['papers'])}")
        logger.info(f"Total tool calls made: {len(all_results['tool_calls'])}")
        
        return all_results