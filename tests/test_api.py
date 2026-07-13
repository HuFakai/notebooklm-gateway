from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from gateway_server.config import Settings
from gateway_server.database import DatabaseManager
from gateway_server.main import create_app


@dataclass
class FakeStatus:
    task_id: str
    status: str
    error: str | None = None


class FakeArtifacts:
    def __init__(self):
        self.audio_kwargs = None
        self.download_id = None

    async def list(self, notebook_id):
        return []

    async def generate_audio(self, notebook_id, **kwargs):
        self.audio_kwargs = kwargs
        return FakeStatus("task-audio", "pending")

    async def poll_status(self, notebook_id, task_id):
        return FakeStatus(task_id, "completed")

    async def download_audio(self, notebook_id, output_path, artifact_id=None):
        self.download_id = artifact_id
        Path(output_path).write_bytes(b"audio")
        return output_path

    async def delete(self, notebook_id, artifact_id):
        return None


class FakeNotebooks:
    async def list(self):
        return [{"id": "nb-1", "title": "Notebook"}]


class FakeManager:
    def __init__(self, client):
        self.client = client
        self.invalidated = []

    @asynccontextmanager
    async def acquire(self, account):
        yield self.client

    async def invalidate(self, account_id):
        self.invalidated.append(account_id)


def make_client(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        admin_token="admin-secret-token-long-enough",
        cors_origins=(),
    )
    db = DatabaseManager(tmp_path)
    account = db.save_account("user@example.com", "user-secret-key-0001", '{"cookies": []}')
    fake = SimpleNamespace(notebooks=FakeNotebooks(), artifacts=FakeArtifacts())
    app = create_app(settings, db)
    manager = FakeManager(fake)
    app.state.clients = manager
    return TestClient(app), fake, account


def test_user_and_admin_tokens_are_separated(tmp_path):
    client, _, _ = make_client(tmp_path)
    with client:
        assert client.get("/v1/notebooks").status_code == 401
        assert client.get(
            "/v1/notebooks", headers={"Authorization": "Bearer admin-secret-token-long-enough"}
        ).status_code == 403
        response = client.get(
            "/v1/notebooks", headers={"Authorization": "Bearer user-secret-key-0001"}
        )
    assert response.status_code == 200
    assert response.json()["notebooks"][0]["id"] == "nb-1"


def test_artifact_parameters_jobs_and_exact_download_id(tmp_path):
    client, fake, _ = make_client(tmp_path)
    headers = {"Authorization": "Bearer user-secret-key-0001"}
    with client:
        generated = client.post(
            "/v1/notebooks/nb-1/artifacts",
            headers=headers,
            json={
                "type": "audio",
                "language": "zh_Hans",
                "source_ids": ["source-1"],
                "instructions": "面向初学者",
                "audio_format": "debate",
                "audio_length": "long",
            },
        )
        assert generated.status_code == 202, generated.text
        assert generated.json() == {"task_id": "task-audio", "status": "pending", "error": None}
        assert fake.artifacts.audio_kwargs["language"] == "zh_Hans"
        assert fake.artifacts.audio_kwargs["audio_format"].name == "DEBATE"

        polled = client.get("/v1/notebooks/nb-1/artifacts/task-audio", headers=headers)
        assert polled.status_code == 200
        assert polled.json()["status"] == "completed"

        downloaded = client.post(
            "/v1/notebooks/nb-1/artifacts/download",
            headers=headers,
            json={"type": "audio", "artifact_id": "artifact-exact"},
        )
        assert downloaded.status_code == 200
        assert downloaded.content == b"audio"
        assert fake.artifacts.download_id == "artifact-exact"

        missing_id = client.post(
            "/v1/notebooks/nb-1/artifacts/download",
            headers=headers,
            json={"type": "audio"},
        )
        assert missing_id.status_code == 422


def test_unknown_task_cannot_be_polled(tmp_path):
    client, _, _ = make_client(tmp_path)
    with client:
        response = client.get(
            "/v1/notebooks/nb-1/artifacts/not-owned",
            headers={"Authorization": "Bearer user-secret-key-0001"},
        )
    assert response.status_code == 404
