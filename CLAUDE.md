# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT: Use Anchor comments

Add specially formatted comments throughout the codebase, where appropriate, for yourself as inline knowledge that can be easily `grep`ped for.

- Use `AIDEV-NOTE:`, `AIDEV-TODO:`, `AIDEV-QUESTION:`, or `AIDEV-SECTION:` as prefix as appropriate.

- *Important:* Before scanning files, always first try to grep for existing 

- Update relevant anchors, after finishing any task. For example, after moving the WebSocket route above CORS middleware in src/orchestrator/main_fixed.py, add or update an AIDEV-NOTE explaining the rationale (see below).

- Make sure to add relevant anchor comments, whenever a file or piece of code is:

  * too complex, or
  * very important, or
  * could have a bug



When responding to user instructions, the AI assistant (Claude, Cursor, GPT, etc.) should follow this process to ensure clarity, correctness, and maintainability:

1. **Consult Relevant Guidance**: When the user gives an instruction, consult the relevant instructions from `CLAUDE.md` files (both root and directory-specific) for the request.
2. **Clarify Ambiguities**: Based on what you could gather, see if there's any need for clarifications. If so, ask the user targeted questions before proceeding.
3. **Break Down & Plan**: Break down the task at hand and chalk out a rough plan for carrying it out, referencing project conventions and best practices.
4. **Trivial Tasks**: If the plan/request is trivial, go ahead and get started immediately.
5. **Non-Trivial Tasks**: Otherwise, present the plan to the user for review and iterate based on their feedback.
6. **Track Progress**: Use a to-do list (internally, or optionally in a `TODOS.md` file) to keep track of your progress on multi-step or complex tasks.
7. **If Stuck, Re-plan**: If you get stuck or blocked, return to step 3 to re-evaluate and adjust your plan.
8. **Update Documentation**: Once the user's request is fulfilled, update relevant anchor comments (`AIDEV-NOTE`, etc.) and `CLAUDE.md` files in the files and directories you touched.
9. **User Review**: After completing the task, ask the user to review what you've done, and repeat the process as needed.
10. **Session Boundaries**: If the user's request isn't directly related to the current context and can be safely started in a fresh session, suggest starting from scratch to avoid context confusion.


*EXTREMELY IMPORTANT* Master Guidelines - Go through them and take them into consideration.  

We will be using Azure OpenAI Endpoints & DeepSeek R1 and here are the sample codes- 

For GPT 4.1 -
Target URL- |https://mandrakebioworkswestus.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview

import os
from openai import AzureOpenAI

endpoint = "https://mandrakebioworkswestus.openai.azure.com/"
model_name = "gpt-4.1"
deployment = "gpt-4.1"

subscription_key = "<your-api-key>"
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    max_completion_tokens=800,
    temperature=1.0,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    model=deployment
)

print(response.choices[0].message.content)


For GPT o4- Mini- 
target URL- https://mandrakebioworkswestus.openai.azure.com/openai/deployments/o4-mini/chat/completions?api-version=2025-01-01-preview

import os
from openai import AzureOpenAI

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint="https://mandrakebioworkswestus.openai.azure.com/",
    api_key=subscription_key
)

*SUPER IMP:* https://platform.openai.com/docs/guides/tools?api-mode=responses Look at this link indepth and sublinks as well to follow best practices for tool calling, funciton calling etc for OPENAI APIs..  

For DeepSeek R1, here is the sample code- 

Target URL- https://mandrake-resource.services.ai.azure.com/models/chat/completions?api-version=2024-05-01-preview

import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = "https://mandrake-resource.services.ai.azure.com/models"
model_name = "DeepSeek-R1-0528"

client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential("<API_KEY>"),
    api_version="2024-05-01-preview"
)

response = client.complete(
    messages=[
        SystemMessage(content="You are a helpful assistant."),
        UserMessage(content="I am going to Paris, what should I see?"),
    ],
    max_tokens=2048,
    model=model_name
)

print(response.choices[0].message.content)

For DeepSeek R1, we will need a seperate Azure API key as this has a seperate deployment. So define two keys here. 

Now for the project- 

The *orchestrator* won't be an agent. It will just facilitate routing of the user query to specific agents as per the toggles. that the user has selected. 

*WebSearch Agent*- 
There will be total 2 agents here. 

1- BioReseacher- The user query will be received by this agent and it will use the set of tools available at its disposal to do a detailed search and analysis on the given topic. It will pull in as much info from all the tools available at its disposal. It will think hard here. It will assess the query and understand what is the user trying to ask and what all searches we will need to do. We need to properly define all academic research tools available such as the Biorxiv, arxiv, pubmed, semantic scholar etc so that it can call multiple tools efficiently in a proper way. Look at the readme of the MCP and define it. This agent will be 'GPT 4.1'  It will pass all of these info to the Analyser agent. 

Info about websearch -
https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses

2- BioAnalyser- This will be a GPT o4-mini. Once the BioResearcher tool is done, it will pass the detailed dump along with the user query to the BioAnalyser Agent. It will look at the info and think hard if the current analysis satisfactorily solves the user query. Think about different options to faciliate this. There will be two scenarios here - a) Query is satisfactorily solved- then the output will be sent to the user. b) Query isn't solved- then the agent will generate what needs to be researched again and send the necesssary missing info needed back to the Bioresearcher agent and then present the analysis with updated info. This needs to be stored in a cache. So that when the next info is received from the BioResesearcher, the Agent gets the User query, previous output, missing analysis from its end and the updated search results and then provides a detailed analysis. 
This loop will be run just once and after this the agent will stream the output to the user. 

One key element here is that all the research papers received from the tools here will need to be captured seperately. This will be shown to the user at the frontend later. - Paper Title, Abstract, Authors, Citations, Date of Publishing, HyperLink to the paper. Please see if I missed anything. 

## Example Anchor Update

- AIDEV-NOTE: WebSocket route registered before CORS middleware to avoid handshake issues (see CLAUDE.md guidance)

## Recent Fixes

- 2024-06-XX: WebSocket route in src/orchestrator/main_fixed.py is now registered before CORS middleware. This prevents CORS from interfering with WebSocket upgrades and resolves HTTP 500 errors before the handler is reached. See AIDEV-NOTE in that file for details.
