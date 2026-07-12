import os
import sqlite3
import json
from datetime import datetime

# 默认数据库路径，放置在可持久化的 data/ 目录下
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "gateway.db")

class DatabaseManager:
    def __init__(self):
        # 确保数据目录存在
        os.makedirs(DB_DIR, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 支持通过列名访问
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    master_token TEXT NOT NULL,
                    storage_state TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_account(self, email: str, api_key: str, master_token: str, storage_state: str) -> bool:
        """保存或更新账号凭据和 API Key"""
        try:
            # 校验 storage_state 是否是合法的 JSON 字符串
            json.loads(storage_state)
            
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO accounts (email, api_key, master_token, storage_state, status, updated_at)
                    VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
                    ON CONFLICT(email) DO UPDATE SET
                        api_key=excluded.api_key,
                        master_token=excluded.master_token,
                        storage_state=excluded.storage_state,
                        status='active',
                        updated_at=CURRENT_TIMESTAMP
                """, (email, api_key, master_token, storage_state))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error saving account: {e}")
            return False

    def get_account_by_api_key(self, api_key: str):
        """根据 API Key 查询账号"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM accounts WHERE api_key = ? AND status = 'active'", 
                (api_key,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_accounts(self):
        """获取所有账号列表（用于管理页面展示）"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, email, api_key, status, updated_at FROM accounts ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_account_by_id(self, account_id: int) -> bool:
        """删除指定账号"""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
                conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting account: {e}")
            return False

    def update_account_status(self, email: str, status: str) -> bool:
        """更新账号状态（例如 Cookie 失效时标记为 expired）"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE accounts SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?",
                    (status, email)
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"Error updating status: {e}")
            return False
