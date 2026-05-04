"""Embed track metadata into audio files using mutagen."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def _fetch_cover(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.read()
    except Exception as exc:
        logger.debug("Cover fetch failed: %s", exc)
        return None


def _parse_shazam_track(track_info: dict) -> dict:
    """Extract normalised fields from a Shazam track dict."""
    data = {
        "title":  track_info.get("title", ""),
        "artist": track_info.get("subtitle", ""),
        "album":  "",
        "genre":  "",
        "year":   "",
        "cover":  None,
    }
    for section in track_info.get("sections", []):
        for meta in section.get("metadata", []):
            key = meta.get("title", "").lower()
            val = meta.get("text", "")
            if key == "album":      data["album"] = val
            elif key == "released": data["year"]  = val
            elif key == "genre":    data["genre"] = val

    images   = track_info.get("images", {})
    cover_url = images.get("coverarthq") or images.get("coverart")
    if cover_url:
        data["cover"] = _fetch_cover(cover_url)

    return data


def embed_metadata(filepath: str, track_info: dict) -> None:
    """Write Shazam track metadata into *filepath* using the appropriate mutagen backend."""
    ext  = Path(filepath).suffix.lower()
    data = _parse_shazam_track(track_info)

    try:
        if ext == ".flac":
            _embed_flac(filepath, data)
        elif ext == ".mp3":
            _embed_mp3(filepath, data)
        elif ext in (".m4a", ".mp4", ".aac"):
            _embed_mp4(filepath, data)
        elif ext == ".wav":
            _embed_wav(filepath, data)
        else:
            logger.debug("No mutagen backend for extension %s; skipping metadata.", ext)
    except Exception as exc:
        logger.warning("Metadata embedding failed for %s: %s", filepath, exc)


# ── Format-specific writers ───────────────────────────────────────────────────

def _embed_flac(path: str, d: dict) -> None:
    from mutagen.flac import FLAC, Picture  # type: ignore
    audio = FLAC(path)
    if d["title"]:  audio["title"]  = d["title"]
    if d["artist"]: audio["artist"] = d["artist"]
    if d["album"]:  audio["album"]  = d["album"]
    if d["genre"]:  audio["genre"]  = d["genre"]
    if d["year"]:   audio["date"]   = d["year"]
    if d["cover"]:
        pic      = Picture()
        pic.type = 3
        pic.mime = "image/jpeg"
        pic.data = d["cover"]
        audio.clear_pictures()
        audio.add_picture(pic)
    audio.save()


def _embed_mp3(path: str, d: dict) -> None:
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, APIC  # type: ignore
    from mutagen.id3 import error as ID3Error
    try:
        audio = ID3(path)
    except ID3Error:
        audio = ID3()
    if d["title"]:  audio["TIT2"] = TIT2(encoding=3, text=d["title"])
    if d["artist"]: audio["TPE1"] = TPE1(encoding=3, text=d["artist"])
    if d["album"]:  audio["TALB"] = TALB(encoding=3, text=d["album"])
    if d["genre"]:  audio["TCON"] = TCON(encoding=3, text=d["genre"])
    if d["cover"]:
        audio["APIC"] = APIC(
            encoding=3, mime="image/jpeg", type=3, desc="Cover", data=d["cover"]
        )
    audio.save(path)


def _embed_mp4(path: str, d: dict) -> None:
    from mutagen.mp4 import MP4, MP4Cover  # type: ignore
    audio = MP4(path)
    if d["title"]:  audio["\xa9nam"] = [d["title"]]
    if d["artist"]: audio["\xa9ART"] = [d["artist"]]
    if d["album"]:  audio["\xa9alb"] = [d["album"]]
    if d["genre"]:  audio["\xa9gen"] = [d["genre"]]
    if d["year"]:   audio["\xa9day"] = [d["year"]]
    if d["cover"]:
        audio["covr"] = [MP4Cover(d["cover"], imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()


def _embed_wav(path: str, d: dict) -> None:
    from mutagen.wave import WAVE  # type: ignore
    from mutagen.id3 import TIT2, TPE1, TALB, APIC  # type: ignore
    audio = WAVE(path)
    if audio.tags is None:
        audio.add_tags()
    if d["title"]:  audio.tags["TIT2"] = TIT2(encoding=3, text=d["title"])
    if d["artist"]: audio.tags["TPE1"] = TPE1(encoding=3, text=d["artist"])
    if d["album"]:  audio.tags["TALB"] = TALB(encoding=3, text=d["album"])
    if d["cover"]:
        audio.tags["APIC"] = APIC(
            encoding=3, mime="image/jpeg", type=3, desc="Cover", data=d["cover"]
        )
    audio.save()
