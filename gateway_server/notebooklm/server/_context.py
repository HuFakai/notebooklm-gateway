"""Per-request access to the lifespan-bound client.

The REST server binds exactly one
:class:`~notebooklm.client.NotebookLMClient` for the process lifetime via the
ASGI lifespan (one client, bound to the server's event loop, satisfying the
ADR-0004 loop-affinity contract). Route handlers reach it through the
:func:`get_client` FastAPI dependency, so they never touch app-state internals
directly. If startup could not bind a live client, diagnostics can still inspect
the recorded failure while client-dependent routes receive the normal structured
REST error response.

This module imports NO ``click`` / ``rich`` / ``cli``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Request

from ._limits import LimitGroup, ServerLimiters
from ._pending import PendingRegistry

if TYPE_CHECKING:
    from ..client import NotebookLMClient

__all__ = [
    "AppState",
    "get_client",
    "get_client_error",
    "get_pending",
    "limit_chat",
    "limit_download",
    "limit_generation",
    "limit_research",
    "limit_source_mutation",
    "limit_source_wait",
]


@dataclass
class AppState:
    """Lifespan state: the single long-lived client bound to the server loop.

    ``pending`` is the process-lifetime provenance registry consulted by the
    source / artifact poll handlers (see :mod:`._pending`).
    """

    client: NotebookLMClient | None
    pending: PendingRegistry
    limiters: ServerLimiters
    client_error: BaseException | None = None


async def get_client(request: Request) -> NotebookLMClient:
    """多账号动态路由注入函数"""
    from gateway_server.database import DatabaseManager
    import os
    import json
    from pathlib import Path
    from fastapi import HTTPException, status

    db = DatabaseManager()
    
    # 1. 提取 Authorization Header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token"
        )
    
    api_key = auth_header.split(" ")[1]
    
    # 2. 限制管理员 Token 直接进行业务调用
    admin_token = os.environ.get("NOTEBOOKLM_ADMIN_TOKEN", "admin_secret_token_change_me")
    if api_key == admin_token:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin token cannot be used to perform notebook operations. Please use a user account API key."
         )

    # 3. 声明或读取内存客户端池
    # 在 app.state 上绑定 client_pool 保持单例
    if not hasattr(request.app.state, "client_pool"):
        request.app.state.client_pool = {}
    
    client_pool = request.app.state.client_pool

    # 4. 从缓存获取
    if api_key in client_pool:
        client = client_pool[api_key]
        # 异步做个文件改写检测与库数据同步
        _sync_back_if_modified(client._path.parent.name)  # client._path.parent.name 是账号 email
        return client

    # 5. 从 SQLite 数据库查找
    account = db.get_account_by_api_key(api_key)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key or account is inactive/expired"
        )

    email = account["email"]
    
    # 准备账号本地存储目录
    profile_dir = Path("data/profiles") / email
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        from gateway_server.notebooklm.auth import generate_android_id
        # 写回 master_token.json 和 storage_state.json
        master_token_data = {
            "version": 1,
            "email": email,
            "android_id": generate_android_id(),
            "master_token": account["master_token"]
        }
        with open(profile_dir / "master_token.json", "w") as f:
            json.dump(master_token_data, f)
            
        storage_state_data = json.loads(account["storage_state"])
        with open(profile_dir / "storage_state.json", "w") as f:
            json.dump(storage_state_data, f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare local credentials: {e}"
        )

    # 6. 初始化并绑定当前会话
    try:
        client = NotebookLMClient(path=profile_dir)
        await client.__aenter__()
        client_pool[api_key] = client
        return client
    except Exception as e:
        db.update_account_status(email, "expired")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize NotebookLM Session: {e}. Session marked as expired."
        )


def _sync_back_if_modified(email: str):
    """当程序产生 Cookie 回写时，同步更新回 SQLite 数据库中"""
    from gateway_server.database import DatabaseManager
    db = DatabaseManager()
    state_file = Path("data/profiles") / email / "storage_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                state_data = f.read()
            with db._get_connection() as conn:
                conn.execute(
                    "UPDATE accounts SET storage_state = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?",
                    (state_data, email)
                )
                conn.commit()
        except Exception as e:
            print(f"Failed to sync credentials back to database for {email}: {e}")



def get_client_error(request: Request) -> BaseException | None:
    """Return the startup failure that prevented binding a live client, if any."""
    error = _state(request).client_error
    return _fresh_exception(error) if error is not None else None


def get_pending(request: Request) -> PendingRegistry:
    """Return the process-lifetime pending-id registry for the current request."""
    return _state(request).pending


async def limit_source_mutation(request: Request) -> AsyncIterator[None]:
    """Backpressure source create/rename/delete routes."""
    async with _limit(request, "source_mutation"):
        yield


async def limit_source_wait(request: Request) -> AsyncIterator[None]:
    """Backpressure source wait routes."""
    async with _limit(request, "source_wait"):
        yield


async def limit_generation(request: Request) -> AsyncIterator[None]:
    """Backpressure artifact generation routes."""
    async with _limit(request, "generation"):
        yield


async def limit_download(request: Request) -> AsyncIterator[None]:
    """Backpressure artifact download routes."""
    async with _limit(request, "download"):
        yield


async def limit_research(request: Request) -> AsyncIterator[None]:
    """Backpressure research mutation/import routes."""
    async with _limit(request, "research"):
        yield


async def limit_chat(request: Request) -> AsyncIterator[None]:
    """Backpressure blocking chat ask routes."""
    async with _limit(request, "chat"):
        yield


@asynccontextmanager
async def _limit(request: Request, group: LimitGroup) -> AsyncIterator[None]:
    async with _state(request).limiters.acquire(group):
        yield


def _state(request: Request) -> AppState:
    state: AppState | None = getattr(request.app.state, "notebooklm", None)
    if state is None:  # pragma: no cover - lifespan always binds before requests
        raise RuntimeError("no client bound to the server (lifespan did not run)")
    return state


def _fresh_exception(exc: BaseException) -> BaseException:
    """Clone a stored startup error so repeated requests do not mutate traceback state."""
    return exc.__class__(*exc.args)
