# AIDEV-SECTION: WebSocket Connection Manager
import asyncio
import logging
from typing import Dict, Set
from datetime import datetime
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept WebSocket connection and start heartbeat"""
        # AIDEV-QUESTION: Should we add subprotocol or headers to websocket.accept()?
        # The handshake timeout might be due to missing protocol negotiation
        # Consider: await websocket.accept(subprotocol=None, headers=None)
        await websocket.accept()
        self.active_connections[task_id] = websocket
        
        # Start heartbeat task
        self.heartbeat_tasks[task_id] = asyncio.create_task(
            self._heartbeat_loop(websocket, task_id)
        )
        logger.info(f"WebSocket connected for task {task_id}")
        
    async def disconnect(self, task_id: str):
        """Properly disconnect WebSocket"""
        if task_id in self.active_connections:
            websocket = self.active_connections[task_id]
            
            # Cancel heartbeat
            if task_id in self.heartbeat_tasks:
                self.heartbeat_tasks[task_id].cancel()
                del self.heartbeat_tasks[task_id]
            
            # Close connection if still open
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.debug(f"Error closing WebSocket for {task_id}: {e}")
            
            del self.active_connections[task_id]
            logger.info(f"WebSocket disconnected for task {task_id}")
    
    async def send_json(self, task_id: str, data: dict):
        """Send JSON data to specific connection"""
        if task_id in self.active_connections:
            websocket = self.active_connections[task_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(data)
                    return True
                except Exception as e:
                    logger.error(f"Error sending to {task_id}: {e}")
                    await self.disconnect(task_id)
        return False
    
    async def _heartbeat_loop(self, websocket: WebSocket, task_id: str):
        """Send periodic heartbeats"""
        try:
            while task_id in self.active_connections:
                await asyncio.sleep(30)
                
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                    
                success = await self.send_json(task_id, {
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                if not success:
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error for {task_id}: {e}")

    async def connection_context(self, websocket: WebSocket, task_id: str):
        """Context manager for WebSocket connections"""
        class ConnectionContext:
            def __init__(self, manager, websocket, task_id):
                self.manager = manager
                self.websocket = websocket
                self.task_id = task_id
                
            async def __aenter__(self):
                await self.manager.connect(self.websocket, self.task_id)
                return self.manager
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await self.manager.disconnect(self.task_id)
                
        return ConnectionContext(self, websocket, task_id)
    
    def get_connection_info(self):
        """Get information about active connections"""
        return {
            "active_connections": len(self.active_connections),
            "connection_ids": list(self.active_connections.keys())
        }

# Global connection manager
manager = ConnectionManager()
ws_manager = manager  # Alias for compatibility