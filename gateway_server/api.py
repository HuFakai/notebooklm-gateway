from __future__ import annotations

import asyncio
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from notebooklm import (
    AudioFormat,
    AudioLength,
    ChatGoal,
    ChatMode,
    ChatResponseLength,
    InfographicDetail,
    InfographicOrientation,
    InfographicStyle,
    QuizDifficulty,
    QuizQuantity,
    ReportFormat,
    SharePermission,
    ShareViewLevel,
    SlideDeckFormat,
    SlideDeckLength,
    VideoFormat,
    VideoStyle,
    __version__ as notebooklm_version,
)

from .database import Account
from .schemas import (
    ArtifactDownload,
    ArtifactGenerate,
    ChatAsk,
    ChatConfigure,
    NoteBody,
    NotebookCreate,
    NotebookRename,
    ResearchImportBody,
    ResearchStartBody,
    SharePermissionUpdate,
    SharePublic,
    ShareUser,
    ShareView,
    SourceBatch,
    SourceDrive,
    SourceText,
    SourceURL,
    SourceWait,
    TitleUpdate,
)
from .serialization import jsonable


def _enum(enum_type: type, value: str | None):
    return enum_type.__members__[value.upper()] if value else None


async def get_account(request: Request) -> Account:
    auth = request.headers.get("Authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Missing or invalid Bearer token")
    if token == request.app.state.settings.admin_token:
        raise HTTPException(403, "Admin token cannot call notebook APIs")
    account = await asyncio.to_thread(request.app.state.db.get_account_by_api_key, token)
    if not account:
        raise HTTPException(401, "Invalid API key or account is inactive")
    return account


async def get_client(
    request: Request, account: Annotated[Account, Depends(get_account)]
) -> AsyncIterator[Any]:
    async with request.app.state.clients.acquire(account) as client:
        yield client


AccountDep = Annotated[Account, Depends(get_account)]
ClientDep = Annotated[Any, Depends(get_client)]


def create_api_router() -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.get("/server/info")
    async def server_info(account: AccountDep) -> dict[str, Any]:
        return {
            "name": "notebooklm-gateway",
            "version": "0.2.0",
            "sdk_version": notebooklm_version,
            "account": {"id": account.id, "email": account.email, "status": account.status},
            "capabilities": {
                "multi_tenant": True,
                "persistent_jobs": True,
                "artifact_types": [
                    "audio", "video", "cinematic_video", "report", "quiz", "flashcards",
                    "infographic", "slide_deck", "data_table", "mind_map",
                ],
            },
        }

    @router.get("/notebooks")
    async def list_notebooks(client: ClientDep) -> dict[str, Any]:
        return {"notebooks": jsonable(await client.notebooks.list())}

    @router.post("/notebooks", status_code=201)
    async def create_notebook(body: NotebookCreate, client: ClientDep) -> Any:
        return jsonable(await client.notebooks.create(body.title.strip()))

    @router.get("/notebooks/{notebook_id}")
    async def get_notebook(notebook_id: str, client: ClientDep) -> Any:
        return jsonable(await client.notebooks.get(notebook_id))

    @router.patch("/notebooks/{notebook_id}")
    async def rename_notebook(notebook_id: str, body: NotebookRename, client: ClientDep) -> Any:
        return jsonable(await client.notebooks.rename(notebook_id, body.title.strip()))

    @router.delete("/notebooks/{notebook_id}", status_code=204)
    async def delete_notebook(notebook_id: str, client: ClientDep) -> Response:
        await client.notebooks.delete(notebook_id)
        return Response(status_code=204)

    @router.get("/notebooks/{notebook_id}/suggested-prompts")
    async def suggested_prompts(notebook_id: str, client: ClientDep) -> dict[str, Any]:
        description = await client.notebooks.get_description(notebook_id)
        return {"suggestions": jsonable(description.suggested_topics)}

    @router.get("/notebooks/{notebook_id}/description")
    async def notebook_description(notebook_id: str, client: ClientDep) -> Any:
        return jsonable(await client.notebooks.get_description(notebook_id))

    @router.get("/notebooks/{notebook_id}/sources")
    async def list_sources(notebook_id: str, client: ClientDep) -> dict[str, Any]:
        return {"sources": jsonable(await client.sources.list(notebook_id))}

    @router.get("/notebooks/{notebook_id}/sources/{source_id}")
    async def get_source(notebook_id: str, source_id: str, client: ClientDep) -> Any:
        source = await client.sources.get(notebook_id, source_id)
        if source is None:
            raise HTTPException(404, "Source not found")
        return jsonable(source)

    @router.post("/notebooks/{notebook_id}/sources/url", status_code=201)
    async def add_url(notebook_id: str, body: SourceURL, client: ClientDep) -> Any:
        return jsonable(await client.sources.add_url(notebook_id, body.url))

    @router.post("/notebooks/{notebook_id}/sources/text", status_code=201)
    async def add_text(notebook_id: str, body: SourceText, client: ClientDep) -> Any:
        return jsonable(await client.sources.add_text(notebook_id, body.title, body.text))

    @router.post("/notebooks/{notebook_id}/sources/drive", status_code=201)
    async def add_drive(notebook_id: str, body: SourceDrive, client: ClientDep) -> Any:
        return jsonable(
            await client.sources.add_drive(notebook_id, body.file_id, body.title, body.mime_type)
        )

    @router.post("/notebooks/{notebook_id}/sources/batch", status_code=201)
    async def add_batch(notebook_id: str, body: SourceBatch, client: ClientDep) -> dict[str, Any]:
        results = await asyncio.gather(
            *(client.sources.add_url(notebook_id, url) for url in body.urls),
            return_exceptions=True,
        )
        return {
            "sources": [jsonable(item) for item in results if not isinstance(item, Exception)],
            "errors": [str(item) for item in results if isinstance(item, Exception)],
        }

    @router.post("/notebooks/{notebook_id}/sources/file", status_code=201)
    async def add_file(
        request: Request,
        notebook_id: str,
        client: ClientDep,
        file: UploadFile = File(...),
    ) -> Any:
        suffix = Path(file.filename or "upload.bin").suffix
        fd, temp_name = tempfile.mkstemp(suffix=suffix, dir=request.app.state.settings.data_dir)
        total = 0
        try:
            with os.fdopen(fd, "wb") as handle:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > request.app.state.settings.max_upload_bytes:
                        raise HTTPException(413, "Uploaded file is too large")
                    handle.write(chunk)
            result = await client.sources.add_file(
                notebook_id, temp_name, mime_type=file.content_type, title=file.filename
            )
            return jsonable(result)
        finally:
            await file.close()
            Path(temp_name).unlink(missing_ok=True)

    @router.post("/notebooks/{notebook_id}/sources/wait")
    async def wait_sources(notebook_id: str, body: SourceWait, client: ClientDep) -> dict[str, Any]:
        source_ids = body.source_ids or [item.id for item in await client.sources.list(notebook_id)]

        async def wait_one(source_id: str):
            return await client.sources.wait_until_ready(
                notebook_id, source_id, timeout=body.timeout, initial_interval=body.interval
            )

        results = await asyncio.gather(*(wait_one(item) for item in source_ids), return_exceptions=True)
        return {
            "sources": [jsonable(item) for item in results if not isinstance(item, Exception)],
            "errors": [str(item) for item in results if isinstance(item, Exception)],
        }

    @router.get("/notebooks/{notebook_id}/sources/{source_id}/content")
    @router.get("/notebooks/{notebook_id}/sources/{source_id}/text")
    async def source_content(notebook_id: str, source_id: str, client: ClientDep) -> Any:
        result = jsonable(await client.sources.get_fulltext(notebook_id, source_id))
        if isinstance(result, dict):
            result["text"] = result.get("content", "")
        return result

    @router.get("/notebooks/{notebook_id}/sources/{source_id}/guide")
    async def source_guide(notebook_id: str, source_id: str, client: ClientDep) -> Any:
        return jsonable(await client.sources.get_guide(notebook_id, source_id))

    @router.patch("/notebooks/{notebook_id}/sources/{source_id}")
    async def rename_source(
        notebook_id: str, source_id: str, body: TitleUpdate, client: ClientDep
    ) -> Any:
        return jsonable(await client.sources.rename(notebook_id, source_id, body.title))

    @router.delete("/notebooks/{notebook_id}/sources/{source_id}", status_code=204)
    async def delete_source(notebook_id: str, source_id: str, client: ClientDep) -> Response:
        await client.sources.delete(notebook_id, source_id)
        return Response(status_code=204)

    @router.post("/notebooks/{notebook_id}/chat")
    async def chat(notebook_id: str, body: ChatAsk, client: ClientDep) -> Any:
        return jsonable(
            await client.chat.ask(
                notebook_id,
                body.question,
                source_ids=body.source_ids,
                conversation_id=body.conversation_id,
            )
        )

    @router.post("/notebooks/{notebook_id}/chat/configure")
    async def configure_chat(notebook_id: str, body: ChatConfigure, client: ClientDep) -> dict[str, Any]:
        if body.chat_mode:
            await client.chat.set_mode(notebook_id, _enum(ChatMode, body.chat_mode))
        else:
            await client.chat.configure(
                notebook_id,
                goal=_enum(ChatGoal, body.goal),
                response_length=_enum(ChatResponseLength, body.response_length),
                custom_prompt=body.custom_prompt,
            )
        return {"ok": True}

    @router.post("/notebooks/{notebook_id}/research", status_code=202)
    async def start_research(
        notebook_id: str, body: ResearchStartBody, client: ClientDep
    ) -> Any:
        result = await client.research.start(notebook_id, body.query, body.source, body.mode)
        if result is None:
            raise HTTPException(502, "NotebookLM did not start a research task")
        return jsonable(result)

    @router.get("/notebooks/{notebook_id}/research/{run_id}")
    async def research_status(notebook_id: str, run_id: str, client: ClientDep) -> Any:
        return jsonable(await client.research.poll(notebook_id, run_id))

    @router.delete("/notebooks/{notebook_id}/research/{run_id}")
    async def cancel_research(notebook_id: str, run_id: str, account: AccountDep) -> Any:
        del notebook_id, run_id, account
        raise HTTPException(
            501,
            "notebooklm-py 0.7.3 has no public research cancellation API; the task continues upstream",
        )

    @router.post("/notebooks/{notebook_id}/research/{run_id}/import", status_code=201)
    async def import_research(
        notebook_id: str,
        run_id: str,
        client: ClientDep,
        body: ResearchImportBody | None = None,
    ) -> dict[str, Any]:
        sources = body.sources if body and body.sources is not None else None
        if sources is None:
            task = await client.research.poll(notebook_id, run_id)
            sources = list(task.sources)
        return {
            "sources": jsonable(
                await client.research.import_sources_with_verification(notebook_id, run_id, sources)
            )
        }

    @router.get("/notebooks/{notebook_id}/notes")
    async def list_notes(notebook_id: str, client: ClientDep) -> dict[str, Any]:
        return {"notes": jsonable(await client.notes.list(notebook_id))}

    @router.get("/notebooks/{notebook_id}/notes/{note_id}")
    async def get_note(notebook_id: str, note_id: str, client: ClientDep) -> Any:
        result = await client.notes.get(notebook_id, note_id)
        if result is None:
            raise HTTPException(404, "Note not found")
        return jsonable(result)

    @router.post("/notebooks/{notebook_id}/notes", status_code=201)
    async def create_note(notebook_id: str, body: NoteBody, client: ClientDep) -> Any:
        return jsonable(await client.notes.create(notebook_id, body.title, body.content))

    @router.put("/notebooks/{notebook_id}/notes/{note_id}")
    async def update_note(
        notebook_id: str, note_id: str, body: NoteBody, client: ClientDep
    ) -> dict[str, Any]:
        await client.notes.update(notebook_id, note_id, body.content, body.title)
        return {"ok": True}

    @router.delete("/notebooks/{notebook_id}/notes/{note_id}", status_code=204)
    async def delete_note(notebook_id: str, note_id: str, client: ClientDep) -> Response:
        await client.notes.delete(notebook_id, note_id)
        return Response(status_code=204)

    @router.get("/notebooks/{notebook_id}/artifacts")
    async def list_artifacts(
        request: Request, notebook_id: str, account: AccountDep, client: ClientDep
    ) -> dict[str, Any]:
        artifacts = jsonable(await client.artifacts.list(notebook_id))
        jobs = await asyncio.to_thread(request.app.state.db.list_jobs, account.id, notebook_id)
        known = {item["id"] for item in artifacts}
        for job in jobs:
            if job["task_id"] not in known and job["status"] not in {"completed", "removed"}:
                artifacts.append(
                    {
                        "id": job["task_id"],
                        "task_id": job["task_id"],
                        "title": job["request"].get("title") or "正在生成",
                        "type": job["artifact_type"],
                        "status": job["status"],
                        "created_at": job["created_at"],
                        "error": job["error"],
                    }
                )
        return {"artifacts": artifacts, "jobs": jobs}

    @router.post("/notebooks/{notebook_id}/artifacts", status_code=202)
    async def generate_artifact(
        request: Request,
        notebook_id: str,
        body: ArtifactGenerate,
        account: AccountDep,
        client: ClientDep,
    ) -> Any:
        common = {"source_ids": body.source_ids}
        localized = {**common, "language": body.language}
        artifact_type = body.type
        if artifact_type == "audio":
            result = await client.artifacts.generate_audio(
                notebook_id,
                **localized,
                instructions=body.instructions,
                audio_format=_enum(AudioFormat, body.audio_format),
                audio_length=_enum(AudioLength, body.audio_length),
            )
        elif artifact_type == "video":
            result = await client.artifacts.generate_video(
                notebook_id,
                **localized,
                instructions=body.instructions,
                video_format=_enum(VideoFormat, body.video_format),
                video_style=_enum(VideoStyle, body.video_style),
                style_prompt=body.style_prompt,
            )
        elif artifact_type == "cinematic_video":
            result = await client.artifacts.generate_cinematic_video(
                notebook_id, **localized, instructions=body.instructions
            )
        elif artifact_type == "report":
            result = await client.artifacts.generate_report(
                notebook_id,
                report_format=ReportFormat(body.report_format or "briefing_doc"),
                **localized,
                custom_prompt=body.custom_prompt,
                extra_instructions=body.extra_instructions or body.instructions,
            )
        elif artifact_type in {"quiz", "flashcards"}:
            method = (
                client.artifacts.generate_quiz
                if artifact_type == "quiz"
                else client.artifacts.generate_flashcards
            )
            result = await method(
                notebook_id,
                **common,
                instructions=body.instructions,
                quantity=_enum(QuizQuantity, body.quantity),
                difficulty=_enum(QuizDifficulty, body.difficulty),
            )
        elif artifact_type == "infographic":
            result = await client.artifacts.generate_infographic(
                notebook_id,
                **localized,
                instructions=body.instructions,
                orientation=_enum(InfographicOrientation, body.orientation),
                detail_level=_enum(InfographicDetail, body.detail_level),
                style=_enum(InfographicStyle, body.infographic_style),
            )
        elif artifact_type == "slide_deck":
            result = await client.artifacts.generate_slide_deck(
                notebook_id,
                **localized,
                instructions=body.instructions,
                slide_format=_enum(SlideDeckFormat, body.slide_format),
                slide_length=_enum(SlideDeckLength, body.slide_length),
            )
        elif artifact_type == "data_table":
            result = await client.artifacts.generate_data_table(
                notebook_id, **localized, instructions=body.instructions
            )
        else:
            mind_map = await client.artifacts.generate_mind_map(
                notebook_id, **localized, instructions=body.instructions
            )
            task_id = mind_map.note_id or "mind-map-completed"
            result = {"task_id": task_id, "status": "completed", "result": jsonable(mind_map)}

        payload = body.model_dump(exclude_none=True)
        result_data = jsonable(result)
        task_id = result_data.get("task_id")
        if task_id:
            await asyncio.to_thread(
                request.app.state.db.save_job,
                account.id,
                notebook_id,
                task_id,
                artifact_type,
                result_data.get("status", "pending"),
                payload,
                result_data.get("error"),
            )
        return result_data

    @router.get("/notebooks/{notebook_id}/artifacts/{task_id}")
    async def poll_artifact(
        request: Request,
        notebook_id: str,
        task_id: str,
        account: AccountDep,
        client: ClientDep,
    ) -> Any:
        job = await asyncio.to_thread(
            request.app.state.db.get_job, account.id, notebook_id, task_id
        )
        if not job:
            raise HTTPException(404, "Unknown artifact task for this account and notebook")
        result = jsonable(await client.artifacts.poll_status(notebook_id, task_id))
        await asyncio.to_thread(
            request.app.state.db.save_job,
            account.id,
            notebook_id,
            task_id,
            job["artifact_type"],
            result["status"],
            job["request"],
            result.get("error"),
        )
        result["type"] = job["artifact_type"]
        return result

    @router.get("/notebooks/{notebook_id}/artifacts/{artifact_id}/prompt")
    async def artifact_prompt(
        request: Request, notebook_id: str, artifact_id: str, account: AccountDep
    ) -> dict[str, Any]:
        job = await asyncio.to_thread(
            request.app.state.db.get_job, account.id, notebook_id, artifact_id
        )
        if not job:
            raise HTTPException(404, "Generation parameters are not available")
        return {"prompt": job["request"].get("instructions"), "parameters": job["request"]}

    @router.patch("/notebooks/{notebook_id}/artifacts/{artifact_id}")
    async def rename_artifact(
        notebook_id: str, artifact_id: str, body: TitleUpdate, client: ClientDep
    ) -> Any:
        return jsonable(await client.artifacts.rename(notebook_id, artifact_id, body.title))

    @router.post("/notebooks/{notebook_id}/artifacts/{artifact_id}/retry", status_code=202)
    async def retry_artifact(
        request: Request,
        notebook_id: str,
        artifact_id: str,
        account: AccountDep,
        client: ClientDep,
    ) -> Any:
        job = await asyncio.to_thread(
            request.app.state.db.get_job, account.id, notebook_id, artifact_id
        )
        if not job:
            raise HTTPException(404, "Artifact job not found")
        result = jsonable(await client.artifacts.retry_failed(notebook_id, artifact_id))
        await asyncio.to_thread(
            request.app.state.db.save_job,
            account.id,
            notebook_id,
            artifact_id,
            job["artifact_type"],
            result["status"],
            job["request"],
            result.get("error"),
        )
        return result

    @router.delete("/notebooks/{notebook_id}/artifacts/{artifact_id}", status_code=204)
    async def delete_artifact(notebook_id: str, artifact_id: str, client: ClientDep) -> Response:
        await client.artifacts.delete(notebook_id, artifact_id)
        return Response(status_code=204)

    @router.post("/notebooks/{notebook_id}/artifacts/download")
    async def download_artifact(
        notebook_id: str,
        body: ArtifactDownload,
        background_tasks: BackgroundTasks,
        client: ClientDep,
    ) -> FileResponse:
        defaults = {
            "audio": ("download_audio", ".mp3"),
            "video": ("download_video", ".mp4"),
            "report": ("download_report", ".md"),
            "quiz": ("download_quiz", ".json"),
            "flashcards": ("download_flashcards", ".json"),
            "infographic": ("download_infographic", ".png"),
            "slide_deck": ("download_slide_deck", ".pdf"),
            "data_table": ("download_data_table", ".csv"),
            "mind_map": ("download_mind_map", ".json"),
        }
        method_name, suffix = defaults[body.type]
        method = getattr(client.artifacts, method_name)
        output_format = body.output_format
        if body.type == "slide_deck" and output_format == "pptx":
            suffix = ".pptx"
        elif body.type in {"quiz", "flashcards"} and output_format == "markdown":
            suffix = ".md"
        fd, output_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        kwargs: dict[str, Any] = {"artifact_id": body.artifact_id}
        if body.type in {"slide_deck", "quiz", "flashcards"}:
            kwargs["output_format"] = output_format or ("pdf" if body.type == "slide_deck" else "json")
        try:
            await method(notebook_id, output_path, **kwargs)
        except Exception:
            Path(output_path).unlink(missing_ok=True)
            raise
        background_tasks.add_task(Path(output_path).unlink, missing_ok=True)
        media_type = mimetypes.guess_type(output_path)[0] or "application/octet-stream"
        return FileResponse(
            output_path,
            media_type=media_type,
            filename=f"{body.type}-{body.artifact_id}{suffix}",
            background=background_tasks,
        )

    @router.get("/notebooks/{notebook_id}/share")
    async def share_status(notebook_id: str, client: ClientDep) -> Any:
        return jsonable(await client.sharing.get_status(notebook_id))

    @router.post("/notebooks/{notebook_id}/share/public")
    async def share_public(notebook_id: str, body: SharePublic, client: ClientDep) -> Any:
        return jsonable(await client.sharing.set_public(notebook_id, body.public))

    @router.post("/notebooks/{notebook_id}/share/users", status_code=201)
    async def share_add_user(notebook_id: str, body: ShareUser, client: ClientDep) -> Any:
        return jsonable(
            await client.sharing.add_user(
                notebook_id,
                str(body.email),
                _enum(SharePermission, body.permission),
                body.notify,
                body.welcome_message,
            )
        )

    @router.patch("/notebooks/{notebook_id}/share/users/{email}")
    async def share_update_user(
        notebook_id: str, email: str, body: SharePermissionUpdate, client: ClientDep
    ) -> Any:
        return jsonable(
            await client.sharing.update_user(
                notebook_id, email, _enum(SharePermission, body.permission)
            )
        )

    @router.delete("/notebooks/{notebook_id}/share/users/{email}", status_code=204)
    async def share_remove_user(notebook_id: str, email: str, client: ClientDep) -> Response:
        await client.sharing.remove_user(notebook_id, email)
        return Response(status_code=204)

    @router.post("/notebooks/{notebook_id}/share/view-level")
    async def share_view_level(notebook_id: str, body: ShareView, client: ClientDep) -> Any:
        return jsonable(
            await client.sharing.set_view_level(notebook_id, _enum(ShareViewLevel, body.level))
        )

    return router
