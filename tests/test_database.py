import sqlite3

import pytest

from gateway_server.database import DatabaseManager


def test_plaintext_accounts_are_migrated_and_lookup_is_hashed(tmp_path):
    db_path = tmp_path / "gateway.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                master_token TEXT NOT NULL,
                storage_state TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute(
            "INSERT INTO accounts(email, api_key, master_token, storage_state) VALUES (?, ?, ?, ?)",
            ("legacy@example.com", "legacy-secret-key", "old-master", '{"cookies": []}'),
        )

    db = DatabaseManager(tmp_path)
    account = db.get_account_by_api_key("legacy-secret-key")
    assert account is not None
    assert account.email == "legacy@example.com"
    assert account.storage_state == '{"cookies": []}'

    with sqlite3.connect(db_path) as conn:
        raw = conn.execute(
            "SELECT api_key, master_token, storage_state, api_key_hash FROM accounts"
        ).fetchone()
    assert all(value.startswith("enc:v1:") for value in raw[:3])
    assert raw[3] and "legacy-secret-key" not in raw[3]
    assert (tmp_path / ".gateway-key").stat().st_mode & 0o777 == 0o600


def test_account_keys_are_unique_and_jobs_are_tenant_scoped(tmp_path):
    db = DatabaseManager(tmp_path)
    first = db.save_account("a@example.com", "a-secret-key-0001", '{"cookies": []}')
    second = db.save_account("b@example.com", "b-secret-key-0002", '{"cookies": []}')

    with pytest.raises(ValueError):
        db.save_account("b@example.com", "a-secret-key-0001", '{"cookies": []}')

    db.save_job(first.id, "nb-1", "task-1", "audio", "pending", {"language": "zh_Hans"})
    assert db.get_job(first.id, "nb-1", "task-1")["artifact_type"] == "audio"
    assert db.get_job(second.id, "nb-1", "task-1") is None
