# AIDEV-SECTION: Azure OpenAI Configuration for SDK
"""
Azure OpenAI configuration for the OpenAI Agents SDK.
Sets up clients for different models (GPT-4.1 and o4-mini).
"""
import os
import logging
from openai import AsyncAzureOpenAI
from agents import set_default_openai_client, set_default_openai_api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Get Azure OpenAI configuration
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
GPT4_DEPLOYMENT = os.getenv("DEPLOYMENT_NAME", "gpt-4.1")
O4MINI_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME", "o4-mini")

if not ENDPOINT_URL or not API_KEY:
    raise ValueError("ENDPOINT_URL and AZURE_OPENAI_API_KEY must be set")

# Create client for GPT-4.1
gpt4_client = AsyncAzureOpenAI(
    api_key=API_KEY,
    api_version="2025-01-01-preview",
    azure_endpoint=ENDPOINT_URL,
)

# Create client for o4-mini (same endpoint, different deployment)
o4mini_client = AsyncAzureOpenAI(
    api_key=API_KEY,
    api_version="2025-01-01-preview",
    azure_endpoint=ENDPOINT_URL,
)

# Set default client (we'll override per agent)
set_default_openai_client(gpt4_client)

# Use Chat Completions API as Azure doesn't support Responses API yet
set_default_openai_api("chat_completions")

logger.info(f"Azure OpenAI configured with endpoint: {ENDPOINT_URL}")
logger.info(f"GPT-4.1 deployment: {GPT4_DEPLOYMENT}")
logger.info(f"o4-mini deployment: {O4MINI_DEPLOYMENT}")

# Export deployment names for use in agents
__all__ = [
    "gpt4_client",
    "o4mini_client",
    "GPT4_DEPLOYMENT",
    "O4MINI_DEPLOYMENT"
]