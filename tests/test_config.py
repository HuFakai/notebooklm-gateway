import pytest

from gateway_server.config import Settings


def test_rejects_placeholder_admin_token(monkeypatch, tmp_path):
    monkeypatch.setenv("GATEWAY_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GATEWAY_ADMIN_TOKEN", "请替换为至少32字节的强随机令牌")

    with pytest.raises(RuntimeError, match="strong random value"):
        Settings.from_env()


def test_rejects_wildcard_cors(monkeypatch, tmp_path):
    monkeypatch.setenv("GATEWAY_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GATEWAY_ADMIN_TOKEN", "a-secure-administrator-token-over-32-bytes")
    monkeypatch.setenv("GATEWAY_CORS_ORIGINS", "*")

    with pytest.raises(RuntimeError, match="cannot contain"):
        Settings.from_env()
