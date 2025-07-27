#!/usr/bin/env python3
"""
Run the Bio Agent Backend with OpenAI Agents SDK implementation.
This starts the SDK version of the API on port 6001.
"""
import os
import sys
import uvicorn
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Start the SDK server"""
    port = int(os.getenv("SDK_PORT", 6001))
    
    print(f"""
    ==========================================
    Bio Agent Backend - SDK Implementation
    ==========================================
    
    Using OpenAI Agents SDK for orchestration
    Port: {port}
    
    Endpoints:
    - GET  /              - API info
    - POST /search        - Start search
    - WS   /ws/{{task_id}} - Progress updates
    - GET  /health        - Health check
    
    Starting server...
    """)
    
    # Run the SDK version
    uvicorn.run(
        "src.orchestrator.main_sdk:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
        # WebSocket settings
        ws_ping_interval=20,
        ws_ping_timeout=10
    )


if __name__ == "__main__":
    main()