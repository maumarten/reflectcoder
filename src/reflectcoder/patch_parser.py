"""Shared, defensively-written JSON patch parser.

The model occasionally returns things like `{"files": "<the whole code>"}`
or paths containing newlines. Those shapes will blow up the sandbox if passed
through naively, so we validate here and reject anything suspicious. A None
return is treated by agents as a failed iteration, which the reflective loop
will recover from.
"""

from __future__ import annotations

import json
import re

from reflectcoder.schemas import Patch

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)
_MAX_PATH_LEN = 200
_FORBIDDEN_PATH_CHARS = set('\n\r\t\x00:*?"<>|')


def parse_patch(text: str) -> Patch | None:
    stripped = _FENCE.sub("", text).strip()
    payload = _try_json(stripped)
    if payload is None:
        match = _JSON_BLOCK.search(stripped)
        if match:
            payload = _try_json(match.group(0))
    if payload is None:
        return None

    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        return None

    clean: dict[str, str] = {}
    for path, content in files.items():
        if not _is_safe_path(path):
            return None
        if not isinstance(content, str):
            return None
        clean[path] = content

    return Patch(files=clean, rationale=str(payload.get("rationale", "")))


def _is_safe_path(path: object) -> bool:
    if not isinstance(path, str) or not path:
        return False
    if len(path) > _MAX_PATH_LEN:
        return False
    if any(ch in _FORBIDDEN_PATH_CHARS for ch in path):
        return False
    # Block path traversal; also block absolute paths on both POSIX and Windows.
    if ".." in path.replace("\\", "/").split("/"):
        return False
    if path.startswith(("/", "\\")) or (len(path) > 1 and path[1] == ":"):
        return False
    return True


def _try_json(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
