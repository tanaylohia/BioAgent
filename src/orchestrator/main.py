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
import json

from src.models.search import SearchRequest, SearchResult
from src.agents.search_agent import SearchAgent
from src.utils.websocket_manager import ws_manager

# Setup
app = FastAPI(title="Bio Agent API", version="1.0.0")

# AIDEV-NOTE: CORS configuration for frontend access
# In production, replace "*" with specific frontend URLs
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

# Initialize agents lazily
search_agent = None

def get_search_agent():
    global search_agent
    if search_agent is None:
        try:
            logger.info("Initializing SearchAgent...")
            search_agent = SearchAgent()
            logger.info("SearchAgent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SearchAgent: {e}", exc_info=True)
            raise RuntimeError(f"SearchAgent initialization failed: {str(e)}")
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
        return {"status": "error", "message": str(e), "type": type(e).__name__}

@app.get("/debug/mock-search")
async def mock_search():
    """Mock search endpoint that returns dummy data without external API calls"""
    from src.models.paper import Paper
    from datetime import datetime
    
    # AIDEV-NOTE: Mock endpoint for testing without external dependencies
    mock_papers = [
        Paper(
            title="CRISPR-Cas9: A Revolutionary Gene Editing Tool",
            abstract="This paper reviews the latest advances in CRISPR technology...",
            authors=["Jennifer Doudna", "Emmanuelle Charpentier"],
            citations=1000,
            publication_date=datetime(2024, 1, 15),
            hyperlink="https://example.com/paper1",
            source="Mock Database",
            doi="10.1234/mock.2024.001"
        ),
        Paper(
            title="Applications of CRISPR in Cancer Therapy",
            abstract="We explore the therapeutic potential of CRISPR-Cas9 in treating various cancers...",
            authors=["John Smith", "Jane Doe"],
            citations=250,
            publication_date=datetime(2024, 6, 10),
            hyperlink="https://example.com/paper2",
            source="Mock Database",
            doi="10.1234/mock.2024.002"
        )
    ]
    
    return {
        "status": "success",
        "papers": [p.dict() for p in mock_papers],
        "message": "Mock search completed successfully"
    }

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
        logger.error(f"Search error: {e}", exc_info=True)
        # AIDEV-NOTE: Return more informative error for debugging
        raise HTTPException(500, f"Search initiation failed: {str(e)}")

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
        
        # Create a keep-alive task to prevent timeouts
        keep_alive_event = asyncio.Event()
        keep_alive_task = asyncio.create_task(keep_alive_updates(task_id, keep_alive_event))
        
        # Create progress callback
        async def progress_callback(message: str, progress: int):
            try:
                await send_ws_update(task_id, "progress", {
                    "progress": progress,
                    "current_step": message,
                    "message": message
                })
            except Exception as e:
                logger.warning(f"Failed to send progress update: {e}")
        
        # Create paper callback for streaming papers as they're found
        async def paper_callback(papers: list, phase: str):
            try:
                logger.info(f"Paper callback called with {len(papers)} papers for phase: {phase}")
                
                # Convert Paper objects to dicts
                paper_dicts = []
                for paper in papers:
                    if hasattr(paper, 'dict'):
                        paper_dicts.append(paper.dict())
                    else:
                        paper_dicts.append(paper)
                
                logger.info(f"Sending {len(paper_dicts)} papers via WebSocket for task {task_id}")
                
                await send_ws_update(task_id, "papers", {
                    "papers": paper_dicts,
                    "phase": phase,  # "initial" or "additional"
                    "count": len(paper_dicts),
                    "message": f"Found {len(paper_dicts)} papers in {phase} search"
                })
                
                logger.info(f"Successfully sent papers update for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to send paper update: {e}", exc_info=True)
        
        # Create stream callback for summary streaming
        async def stream_callback(chunk: str):
            try:
                await send_ws_update(task_id, "summary_stream", {
                    "chunk": chunk,
                    "message": "Streaming analysis..."
                })
            except Exception as e:
                logger.warning(f"Failed to send stream update: {e}")
        
        # Execute search with progress callback and timeout
        # AIDEV-NOTE: Increased timeout to 300 seconds (5 minutes) for complex searches
        agent = get_search_agent()
        result = await asyncio.wait_for(
            agent.execute(request.query, progress_callback, paper_callback, stream_callback),
            timeout=300.0  # 5 minute timeout
        )
        
        logger.info(f"Search completed for task {task_id}")
        
        # Stop keep-alive updates
        keep_alive_event.set()
        await keep_alive_task
        
        # Store result
        active_tasks[task_id]["result"] = result
        active_tasks[task_id]["status"] = "completed"
        
        # Send final result - avoid dict() method to prevent mode= errors
        logger.info("Preparing result for WebSocket")
        # AIDEV-NOTE: Manually construct dict to avoid Pydantic version issues
        result_data = {
            "query": result.query,
            "analysis": result.analysis,
            "papers": [
                {
                    "title": p.title,
                    "abstract": p.abstract,
                    "authors": p.authors,
                    "citations": p.citations,
                    "publication_date": p.publication_date.isoformat() if p.publication_date else None,
                    "hyperlink": p.hyperlink,
                    "source": p.source,
                    "doi": p.doi,
                    "journal": p.journal
                } for p in result.papers
            ],
            "tool_calls": result.tool_calls or [],
            "reasoning_trace": result.reasoning_trace or []
        }
        await send_ws_update(task_id, "result", result_data)
        
    except asyncio.TimeoutError:
        error_msg = "Search timed out after 5 minutes. The query might be too broad or external services are slow."
        logger.error(f"Search timeout for task {task_id}")
        
        # Stop keep-alive updates
        keep_alive_event.set()
        await keep_alive_task
        
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = error_msg
        await send_ws_update(task_id, "error", {"error": error_msg})
    except Exception as e:
        logger.error(f"Search execution error for task {task_id}: {e}", exc_info=True)
        # Stop keep-alive updates if they're running
        if 'keep_alive_event' in locals():
            keep_alive_event.set()
            if 'keep_alive_task' in locals():
                await keep_alive_task
        
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = str(e)
        await send_ws_update(task_id, "error", {"error": str(e)})

async def keep_alive_updates(task_id: str, stop_event: asyncio.Event):
    """Send periodic keep-alive updates to prevent timeout"""
    last_progress = 10
    messages = [
        "Searching scientific databases...",
        "Analyzing research papers...",
        "Processing search results...",
        "Extracting key findings...",
        "Compiling comprehensive analysis..."
    ]
    message_index = 0
    
    while not stop_event.is_set():
        try:
            # Wait for 30 seconds or until stopped
            await asyncio.wait_for(stop_event.wait(), timeout=30.0)
            if stop_event.is_set():
                break
        except asyncio.TimeoutError:
            # Send a keep-alive progress update
            last_progress = min(last_progress + 5, 90)  # Gradually increase progress
            await send_ws_update(task_id, "progress", {
                "progress": last_progress,
                "current_step": messages[message_index % len(messages)],
                "message": "Search in progress..."
            })
            message_index += 1
            logger.debug(f"Sent keep-alive update for task {task_id}")

async def send_ws_update(task_id: str, msg_type: str, data: Dict):
    """Send update via WebSocket if connected"""
    # AIDEV-NOTE: Use json.dumps/loads to ensure proper serialization
    # This handles any Pydantic v2 models that might use mode='json'
    try:
        logger.debug(f"Attempting to send {msg_type} update for task {task_id}")
        
        # Convert to JSON string and back to ensure compatibility
        json_str = json.dumps(data, default=str)
        safe_data = json.loads(json_str)
        
        # Check if WebSocket is connected
        if task_id not in ws_manager.active_connections:
            logger.warning(f"No WebSocket connection for task {task_id}, message type: {msg_type}")
            return
        
        sent = await ws_manager.send_json(task_id, {
            "type": msg_type,
            "data": safe_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if sent:
            logger.debug(f"Successfully sent {msg_type} update for task {task_id}")
        else:
            logger.warning(f"Failed to send {msg_type} update for task {task_id}")
            
    except Exception as e:
        logger.error(f"Error in send_ws_update: {e}", exc_info=True)
        # Send error notification
        await ws_manager.send_json(task_id, {
            "type": "error",
            "data": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat()
        })

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time updates"""
    logger.info(f"WebSocket connection request for task {task_id}")
    
    # Accept the connection
    await websocket.accept()
    logger.info(f"WebSocket accepted for task {task_id}")
    
    try:
        # Register with manager
        ws_manager.active_connections[task_id] = websocket
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "data": {"task_id": task_id, "message": "WebSocket connected successfully"},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"WebSocket registered for task {task_id}, total connections: {len(ws_manager.active_connections)}")
        
        # Keep connection alive
        while True:
            try:
                # Wait for messages from client (mainly for ping/pong)
                data = await websocket.receive_text()
                logger.debug(f"Received from client for task {task_id}: {data}")
                
                # Send pong response if it's a ping
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for task {task_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error for task {task_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for task {task_id}: {e}", exc_info=True)
    finally:
        # Cleanup
        if task_id in ws_manager.active_connections:
            del ws_manager.active_connections[task_id]
            logger.info(f"WebSocket cleaned up for task {task_id}, remaining connections: {len(ws_manager.active_connections)}")

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