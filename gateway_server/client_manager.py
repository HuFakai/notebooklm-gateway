from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from notebooklm import NotebookLMClient
from notebooklm import AuthError

from .database import Account, DatabaseManager


@dataclass(slots=True)
class _Entry:
    account: Account
    client: Any
    context: Any
    storage_path: Path
    storage_digest: str
    refs: int
    last_used: float


class ClientManager:
    """Loop-safe, bounded LRU pool of public NotebookLM SDK clients."""

    def __init__(
        self,
        db: DatabaseManager,
        profiles_dir: Path,
        *,
        max_clients: int = 20,
        idle_seconds: int = 1800,
        keepalive_seconds: int = 600,
        client_factory: Callable[..., Any] = NotebookLMClient.from_storage,
    ):
        self.db = db
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.max_clients = max_clients
        self.idle_seconds = idle_seconds
        self.keepalive_seconds = keepalive_seconds
        self.client_factory = client_factory
        self._entries: dict[int, _Entry] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, account: Account) -> AsyncIterator[Any]:
        entry = await self._get_or_create(account)
        entry.refs += 1
        entry.last_used = time.monotonic()
        try:
            yield entry.client
        finally:
            entry.refs = max(0, entry.refs - 1)
            entry.last_used = time.monotonic()
            await self._sync_if_changed(entry)
            await self._evict()

    async def _get_or_create(self, account: Account) -> _Entry:
        entry = self._entries.get(account.id)
        if entry and entry.account.updated_at == account.updated_at:
            return entry
        async with self._pool_lock:
            lock = self._locks.setdefault(account.id, asyncio.Lock())
        async with lock:
            entry = self._entries.get(account.id)
            if entry and entry.account.updated_at == account.updated_at:
                return entry
            if entry:
                await self._close_entry(entry)
            storage_path = await asyncio.to_thread(self._prepare_profile, account)
            context = self.client_factory(
                path=str(storage_path),
                keepalive=self.keepalive_seconds,
                rate_limit_max_retries=3,
                server_error_max_retries=3,
            )
            try:
                client = await context.__aenter__()
            except Exception as exc:
                if isinstance(exc, AuthError):
                    await asyncio.to_thread(self.db.update_account_status, account.id, "expired")
                raise
            digest = await asyncio.to_thread(self._file_digest, storage_path)
            entry = _Entry(
                account=account,
                client=client,
                context=context,
                storage_path=storage_path,
                storage_digest=digest,
                refs=0,
                last_used=time.monotonic(),
            )
            self._entries[account.id] = entry
            await self._evict()
            return entry

    def _prepare_profile(self, account: Account) -> Path:
        profile_dir = self.profiles_dir / str(account.id)
        profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(profile_dir, 0o700)
        except OSError:
            pass
        storage_path = profile_dir / "storage_state.json"
        data = json.dumps(json.loads(account.storage_state), ensure_ascii=False, separators=(",", ":"))
        temp_path = storage_path.with_suffix(".tmp")
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, storage_path)
        return storage_path

    @staticmethod
    def _file_digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    async def _sync_if_changed(self, entry: _Entry) -> None:
        try:
            digest = await asyncio.to_thread(self._file_digest, entry.storage_path)
            if digest == entry.storage_digest:
                return
            storage_state = await asyncio.to_thread(entry.storage_path.read_text, "utf-8")
            await asyncio.to_thread(self.db.update_storage_state, entry.account.id, storage_state)
            entry.storage_digest = digest
        except (OSError, json.JSONDecodeError):
            return

    async def invalidate(self, account_id: int) -> None:
        async with self._pool_lock:
            entry = self._entries.pop(account_id, None)
        if entry:
            await self._close_entry(entry)

    async def _evict(self) -> None:
        now = time.monotonic()
        candidates = sorted(self._entries.values(), key=lambda item: item.last_used)
        to_close: list[_Entry] = []
        for entry in candidates:
            if entry.refs:
                continue
            is_idle = now - entry.last_used >= self.idle_seconds
            over_limit = len(self._entries) - len(to_close) > self.max_clients
            if is_idle or over_limit:
                self._entries.pop(entry.account.id, None)
                to_close.append(entry)
        for entry in to_close:
            await self._close_entry(entry)

    async def _close_entry(self, entry: _Entry) -> None:
        try:
            await entry.context.__aexit__(None, None, None)
        finally:
            await self._sync_if_changed(entry)

    async def close(self) -> None:
        entries = list(self._entries.values())
        self._entries.clear()
        for entry in entries:
            await self._close_entry(entry)
        self._locks.clear()
