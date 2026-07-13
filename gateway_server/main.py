from __future__ import annotations

import asyncio
import hmac
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from notebooklm import (
    AuthError,
    NetworkError,
    NotebookLMError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    WaitTimeoutError,
)

from .api import create_api_router
from .client_manager import ClientManager
from .config import Settings
from .database import DatabaseManager
from .schemas import CredentialsUpload, KeyUpdate, StatusUpdate

ROOT = Path(__file__).resolve().parents[1]


async def require_admin(request: Request) -> None:
    auth = request.headers.get("Authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        token, request.app.state.settings.admin_token
    ):
        raise HTTPException(401, "Invalid admin token")


AdminDep = Annotated[None, Depends(require_admin)]


def create_app(settings: Settings | None = None, db: DatabaseManager | None = None) -> FastAPI:
    resolved = settings or Settings.from_env()
    database = db or DatabaseManager(resolved.data_dir)
    manager = ClientManager(
        database,
        resolved.data_dir / "profiles",
        max_clients=resolved.max_clients,
        idle_seconds=resolved.client_idle_seconds,
        keepalive_seconds=resolved.keepalive_seconds,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await manager.close()

    application = FastAPI(
        title="NotebookLM Gateway",
        version="0.2.0",
        description="Multi-tenant thin gateway backed by the public notebooklm-py API.",
        lifespan=lifespan,
    )
    application.state.settings = resolved
    application.state.db = database
    application.state.clients = manager

    if resolved.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith(("/admin", "/noteweb")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(NotebookLMError)
    async def notebooklm_error(_: Request, exc: NotebookLMError) -> JSONResponse:
        if isinstance(exc, AuthError):
            code = 401
        elif isinstance(exc, NotFoundError):
            code = 404
        elif isinstance(exc, ValidationError):
            code = 400
        elif isinstance(exc, RateLimitError):
            code = 429
        elif isinstance(exc, WaitTimeoutError):
            code = 504
        elif isinstance(exc, NetworkError):
            code = 502
        else:
            code = 502
        return JSONResponse(status_code=code, content={"detail": str(exc), "upstream": True})

    @application.get("/healthz", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/v1/auth/credentials", tags=["Auth"])
    async def upload_credentials(
        body: CredentialsUpload, _: AdminDep
    ) -> dict[str, str | bool | int]:
        try:
            storage_state = json.loads(body.storage_state)
            if not isinstance(storage_state, dict) or not isinstance(
                storage_state.get("cookies"), list
            ):
                raise ValueError("storage_state must contain a cookies array")
            account = await asyncio.to_thread(
                database.save_account,
                str(body.email),
                body.api_key,
                body.storage_state,
                body.master_token,
                body.android_id,
            )
        except json.JSONDecodeError as exc:
            raise HTTPException(400, "storage_state must be valid JSON") from exc
        except ValueError as exc:
            status = 400 if str(exc).startswith("storage_state") else 409
            raise HTTPException(status, str(exc)) from exc
        await manager.invalidate(account.id)
        return {"ok": True, "account_id": account.id, "message": "Credentials updated"}

    @application.get("/admin/api/accounts", tags=["Admin"])
    async def list_accounts(_: AdminDep) -> dict[str, object]:
        return {"ok": True, "accounts": await asyncio.to_thread(database.get_all_accounts)}

    @application.delete("/admin/api/accounts/{account_id}", tags=["Admin"])
    async def delete_account(account_id: int, _: AdminDep) -> dict[str, object]:
        await manager.invalidate(account_id)
        deleted = await asyncio.to_thread(database.delete_account_by_id, account_id)
        if not deleted:
            raise HTTPException(404, "Account not found")
        return {"ok": True}

    @application.put("/admin/api/accounts/{account_id}/status", tags=["Admin"])
    async def update_status(
        account_id: int, body: StatusUpdate, _: AdminDep
    ) -> dict[str, object]:
        updated = await asyncio.to_thread(database.update_account_status, account_id, body.status)
        if not updated:
            raise HTTPException(404, "Account not found")
        if body.status != "active":
            await manager.invalidate(account_id)
        return {"ok": True, "status": body.status}

    @application.put("/admin/api/accounts/{account_id}/key", tags=["Admin"])
    async def update_key(
        account_id: int, body: KeyUpdate, _: AdminDep
    ) -> dict[str, object]:
        api_key = body.api_key.strip()
        if any(char.isspace() for char in api_key):
            raise HTTPException(400, "API key cannot contain whitespace")
        try:
            _, account = await asyncio.to_thread(database.update_account_key, account_id, api_key)
        except KeyError as exc:
            raise HTTPException(404, "Account not found") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        await manager.invalidate(account.id)
        return {"ok": True}

    application.include_router(create_api_router())

    @application.get("/admin", response_class=HTMLResponse, include_in_schema=False)
    async def admin_page() -> HTMLResponse:
        path = Path(__file__).with_name("admin.html")
        if not path.exists():
            raise HTTPException(404, "Admin console not found")
        return HTMLResponse(path.read_text("utf-8"))

    packaged_noteweb = Path(__file__).with_name("noteweb")
    noteweb = packaged_noteweb if packaged_noteweb.exists() else ROOT / "noteweb"
    if noteweb.exists():
        application.mount("/noteweb", StaticFiles(directory=noteweb, html=True), name="noteweb")

    @application.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/noteweb/")

    return application


app = create_app()
