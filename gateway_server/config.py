from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise RuntimeError(f"{name} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    admin_token: str
    cors_origins: tuple[str, ...]
    max_clients: int = 20
    client_idle_seconds: int = 1800
    keepalive_seconds: int = 600
    max_upload_bytes: int = 100 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        admin_token = os.getenv("GATEWAY_ADMIN_TOKEN") or os.getenv("NOTEBOOKLM_ADMIN_TOKEN")
        rejected_tokens = {
            "admin_secret_token_change_me",
            "请替换为至少32字节的强随机令牌",
        }
        if not admin_token or admin_token in rejected_tokens or len(admin_token.encode()) < 32:
            raise RuntimeError(
                "Set GATEWAY_ADMIN_TOKEN to a strong random value of at least 32 bytes; "
                "example tokens are rejected."
            )
        data_dir = Path(os.getenv("GATEWAY_DATA_DIR", "data")).expanduser().resolve()
        cors = tuple(
            item.strip()
            for item in os.getenv("GATEWAY_CORS_ORIGINS", "").split(",")
            if item.strip()
        )
        if "*" in cors:
            raise RuntimeError(
                "GATEWAY_CORS_ORIGINS cannot contain '*'; list trusted origins explicitly."
            )
        return cls(
            data_dir=data_dir,
            admin_token=admin_token,
            cors_origins=cors,
            max_clients=_positive_int("GATEWAY_MAX_CLIENTS", 20),
            client_idle_seconds=_positive_int("GATEWAY_CLIENT_IDLE_SECONDS", 1800),
            keepalive_seconds=_positive_int("GATEWAY_KEEPALIVE_SECONDS", 600),
            max_upload_bytes=_positive_int("GATEWAY_MAX_UPLOAD_BYTES", 100 * 1024 * 1024),
        )
