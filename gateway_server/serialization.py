from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


ARTIFACT_STATUS = {1: "in_progress", 2: "pending", 3: "completed", 4: "failed"}
SOURCE_STATUS = {1: "processing", 2: "ready", 3: "error"}


def jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value if isinstance(value.value, str) else value.name.lower()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if is_dataclass(value):
        result = {
            field.name: jsonable(getattr(value, field.name))
            for field in fields(value)
            if not field.name.startswith("_") and field.name != "raw_response"
        }
        class_name = value.__class__.__name__
        if class_name == "Artifact":
            result["type"] = value.kind.value
            result["status_code"] = value.status
            result["status"] = ARTIFACT_STATUS.get(value.status, "unknown")
        elif class_name == "Source":
            result["type"] = value.kind.value
            result["status_code"] = int(value.status)
            result["status"] = SOURCE_STATUS.get(int(value.status), "unknown")
        elif hasattr(value, "kind"):
            result["type"] = jsonable(value.kind)
        return result
    if hasattr(value, "to_dict"):
        return jsonable(value.to_dict())
    return str(value)
