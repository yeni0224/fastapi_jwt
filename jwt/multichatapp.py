from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict
from datetime import datetime

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        # { "room_id": [websocket1, websocket2, ...] } 구조
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws-chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_json()
            message = {
                "sender": data.get("sender", "Anonymous"),
                "content": data.get("content", ""),
                "type": data.get("type", "CHAT"),
                "room_id": room_id,
                "timestamp": datetime.now().isoformat()
            }

            if message["type"] == "JOIN":
                message["content"] = f"{message['sender']} 님이 방에 입장하셨습니다."

            await manager.broadcast(room_id, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)