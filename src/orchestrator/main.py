# AIDEV-SECTION: Orchestrator with WebSocket Support
# AIDEV-NOTE: WebSocket Handshake Timeout Analysis
# The WebSocket connection timeout during opening handshake can be caused by:
# 1. Module-based execution (-m flag) vs direct script execution differences
# 2. CORS middleware not properly handling WebSocket upgrade requests
# 3. Missing subprotocol negotiation during WebSocket accept
# 4. Firewall/antivirus blocking WebSocket connections on Windows
# 5. Event loop conflicts between FastAPI and uvicorn when using module execution
# Current workarounds:
# - Use run_backend_ws_fix.py which configures uvicorn properly
# - Ensure single worker mode for WebSocket compatibility
# - Proper ping/pong intervals configured (20s ping, 10s timeout)

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict

from src.models.search import SearchRequest, SearchResult
from src.agents.search_agent import SearchAgent
from src.utils.websocket_manager import ws_manager

# Setup
app = FastAPI(title="Bio Agent API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize agents lazily
search_agent = None

def get_search_agent():
    global search_agent
    if search_agent is None:
        logger.info("Initializing SearchAgent...")
        search_agent = SearchAgent()
    return search_agent

# Active tasks tracking
active_tasks: Dict[str, Dict] = {}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/debug/config")
def debug_config():
    """Debug endpoint to check current configuration"""
    import os
    return {
        "status": "debug",
        "env": {
            "ENDPOINT_URL": os.getenv("ENDPOINT_URL"),
            "DEPLOYMENT_NAME": os.getenv("DEPLOYMENT_NAME"),
            "AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME": os.getenv("AZURE_OPENAI_GPT4O_DEPLOYMENT_NAME"),
            "API_KEY_SET": bool(os.getenv("AZURE_OPENAI_API_KEY"))
        },
        "loaded_at": datetime.utcnow().isoformat()
    }

@app.get("/debug/test-search")
async def test_search():
    """Test endpoint to run a simple search synchronously"""
    try:
        from src.tools.search_tools import search_papers
        result = await asyncio.wait_for(
            search_papers("test", limit=2),
            timeout=5.0
        )
        return {"status": "success", "result": result}
    except asyncio.TimeoutError:
        return {"status": "timeout", "message": "Search timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/search")
async def search(request: SearchRequest) -> Dict:
    """Route query to search agent if search toggle is on"""
    try:
        if request.toggles.get("search", True):
            # Generate task ID
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            
            # Store task info
            active_tasks[task_id] = {
                "status": "in_progress",
                "query": request.query,
                "started_at": datetime.utcnow()
            }
            
            # Start search in background with proper error handling
            task = asyncio.create_task(execute_search(task_id, request))
            
            # Store the task reference to prevent garbage collection
            if not hasattr(app.state, "background_tasks"):
                app.state.background_tasks = set()
            app.state.background_tasks.add(task)
            task.add_done_callback(lambda t: app.state.background_tasks.discard(t))
            
            return {
                "task_id": task_id,
                "status": "in_progress",
                "message": "Search started"
            }
        else:
            raise HTTPException(400, "No agents enabled")
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(500, str(e))

async def execute_search(task_id: str, request: SearchRequest):
    """Execute search and send updates via WebSocket"""
    try:
        logger.info(f"Starting search for task {task_id}: {request.query}")
        
        # Send initial progress
        await send_ws_update(task_id, "progress", {
            "progress": 10,
            "current_step": "Initializing search",
            "message": "Starting BioResearcher agent"
        })
        
        logger.info(f"Executing search agent for: {request.query}")
        
        # Create progress callback
        async def progress_callback(message: str, progress: int):
            await send_ws_update(task_id, "progress", {
                "progress": progress,
                "current_step": message,
                "message": message
            })
        
        # Execute search with progress callback
        agent = get_search_agent()
        result = await agent.execute(request.query, progress_callback)
        
        logger.info(f"Search completed for task {task_id}")
        # Store result
        active_tasks[task_id]["result"] = result
        active_tasks[task_id]["status"] = "completed"
        
        # Send final result
        await send_ws_update(task_id, "result", result.dict())
        
    except Exception as e:
        logger.error(f"Search execution error for task {task_id}: {e}", exc_info=True)
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = str(e)
        await send_ws_update(task_id, "error", {"error": str(e)})

async def send_ws_update(task_id: str, msg_type: str, data: Dict):
    """Send update via WebSocket if connected"""
    await ws_manager.send_json(task_id, {
        "type": msg_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    })

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint - minimal implementation"""
    # AIDEV-NOTE: Minimal WebSocket to debug HTTP 500 issue
    await websocket.accept()
    
    try:
        # Send initial message
        await websocket.send_json({"type": "connected", "task_id": task_id})
        
        # Add to manager for updates
        ws_manager.active_connections[task_id] = websocket
        
        # Keep alive until client disconnects
        while True:
            try:
                data = await websocket.receive_text()
                # Echo back
                await websocket.send_text(f"Echo: {data}")
            except WebSocketDisconnect:
                break
                
    finally:
        # Cleanup
        if task_id in ws_manager.active_connections:
            del ws_manager.active_connections[task_id]

@app.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return ws_manager.get_connection_info()

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and results"""
    if task_id not in active_tasks:
        raise HTTPException(404, "Task not found")
    
    task = active_tasks[task_id]
    response = {
        "task_id": task_id,
        "status": task["status"],
        "query": task["query"]
    }
    
    if "result" in task:
        result_dict = task["result"].dict()
        # Include tool calls in the response
        response["result"] = result_dict
        response["tool_calls"] = result_dict.get("tool_calls", [])
    if "error" in task:
        response["error"] = task["error"]
    
    return response

if __name__ == "__main__":
    import uvicorn
    # Configure uvicorn with WebSocket-specific settings
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        # WebSocket settings
        ws_ping_interval=20,  # Send ping every 20 seconds
        ws_ping_timeout=10,   # Wait 10 seconds for pong
        # General settings
        timeout_keep_alive=75,  # Keep connection alive for 75 seconds
        access_log=True
    )