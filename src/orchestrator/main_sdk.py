# AIDEV-SECTION: Orchestrator with SDK Support
"""
FastAPI orchestrator that uses the OpenAI Agents SDK implementation.
This is a modified version of main.py that uses SDK-based search.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict
import json
import os

from src.models.search import SearchRequest, SearchResult
from src.orchestrator.sdk_search import execute_sdk_search
from src.utils.websocket_manager import ws_manager

# Setup
app = FastAPI(title="Bio Agent API (SDK)", version="2.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active tasks
active_tasks: Dict[str, Dict] = {}

@app.on_event("startup")
async def startup():
    """Initialize SDK agents on startup"""
    logger.info("Bio Agent API (SDK) starting up...")
    # SDK agents are initialized on import, no need for explicit init
    logger.info("SDK agents ready")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Bio Agent API (SDK) shutting down...")
    # Cancel any active tasks
    for task_id, task_info in active_tasks.items():
        if not task_info["task"].done():
            task_info["task"].cancel()

@app.get("/")
async def root():
    return {
        "message": "Bio Agent API (SDK Version)",
        "version": "2.0.0",
        "implementation": "OpenAI Agents SDK",
        "endpoints": ["/search", "/ws/{task_id}"]
    }

@app.post("/search")
async def search(request: SearchRequest) -> Dict:
    """
    Start a new search task using SDK implementation.
    Returns a task ID for WebSocket connection.
    """
    logger.info(f"Received search request: {request.query}")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Create progress callback for WebSocket updates
    async def progress_callback(message: str, progress: int):
        await ws_manager.send_progress(task_id, {
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
    
    # Create search task
    async def run_search():
        try:
            logger.info(f"Starting SDK search for task {task_id}")
            
            # Run SDK search with progress updates
            result = await execute_sdk_search(
                query=request.query,
                progress_callback=progress_callback
            )
            
            # Send final result
            await ws_manager.send_result(task_id, result.model_dump())
            
            # Store result
            active_tasks[task_id]["result"] = result
            active_tasks[task_id]["status"] = "completed"
            
            logger.info(f"Search task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Search task {task_id} failed: {e}", exc_info=True)
            await ws_manager.send_error(task_id, str(e))
            active_tasks[task_id]["status"] = "failed"
            active_tasks[task_id]["error"] = str(e)
    
    # Start task
    task = asyncio.create_task(run_search())
    active_tasks[task_id] = {
        "task": task,
        "status": "running",
        "created_at": datetime.now()
    }
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Search initiated. Connect to WebSocket for real-time updates."
    }

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time search progress"""
    logger.info(f"WebSocket connection attempt for task {task_id}")
    
    try:
        # Accept connection
        await websocket.accept()
        logger.info(f"WebSocket connected for task {task_id}")
        
        # Register connection
        await ws_manager.connect(task_id, websocket)
        
        # Send initial connection message
        await ws_manager.send_message(task_id, {
            "type": "connected",
            "task_id": task_id,
            "message": "Connected to search progress stream"
        })
        
        # Check if task exists
        if task_id in active_tasks:
            task_info = active_tasks[task_id]
            
            # If task is already completed, send result immediately
            if task_info["status"] == "completed" and "result" in task_info:
                await ws_manager.send_result(task_id, task_info["result"].model_dump())
            elif task_info["status"] == "failed":
                await ws_manager.send_error(task_id, task_info.get("error", "Unknown error"))
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong handled by WebSocket)
                message = await websocket.receive_text()
                
                # Echo back any client messages
                await ws_manager.send_message(task_id, {
                    "type": "echo",
                    "message": message
                })
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for task {task_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error for task {task_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection failed for task {task_id}: {e}", exc_info=True)
    finally:
        # Disconnect and cleanup
        ws_manager.disconnect(task_id)
        
        # Clean up completed tasks after disconnect
        if task_id in active_tasks and active_tasks[task_id]["status"] in ["completed", "failed"]:
            del active_tasks[task_id]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "implementation": "OpenAI Agents SDK",
        "active_tasks": len(active_tasks)
    }

if __name__ == "__main__":
    import uvicorn
    
    # Use environment variable to set port
    port = int(os.getenv("PORT", 6000))
    
    logger.info(f"Starting Bio Agent API (SDK) on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )