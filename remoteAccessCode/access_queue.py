"""Cookie-based exclusive control queue for the remote jig UI."""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any, Optional

from fastapi import HTTPException, Request, Response

CLIENT_COOKIE = "jig_client"
ACCESS_SLOT_SEC = int(os.environ.get("ACCESS_SLOT_SEC", "60"))
ACCESS_HEARTBEAT_TIMEOUT_SEC = float(os.environ.get("ACCESS_HEARTBEAT_TIMEOUT_SEC", "15"))


class AccessQueue:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.holder_id: Optional[str] = None
        self.holder_since: float = 0.0
        self.deadline_at: Optional[float] = None
        self.queue: list[str] = []
        self.last_seen: dict[str, float] = {}

    def _now(self) -> float:
        return time.time()

    def _clear_holder_unlocked(self) -> None:
        self.holder_id = None
        self.holder_since = 0.0
        self.deadline_at = None

    def _promote_unlocked(self) -> None:
        now = self._now()
        while self.queue:
            nxt = self.queue.pop(0)
            ts = self.last_seen.get(nxt)
            if ts is None or now - ts > ACCESS_HEARTBEAT_TIMEOUT_SEC:
                self.last_seen.pop(nxt, None)
                continue
            self.holder_id = nxt
            self.holder_since = now
            self.deadline_at = (now + ACCESS_SLOT_SEC) if self.queue else None
            return
        self._clear_holder_unlocked()

    def _sync_deadline_unlocked(self) -> None:
        if not self.holder_id:
            self.deadline_at = None
            return
        if not self.queue:
            self.deadline_at = None
            return
        if self.deadline_at is None:
            self.deadline_at = self._now() + ACCESS_SLOT_SEC

    def _remove_unlocked(self, client_id: str) -> None:
        if client_id in self.queue:
            self.queue = [c for c in self.queue if c != client_id]
        was_holder = self.holder_id == client_id
        self.last_seen.pop(client_id, None)
        if was_holder:
            self._clear_holder_unlocked()
            self._promote_unlocked()
        else:
            self._sync_deadline_unlocked()

    def tick(self, busy: str) -> None:
        """Reap stale clients and promote when the holder's slot has expired."""
        with self.lock:
            self._tick_unlocked(busy)

    def _tick_unlocked(self, busy: str) -> None:
        now = self._now()
        stale = [
            cid
            for cid, ts in list(self.last_seen.items())
            if now - ts > ACCESS_HEARTBEAT_TIMEOUT_SEC
        ]
        for cid in stale:
            self._remove_unlocked(cid)

        if (
            self.holder_id
            and self.deadline_at is not None
            and now >= self.deadline_at
            and busy == "idle"
        ):
            expired = self.holder_id
            self._clear_holder_unlocked()
            self.last_seen.pop(expired, None)
            self._promote_unlocked()

        if self.holder_id is None and self.queue:
            self._promote_unlocked()

        self._sync_deadline_unlocked()

    def touch(self, client_id: str) -> None:
        with self.lock:
            self.last_seen[client_id] = self._now()

    def claim(self, client_id: str, busy: str) -> dict[str, Any]:
        with self.lock:
            self._tick_unlocked(busy)
            self.last_seen[client_id] = self._now()
            if self.holder_id == client_id:
                return self._snapshot_unlocked(client_id)
            if client_id in self.queue:
                return self._snapshot_unlocked(client_id)
            if self.holder_id is None:
                self.holder_id = client_id
                self.holder_since = self._now()
                self.deadline_at = None
                self._sync_deadline_unlocked()
                return self._snapshot_unlocked(client_id)
            self.queue.append(client_id)
            self._sync_deadline_unlocked()
            return self._snapshot_unlocked(client_id)

    def heartbeat(self, client_id: str, busy: str) -> dict[str, Any]:
        with self.lock:
            self._tick_unlocked(busy)
            self.last_seen[client_id] = self._now()
            # Auto-claim if free and this client is not queued elsewhere
            if self.holder_id is None and client_id not in self.queue:
                self.holder_id = client_id
                self.holder_since = self._now()
                self.deadline_at = None
            return self._snapshot_unlocked(client_id)

    def leave(self, client_id: str, busy: str) -> dict[str, Any]:
        with self.lock:
            self._tick_unlocked(busy)
            self._remove_unlocked(client_id)
            return self._snapshot_unlocked(None)

    def snapshot(self, client_id: Optional[str], busy: str) -> dict[str, Any]:
        with self.lock:
            self._tick_unlocked(busy)
            return self._snapshot_unlocked(client_id)

    def _snapshot_unlocked(self, client_id: Optional[str]) -> dict[str, Any]:
        role = "none"
        position = None
        seconds_left = None
        if client_id and client_id == self.holder_id:
            role = "holder"
            if self.deadline_at is not None:
                seconds_left = max(0, int(self.deadline_at - self._now()))
        elif client_id and client_id in self.queue:
            role = "waiting"
            position = self.queue.index(client_id) + 1
        return {
            "role": role,
            "position": position,
            "queue_length": len(self.queue),
            "seconds_left": seconds_left,
            "slot_sec": ACCESS_SLOT_SEC,
            "has_holder": self.holder_id is not None,
        }

    def assert_holder(self, client_id: str, busy: str) -> None:
        with self.lock:
            self._tick_unlocked(busy)
            if self.holder_id != client_id:
                if client_id in self.queue:
                    raise HTTPException(status_code=423, detail="waiting")
                raise HTTPException(status_code=423, detail="not_holder")
            if self.deadline_at is not None and self._now() >= self.deadline_at:
                raise HTTPException(status_code=423, detail="expired")


access = AccessQueue()


def get_client_id(request: Request) -> str:
    client_id = getattr(request.state, "client_id", None)
    if client_id:
        return str(client_id)
    cookie = request.cookies.get(CLIENT_COOKIE)
    if cookie:
        return cookie
    return str(uuid.uuid4())


def set_client_cookie(response: Response, client_id: str) -> None:
    response.set_cookie(
        key=CLIENT_COOKIE,
        value=client_id,
        max_age=365 * 24 * 60 * 60,
        httponly=False,
        samesite="lax",
        path="/",
    )


def require_holder(request: Request, busy: str) -> str:
    client_id = get_client_id(request)
    access.assert_holder(client_id, busy)
    return client_id
