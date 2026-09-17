import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket

class EventBus:
    """
    WebSocket event broadcaster for live crawl monitoring (PRD Section 67-68).
    Broadcasting real-time statistics, speed gauges, and streaming logs.
    """
    def __init__(self):
        self._job_subscribers: Dict[str, Set[WebSocket]] = {}
        self._global_subscribers: Set[WebSocket] = set()
        self._socket_locks: Dict[WebSocket, asyncio.Lock] = {}
        self._lock = asyncio.Lock()

    async def register(self, ws: WebSocket, job_id: Optional[str] = None):
        await ws.accept()
        async with self._lock:
            if ws not in self._socket_locks:
                self._socket_locks[ws] = asyncio.Lock()
            if job_id:
                if job_id not in self._job_subscribers:
                    self._job_subscribers[job_id] = set()
                self._job_subscribers[job_id].add(ws)
            else:
                self._global_subscribers.add(ws)

    async def unregister(self, ws: WebSocket, job_id: Optional[str] = None):
        async with self._lock:
            if job_id and job_id in self._job_subscribers:
                self._job_subscribers[job_id].discard(ws)
            self._global_subscribers.discard(ws)
            self._socket_locks.pop(ws, None)

    async def _safe_send(self, ws: WebSocket, payload: str) -> bool:
        lock = self._socket_locks.get(ws)
        if not lock:
            lock = asyncio.Lock()
            self._socket_locks[ws] = lock
        try:
            async with lock:
                await ws.send_text(payload)
            return True
        except Exception:
            return False

    async def broadcast_job_stats(self, job_id: str, stats: dict):
        payload = json.dumps({"type": "stats", "job_id": job_id, "data": stats})
        await self._send_to_job(job_id, payload)

    async def broadcast_log(self, job_id: str, level: str, message: str, timestamp: str):
        payload = json.dumps({
            "type": "log",
            "job_id": job_id,
            "data": {
                "level": level,
                "message": message,
                "timestamp": timestamp
            }
        })
        await self._send_to_job(job_id, payload)

    def publish(self, event_type: str, data: dict):
        """Non-blocking fire-and-forget event broadcast for general events."""
        try:
            loop = asyncio.get_running_loop()
            payload = json.dumps({"type": event_type, "data": data})
            loop.create_task(self._send_global(payload))
        except RuntimeError:
            pass

    async def _send_global(self, payload: str):
        async with self._lock:
            targets = list(self._global_subscribers)
        dead_sockets = []
        for ws in targets:
            ok = await self._safe_send(ws, payload)
            if not ok:
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for dws in dead_sockets:
                    self._global_subscribers.discard(dws)
                    self._socket_locks.pop(dws, None)

    async def _send_to_job(self, job_id: str, payload: str):
        async with self._lock:
            targets = list(self._job_subscribers.get(job_id, set())) + list(self._global_subscribers)

        dead_sockets = []
        for ws in targets:
            ok = await self._safe_send(ws, payload)
            if not ok:
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                if job_id in self._job_subscribers:
                    for dws in dead_sockets:
                        self._job_subscribers[job_id].discard(dws)
                for dws in dead_sockets:
                    self._global_subscribers.discard(dws)
                    self._socket_locks.pop(dws, None)

event_bus = EventBus()
