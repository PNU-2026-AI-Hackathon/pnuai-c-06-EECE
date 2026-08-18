"""펌웨어 정적 분석 — 소스 적재 + 핀 사용 추출.

zip 이든 디렉터리든 {상대경로: 본문} 으로 만든 뒤 `analyze()` 에 넘긴다.
경로는 **업로드한 zip 내부 기준**이다. 서버 임시 경로가 화면에 새지 않는다.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from .arduino import (
    DIRECTION_INPUT,
    DIRECTION_OUTPUT,
    DIRECTION_UNKNOWN,
    SOURCE_SUFFIXES,
    Firmware,
    PinCall,
    PinUse,
    Unreadable,
    classify_unreadable,
    analyze,
    strip_noise,
)

__all__ = [
    "Firmware",
    "PinUse",
    "PinCall",
    "Unreadable",
    "classify_unreadable",
    "analyze",
    "strip_noise",
    "load_directory",
    "load_zip",
    "DIRECTION_INPUT",
    "DIRECTION_OUTPUT",
    "DIRECTION_UNKNOWN",
    "SOURCE_SUFFIXES",
]

#: 소스 파일 하나가 이보다 크면 코드가 아니다. 읽지 않는다.
MAX_SOURCE_BYTES = 1 * 1024 * 1024

#: zip 하나에서 읽을 소스 파일 수 상한
MAX_SOURCE_FILES = 400


def _wanted(name: str) -> bool:
    lowered = name.lower()
    if lowered.startswith("__macosx/") or "/." in f"/{lowered}":
        return False
    return lowered.endswith(SOURCE_SUFFIXES)


def load_zip(data: bytes) -> "dict[str, str]":
    """업로드한 zip 에서 소스만 골라 읽는다. 디스크에 풀지 않는다."""
    sources: "dict[str, str]" = {}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir() or not _wanted(info.filename):
                continue
            if info.file_size > MAX_SOURCE_BYTES:
                continue
            sources[info.filename] = zf.read(info).decode("utf-8", errors="replace")
            if len(sources) >= MAX_SOURCE_FILES:
                break
    return sources


def load_directory(root: "str | Path") -> "dict[str, str]":
    """디렉터리에서 소스를 읽는다. CLI 와 테스트용."""
    base = Path(root)
    sources: "dict[str, str]" = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or not _wanted(path.name):
            continue
        if path.stat().st_size > MAX_SOURCE_BYTES:
            continue
        sources[path.relative_to(base).as_posix()] = path.read_text(
            encoding="utf-8", errors="replace"
        )
        if len(sources) >= MAX_SOURCE_FILES:
            break
    return sources
