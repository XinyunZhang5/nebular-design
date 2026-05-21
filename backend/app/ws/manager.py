import asyncio
import json
from typing import DefaultDict
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for both the public chatroom and per-user DM channels."""

    def __init__(self) -> None:
        # Public chatroom connections
        self._chatroom: list[WebSocket] = []
        # Per-user DM connections: user_id → list of active WebSocket sessions
        self._dm: DefaultDict[str, list[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()

    # ---- Chatroom ----

    async def chatroom_connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._chatroom.append(ws)

    async def chatroom_disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._chatroom.remove(ws)

    async def chatroom_broadcast(self, payload: dict) -> None:
        data = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in list(self._chatroom):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        async with self._lock:
            for ws in dead:
                if ws in self._chatroom:
                    self._chatroom.remove(ws)

    # ---- DM ----

    async def dm_connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._dm[user_id].append(ws)

    async def dm_disconnect(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._dm[user_id]:
                self._dm[user_id].remove(ws)

    async def dm_send(self, user_id: str, payload: dict) -> None:
        data = json.dumps(payload, default=str)
        dead: list[WebSocket] = []
        for ws in list(self._dm.get(user_id, [])):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        async with self._lock:
            for ws in dead:
                if ws in self._dm[user_id]:
                    self._dm[user_id].remove(ws)

    @property
    def chatroom_count(self) -> int:
        return len(self._chatroom)


manager = ConnectionManager()
