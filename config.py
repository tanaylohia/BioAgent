# AIDEV-SECTION: Configuration
import os
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI Configuration
AZURE_CONFIG = {
    "endpoint": os.getenv("ENDPOINT_URL", "https://mandrakebioworkswestus.openai.azure.com/"),
    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
    "api_version": "2025-01-01-preview",
    "deployment_gpt4": os.getenv("DEPLOYMENT_NAME", "gpt-4.1"),
    "deployment_mini": os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME", "o4-mini")
}

# API Configuration
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000
}

# Cache Configuration
CACHE_CONFIG = {
    "ttl": 3600,  # 1 hour
    "max_size": 1000
}