import uuid

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # room_id -> set of active WebSocket connections in that room
        self.active_connections: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, room_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)

    def disconnect(self, room_id: uuid.UUID, websocket: WebSocket):
        connections = self.active_connections.get(room_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            del self.active_connections[room_id]

    async def broadcast_to_room(self, room_id: uuid.UUID, message: dict):
        connections = self.active_connections.get(room_id, set())
        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # cleanup any connections that failed to receive (client vanished)
        for dead in dead_connections:
            self.disconnect(room_id, dead)


manager = ConnectionManager()