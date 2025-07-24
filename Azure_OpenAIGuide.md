This sample demonstrates a basic call to the chat completion API for GPT 4.1 . The call is synchronous.

import os
from openai import AzureOpenAI


endpoint = "https://mandrakebioworkswestus.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview"
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

This sample demonstrates a basic call to the chat completion API for GPT o4-mini. The call is synchronous.

import os
from openai import AzureOpenAI

endpoint = "https://mandrakebioworkswestus.openai.azure.com/openai/deployments/o4-mini/chat/completions?api-version=2025-01-01-preview"
model_name = "o4-mini"
deployment = "o4-mini"

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
    max_completion_tokens=100000,
    model=deployment
)

print(response.choices[0].message.content)