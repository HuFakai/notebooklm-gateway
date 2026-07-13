from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


@dataclass(frozen=True, slots=True)
class Account:
    id: int
    email: str
    api_key: str
    storage_state: str
    status: str
    updated_at: str
    master_token: str = ""
    android_id: str = ""


class DatabaseManager:
    """SQLite store with encrypted credentials and restart-safe artifact jobs."""

    _ENC_PREFIX = "enc:v1:"

    def __init__(self, data_dir: str | Path = "data", encryption_key: str | None = None):
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "gateway.db"
        key = self._load_key(encryption_key)
        self._fernet = Fernet(key)
        self._hmac_key = hashlib.sha256(
            base64.urlsafe_b64decode(key) + b"notebooklm-gateway-api-key-index"
        ).digest()
        self._init_db()
        self._migrate_plaintext_credentials()

    def _load_key(self, configured: str | None) -> bytes:
        env_key = configured or os.getenv("GATEWAY_ENCRYPTION_KEY")
        if env_key:
            return env_key.encode("ascii")
        key_path = self.data_dir / ".gateway-key"
        if key_path.exists():
            return key_path.read_bytes().strip()
        key = Fernet.generate_key()
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(key + b"\n")
        return key

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    master_token TEXT NOT NULL DEFAULT '',
                    storage_state TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active', 'disabled', 'expired')),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS artifact_jobs (
                    account_id INTEGER NOT NULL,
                    task_id TEXT NOT NULL,
                    notebook_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(account_id, task_id),
                    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_artifact_jobs_notebook
                    ON artifact_jobs(account_id, notebook_id, updated_at DESC);
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(accounts)")}
            if "api_key_hash" not in columns:
                conn.execute("ALTER TABLE accounts ADD COLUMN api_key_hash TEXT")
            if "android_id" not in columns:
                conn.execute("ALTER TABLE accounts ADD COLUMN android_id TEXT NOT NULL DEFAULT ''")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_api_key_hash ON accounts(api_key_hash)"
            )

    def _digest(self, value: str) -> str:
        return hmac.new(self._hmac_key, value.encode(), hashlib.sha256).hexdigest()

    def _encrypt(self, value: str) -> str:
        if not value or value.startswith(self._ENC_PREFIX):
            return value
        token = self._fernet.encrypt(value.encode()).decode("ascii")
        return self._ENC_PREFIX + token

    def _decrypt(self, value: str) -> str:
        if not value or not value.startswith(self._ENC_PREFIX):
            return value
        try:
            return self._fernet.decrypt(value[len(self._ENC_PREFIX) :].encode("ascii")).decode()
        except InvalidToken as exc:
            raise RuntimeError("Credential encryption key does not match the database") from exc

    def _migrate_plaintext_credentials(self) -> None:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, api_key, master_token, storage_state, android_id, api_key_hash FROM accounts"
            ).fetchall()
            for row in rows:
                api_key = self._decrypt(row["api_key"])
                needs_migration = not row["api_key_hash"] or any(
                    value and not value.startswith(self._ENC_PREFIX)
                    for value in (
                        row["api_key"],
                        row["master_token"],
                        row["storage_state"],
                        row["android_id"],
                    )
                )
                if not needs_migration:
                    continue
                conn.execute(
                    """UPDATE accounts
                       SET api_key=?, api_key_hash=?, master_token=?, storage_state=?, android_id=?
                       WHERE id=?""",
                    (
                        self._encrypt(row["api_key"]),
                        row["api_key_hash"] or self._digest(api_key),
                        self._encrypt(row["master_token"]),
                        self._encrypt(row["storage_state"]),
                        self._encrypt(row["android_id"]),
                        row["id"],
                    ),
                )

    def save_account(
        self,
        email: str,
        api_key: str,
        storage_state: str,
        master_token: str = "",
        android_id: str = "",
    ) -> Account:
        json.loads(storage_state)
        now = datetime.now(UTC).isoformat()
        digest = self._digest(api_key)
        with self._get_connection() as conn:
            duplicate = conn.execute(
                "SELECT email FROM accounts WHERE api_key_hash=? AND email<>?", (digest, email)
            ).fetchone()
            if duplicate:
                raise ValueError(f"API key is already used by {duplicate['email']}")
            conn.execute(
                """
                INSERT INTO accounts
                    (email, api_key, api_key_hash, master_token, storage_state, android_id, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                ON CONFLICT(email) DO UPDATE SET
                    api_key=excluded.api_key,
                    api_key_hash=excluded.api_key_hash,
                    master_token=excluded.master_token,
                    storage_state=excluded.storage_state,
                    android_id=excluded.android_id,
                    status='active',
                    updated_at=excluded.updated_at
                """,
                (
                    email,
                    self._encrypt(api_key),
                    digest,
                    self._encrypt(master_token),
                    self._encrypt(storage_state),
                    self._encrypt(android_id),
                    now,
                ),
            )
        account = self.get_account_by_api_key(api_key, active_only=False)
        if account is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("Account write was not visible")
        return account

    def _account_from_row(self, row: sqlite3.Row) -> Account:
        return Account(
            id=row["id"],
            email=row["email"],
            api_key=self._decrypt(row["api_key"]),
            master_token=self._decrypt(row["master_token"]),
            storage_state=self._decrypt(row["storage_state"]),
            android_id=self._decrypt(row["android_id"]),
            status=row["status"],
            updated_at=row["updated_at"],
        )

    def get_account_by_api_key(self, api_key: str, *, active_only: bool = True) -> Account | None:
        query = "SELECT * FROM accounts WHERE api_key_hash=?"
        params: tuple[Any, ...] = (self._digest(api_key),)
        if active_only:
            query += " AND status='active'"
        with self._get_connection() as conn:
            row = conn.execute(query, params).fetchone()
        return self._account_from_row(row) if row else None

    def get_account_by_id(self, account_id: int) -> Account | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        return self._account_from_row(row) if row else None

    def get_all_accounts(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM accounts ORDER BY updated_at DESC").fetchall()
        result = []
        for row in rows:
            account = self._account_from_row(row)
            result.append(
                {
                    "id": account.id,
                    "email": account.email,
                    "api_key": account.api_key,
                    "status": account.status,
                    "updated_at": account.updated_at,
                }
            )
        return result

    def delete_account_by_id(self, account_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
        return cursor.rowcount > 0

    def update_account_status(self, account_id: int, status: str) -> bool:
        if status not in {"active", "disabled", "expired"}:
            raise ValueError("status must be active, disabled, or expired")
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE accounts SET status=?, updated_at=? WHERE id=?",
                (status, datetime.now(UTC).isoformat(), account_id),
            )
        return cursor.rowcount > 0

    def update_account_key(self, account_id: int, api_key: str) -> tuple[str, Account]:
        account = self.get_account_by_id(account_id)
        if not account:
            raise KeyError(account_id)
        digest = self._digest(api_key)
        with self._get_connection() as conn:
            duplicate = conn.execute(
                "SELECT id FROM accounts WHERE api_key_hash=? AND id<>?", (digest, account_id)
            ).fetchone()
            if duplicate:
                raise ValueError("API key is already in use")
            conn.execute(
                "UPDATE accounts SET api_key=?, api_key_hash=?, updated_at=? WHERE id=?",
                (self._encrypt(api_key), digest, datetime.now(UTC).isoformat(), account_id),
            )
        updated = self.get_account_by_id(account_id)
        assert updated is not None
        return account.api_key, updated

    def update_storage_state(self, account_id: int, storage_state: str) -> None:
        json.loads(storage_state)
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE accounts SET storage_state=?, updated_at=? WHERE id=?",
                (self._encrypt(storage_state), datetime.now(UTC).isoformat(), account_id),
            )

    def save_job(
        self,
        account_id: int,
        notebook_id: str,
        task_id: str,
        artifact_type: str,
        status: str,
        request: dict[str, Any],
        error: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO artifact_jobs
                    (account_id, task_id, notebook_id, artifact_type, status, request_json,
                     error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, task_id) DO UPDATE SET
                    status=excluded.status, error=excluded.error, updated_at=excluded.updated_at
                """,
                (
                    account_id,
                    task_id,
                    notebook_id,
                    artifact_type,
                    status,
                    json.dumps(request, ensure_ascii=False),
                    error,
                    now,
                    now,
                ),
            )

    def get_job(self, account_id: int, notebook_id: str, task_id: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM artifact_jobs
                   WHERE account_id=? AND notebook_id=? AND task_id=?""",
                (account_id, notebook_id, task_id),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["request"] = json.loads(result.pop("request_json"))
        return result

    def list_jobs(self, account_id: int, notebook_id: str) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM artifact_jobs
                   WHERE account_id=? AND notebook_id=? ORDER BY updated_at DESC LIMIT 100""",
                (account_id, notebook_id),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["request"] = json.loads(item.pop("request_json"))
            result.append(item)
        return result
