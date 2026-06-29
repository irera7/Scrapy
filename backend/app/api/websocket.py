from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import Dict, Set, Optional
import json
import asyncio
import structlog
from jose import jwt, JWTError

from app.core.config import settings

router = APIRouter()
logger = structlog.get_logger()


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return user_id."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Map of user_id to their active connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of job_id to users watching it
        self.job_watchers: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from job watchers
        for job_id in list(self.job_watchers.keys()):
            self.job_watchers[job_id].discard(user_id)
            if not self.job_watchers[job_id]:
                del self.job_watchers[job_id]
        
        logger.info(f"WebSocket disconnected: user {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user."""
        if user_id in self.active_connections:
            message_str = json.dumps(message)
            dead_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message_str)
                except Exception:
                    dead_connections.append(connection)
            
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[user_id].discard(conn)
    
    async def broadcast_to_job_watchers(self, message: dict, job_id: str):
        """Broadcast a message to all users watching a job."""
        if job_id in self.job_watchers:
            message_str = json.dumps(message)
            for user_id in self.job_watchers[job_id]:
                if user_id in self.active_connections:
                    dead_connections = []
                    for connection in self.active_connections[user_id]:
                        try:
                            await connection.send_text(message_str)
                        except Exception:
                            dead_connections.append(connection)
                    
                    for conn in dead_connections:
                        self.active_connections[user_id].discard(conn)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Broadcast a message to all connections of a user."""
        await self.send_personal_message(message, user_id)
    
    def watch_job(self, job_id: str, user_id: str):
        """Subscribe a user to job updates."""
        if job_id not in self.job_watchers:
            self.job_watchers[job_id] = set()
        self.job_watchers[job_id].add(user_id)
    
    def unwatch_job(self, job_id: str, user_id: str):
        """Unsubscribe a user from job updates."""
        if job_id in self.job_watchers:
            self.job_watchers[job_id].discard(user_id)
            if not self.job_watchers[job_id]:
                del self.job_watchers[job_id]


# Global connection manager
manager = ConnectionManager()


@router.websocket("/updates")
async def websocket_updates(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint for real-time updates with token authentication."""
    # Verify token
    user_id = verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            action = message.get("action")
            
            if action == "watch_job":
                job_id = message.get("job_id")
                if job_id:
                    manager.watch_job(job_id, user_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "job_id": job_id
                    }))
            
            elif action == "unwatch_job":
                job_id = message.get("job_id")
                if job_id:
                    manager.unwatch_job(job_id, user_id)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "job_id": job_id
                    }))
            
            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


# Legacy endpoint for backwards compatibility
@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates (legacy, use /updates with token instead)."""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "watch_job":
                job_id = message.get("job_id")
                if job_id:
                    manager.watch_job(job_id, user_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "job_id": job_id
                    }))
            
            elif action == "unwatch_job":
                job_id = message.get("job_id")
                if job_id:
                    manager.unwatch_job(job_id, user_id)
                    await websocket.send_text(json.dumps({
                        "type": "unsubscribed",
                        "job_id": job_id
                    }))
            
            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


# Helper functions for sending updates from workers
async def send_job_update(job_id: str, user_id: str, status: str, progress: float = 0, 
                          items_collected: int = 0, message: str = None):
    """Send a job status update."""
    update = {
        "type": f"job_{status}",
        "payload": {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "items_collected": items_collected,
            "message": message
        }
    }
    
    # Send to specific user
    await manager.broadcast_to_user(user_id, update)
    
    # Also send to job watchers
    await manager.broadcast_to_job_watchers(update, job_id)


async def send_export_update(user_id: str, export_id: str, status: str, progress: float = 0):
    """Send an export status update to the user."""
    await manager.send_personal_message({
        "type": f"export_{status}",
        "payload": {
            "export_id": export_id,
            "status": status,
            "progress": progress
        }
    }, user_id)


async def send_data_update(user_id: str, project_id: str, count: int):
    """Send a data collection update."""
    await manager.send_personal_message({
        "type": "data_collected",
        "payload": {
            "project_id": project_id,
            "count": count
        }
    }, user_id)
