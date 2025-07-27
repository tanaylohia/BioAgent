#!/usr/bin/env python3
"""
Run the Bio Agent Backend with regular Agents implementation.
This starts the regular agents version of the API on port 8000.
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
    """Start the regular agents server"""
    port = int(os.getenv("PORT", 5000))
    
    print(f"""
    ==========================================
    Bio Agent Backend - Regular Agents Implementation
    ==========================================
    
    Using standard agent orchestration (non-SDK)
    Port: {port}
    
    Endpoints:
    - GET  /              - API info
    - POST /search        - Start search
    - WS   /ws/{{task_id}} - Progress updates
    - GET  /health        - Health check
    - GET  /task/{{task_id}} - Get task status
    
    Starting server...
    """)
    
    # Run the regular version
    uvicorn.run(
        "src.orchestrator.main:app",
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