from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class CredentialsUpload(BaseModel):
    email: EmailStr
    api_key: str = Field(min_length=16, max_length=256)
    storage_state: str
    master_token: str = ""
    android_id: str = ""

    @field_validator("api_key")
    @classmethod
    def clean_key(cls, value: str) -> str:
        value = value.strip()
        if any(char.isspace() for char in value):
            raise ValueError("API key cannot contain whitespace")
        return value


class StatusUpdate(BaseModel):
    status: Literal["active", "disabled", "expired"]


class KeyUpdate(BaseModel):
    api_key: str = Field(min_length=16, max_length=256)


class NotebookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)


class NotebookRename(NotebookCreate):
    pass


class SourceURL(BaseModel):
    url: str = Field(min_length=4, max_length=8192)


class SourceText(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=5_000_000)


class SourceBatch(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=50)


class SourceDrive(BaseModel):
    file_id: str
    title: str
    mime_type: str = "application/vnd.google-apps.document"


class SourceWait(BaseModel):
    source_ids: list[str] = Field(default_factory=list, max_length=100)
    timeout: float = Field(default=120, gt=0, le=1800)
    interval: float = Field(default=1, gt=0, le=30)


class TitleUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=500)


class ChatAsk(BaseModel):
    question: str = Field(min_length=1, max_length=20_000)
    source_ids: list[str] | None = None
    conversation_id: str | None = None


class ChatConfigure(BaseModel):
    chat_mode: Literal["default", "learning_guide", "concise", "detailed"] | None = None
    goal: Literal["default", "custom", "learning_guide"] | None = None
    response_length: Literal["default", "shorter", "longer"] | None = None
    custom_prompt: str | None = Field(default=None, max_length=10_000)


class ResearchStartBody(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    source: Literal["web", "drive"] = "web"
    mode: Literal["fast", "deep"] = "fast"


class ResearchImportBody(BaseModel):
    sources: list[dict] | None = None


class NoteBody(BaseModel):
    title: str = Field(default="New Note", max_length=500)
    content: str = Field(default="", max_length=2_000_000)


class ArtifactGenerate(BaseModel):
    type: Literal[
        "audio", "video", "cinematic_video", "report", "quiz", "flashcards",
        "infographic", "slide_deck", "data_table", "mind_map"
    ]
    source_ids: list[str] | None = None
    language: str = Field(default="zh_Hans", min_length=2, max_length=20)
    instructions: str | None = Field(default=None, max_length=20_000)
    audio_format: Literal["deep_dive", "brief", "critique", "debate"] | None = None
    audio_length: Literal["short", "default", "long"] | None = None
    video_format: Literal["explainer", "brief", "cinematic"] | None = None
    video_style: Literal[
        "auto_select", "custom", "classic", "whiteboard", "kawaii", "anime",
        "watercolor", "retro_print", "heritage", "paper_craft"
    ] | None = None
    style_prompt: str | None = Field(default=None, max_length=10_000)
    report_format: Literal["briefing_doc", "study_guide", "blog_post", "custom"] | None = None
    custom_prompt: str | None = Field(default=None, max_length=20_000)
    extra_instructions: str | None = Field(default=None, max_length=20_000)
    quantity: Literal["fewer", "standard", "more"] | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    orientation: Literal["landscape", "portrait", "square"] | None = None
    detail_level: Literal["concise", "standard", "detailed"] | None = None
    infographic_style: Literal[
        "auto_select", "sketch_note", "professional", "bento_grid", "editorial",
        "instructional", "bricks", "clay", "anime", "kawaii", "scientific"
    ] | None = None
    slide_format: Literal["detailed_deck", "presenter_slides"] | None = None
    slide_length: Literal["default", "short"] | None = None


class ArtifactDownload(BaseModel):
    type: Literal[
        "audio", "video", "report", "quiz", "flashcards", "infographic",
        "slide_deck", "data_table", "mind_map"
    ]
    artifact_id: str = Field(min_length=1)
    output_format: str | None = None


class SharePublic(BaseModel):
    public: bool


class ShareUser(BaseModel):
    email: EmailStr
    permission: Literal["viewer", "editor"] = "viewer"
    notify: bool = True
    welcome_message: str = ""


class SharePermissionUpdate(BaseModel):
    permission: Literal["viewer", "editor"]


class ShareView(BaseModel):
    level: Literal["full_notebook", "chat_only"]
