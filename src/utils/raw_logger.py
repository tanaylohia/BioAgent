# AIDEV-SECTION: Raw logging for agent debugging
"""
Simple raw logger for capturing all agent interactions
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Create logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log file with timestamp
LOG_FILE = LOG_DIR / f"raw_agent_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

def log_raw(data):
    """Write raw log entry"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            entry = {
                "timestamp": datetime.now().isoformat(),
                **data
            }
            json.dump(entry, f, ensure_ascii=False, default=str)
            f.write('\n')
    except Exception as e:
        print(f"Logging error: {e}")

def log_method_call(agent, method, inputs):
    """Log agent method call"""
    log_raw({
        "type": "METHOD_CALL",
        "agent": agent,
        "method": method,
        "inputs": inputs
    })

def log_method_result(agent, method, outputs):
    """Log agent method result"""
    log_raw({
        "type": "METHOD_RESULT", 
        "agent": agent,
        "method": method,
        "outputs": outputs
    })

def log_openai_request(agent, model, messages, tools=None):
    """Log Azure OpenAI API request"""
    log_raw({
        "type": "OPENAI_REQUEST",
        "agent": agent,
        "model": model,
        "messages": messages,
        "tools_count": len(tools) if tools else 0,
        "tools": [t.get("function", {}).get("name") for t in tools] if tools else []
    })

def log_openai_response(agent, model, response):
    """Log Azure OpenAI API response"""
    data = {
        "type": "OPENAI_RESPONSE",
        "agent": agent,
        "model": model
    }
    
    # Extract response details
    if hasattr(response, 'choices') and response.choices:
        choice = response.choices[0]
        data["finish_reason"] = choice.finish_reason
        data["content"] = choice.message.content if choice.message.content else None
        data["tool_calls"] = []
        
        if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                data["tool_calls"].append({
                    "id": tc.id,
                    "function": tc.function.name,
                    "arguments": tc.function.arguments
                })
    
    # Add usage if available
    if hasattr(response, 'usage'):
        data["usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    
    log_raw(data)

# Log initialization
log_raw({
    "type": "LOG_INIT",
    "message": f"Raw logging initialized. Log file: {LOG_FILE}"
})

print(f"Raw logging enabled: {LOG_FILE}")