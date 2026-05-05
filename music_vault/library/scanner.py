"""Walk a local music library and build a list of Track objects."""

from __future__ import annotations

import mutagen  # type: ignore
from dataclasses import dataclass, field
from pathlib import Path

from music_vault.core.utils import AUDIO_EXTENSIONS


@dataclass
class Track:
    path: Path
    title: str = ""
    artist: str = ""
    album: str = ""
    year: str = ""
    genre: str = ""
    has_cover: bool = False
    format: str = ""           # extension without dot: "flac", "mp3", …
    duration_sec: float = 0.0
    issues: list[str] = field(default_factory=list)


def scan_library(root: str | Path) -> list[Track]:
    """Walk *root* recursively and return one Track per audio file found."""
    root = Path(root)
    if not root.exists():
        return []
    tracks = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            tags = _read_tags(path)
            tracks.append(Track(
                path=path,
                format=path.suffix.lower().lstrip("."),
                **tags,
            ))
    return tracks


# ── Metadata reading ──────────────────────────────────────────────────────────


def _read_tags(path: Path) -> dict:
    """Read title, artist, album, year, genre, has_cover, duration_sec from *path*."""
    data: dict = {
        "title": "", "artist": "", "album": "",
        "year": "", "genre": "", "has_cover": False, "duration_sec": 0.0,
    }
    try:
        # Non-easy instance: duration and cover-art detection
        f = mutagen.File(str(path))
        if f is None:
            return data
        if hasattr(f, "info") and hasattr(f.info, "length"):
            data["duration_sec"] = round(f.info.length, 1)
        data["has_cover"] = _detect_cover(f)

        # Easy instance: normalised text tags across all formats
        ef = mutagen.File(str(path), easy=True)
        if ef is not None and ef.tags is not None:
            data["title"]  = (ef.tags.get("title")  or [""])[0]
            data["artist"] = (ef.tags.get("artist") or [""])[0]
            data["album"]  = (ef.tags.get("album")  or [""])[0]
            data["year"]   = (ef.tags.get("date")   or [""])[0]
            data["genre"]  = (ef.tags.get("genre")  or [""])[0]
    except Exception:
        pass
    return data


def _detect_cover(f) -> bool:
    """Return True if *f* (a mutagen file object) has embedded cover art."""
    try:
        if hasattr(f, "pictures"):          # FLAC
            return bool(f.pictures)
        tags = getattr(f, "tags", None)
        if tags is None:
            return False
        if "covr" in tags:                  # MP4
            return True
        return any(k.startswith("APIC") for k in tags.keys())  # ID3 (MP3 / WAV)
    except Exception:
        return False
