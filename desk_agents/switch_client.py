"""Minimal Switch agent-protocol client.

Follows https://docs.switchagents.ai/switch-rooms/internals/agent-protocol
and agent-connection: register once with POST /agents (registration key),
open GET /agents/{id}/connection/ws with a reused connection_id and the
rooms to claim, answer every ping with {"type":"pong","cursor":n}, act only
on `message` events whose payload.addressed is true, and call operations
with POST /agents/{id}/ops/{name} + X-Switch-Connection-Id.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
import websockets

CRED_FILE = Path(".switch-agents.local.json")  # gitignored; holds agent API keys


def register(base: str, registration_key: str, name: str, description: str) -> dict:
    creds = json.loads(CRED_FILE.read_text()) if CRED_FILE.exists() else {}
    if name in creds:
        return creds[name]
    r = httpx.post(f"{base}/agents", headers={"Authorization": f"Bearer {registration_key}"}, json={
        "name": name,
        "description": description,
        "connector_type": "campus-campaign-desk",
        "integration_profile": {
            "connection_model": "always_on",
            "message_exchange": True,
            "pre_invocation_mediation": [],
            "post_invocation_mediation": [],
            "event_reporting": [],
        },
    }, timeout=30)
    r.raise_for_status()
    data = r.json()
    creds[name] = {"id": data["id"], "api_key": data["api_key"], "connection_id": str(uuid.uuid4())}
    CRED_FILE.write_text(json.dumps(creds, indent=2))
    CRED_FILE.chmod(0o600)
    return creds[name]


class Agent:
    def __init__(self, base: str, name: str, cred: dict) -> None:
        self.base, self.name = base, name
        self.id, self.key, self.conn = cred["id"], cred["api_key"], cred["connection_id"]
        self.http = httpx.AsyncClient(timeout=60, headers={"Authorization": f"Bearer {self.key}"})
        self.cursor = 0
        self.ready = asyncio.Event()

    async def op(self, _op: str, **args: Any) -> Any:
        # The connection id header binds a call to the claimed room; send it
        # only once the socket is open (an unopened id is a 409).
        headers = {"X-Switch-Connection-Id": self.conn} if self.ready.is_set() else {}
        r = await self.http.post(f"{self.base}/agents/{self.id}/ops/{_op}", json=args, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"{self.name} {_op} -> {r.status_code} {r.text[:300]}")
        return r.json().get("result")

    async def run(self, room_id: str, on_message: Callable[[dict], Awaitable[None]] | None) -> None:
        ws_base = self.base.replace("http", "ws", 1)
        url = f"{ws_base}/agents/{self.id}/connection/ws?connection_id={self.conn}&rooms={room_id}&client=campus-campaign-desk"
        async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {self.key}"}) as ws:
            async for raw in ws:
                frame = json.loads(raw)
                kind = frame.get("type") or frame.get("event")
                if kind == "ping":
                    await ws.send(json.dumps({"type": "pong", "cursor": self.cursor}))
                    continue
                if kind == "connection_state":
                    self.cursor = frame.get("cursor") or 0
                    self.ready.set()
                    continue
                if kind in ("evicted", "refused"):
                    print(f"[{self.name}] {kind}: {frame}")
                    return
                if "id" in frame:
                    self.cursor = max(self.cursor, int(frame["id"]))
                data = frame.get("data") or {}
                if frame.get("event") == "message" and on_message:
                    payload = data.get("payload") or {}
                    if payload.get("addressed"):
                        asyncio.create_task(on_message(payload))
