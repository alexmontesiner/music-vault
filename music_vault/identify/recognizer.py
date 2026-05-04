"""Shazam-based audio recognition helpers."""

from __future__ import annotations

import asyncio
import io
import logging

logger = logging.getLogger(__name__)


def _segment_to_bytes(segment, fmt: str = "mp3", bitrate: str = "128k") -> bytes:
    """Export a pydub AudioSegment to an in-memory bytes buffer."""
    buf = io.BytesIO()
    segment.export(buf, format=fmt, bitrate=bitrate)
    return buf.getvalue()


async def _shazam_recognize(audio_bytes: bytes) -> dict | None:
    """Send *audio_bytes* to Shazam and return the ``track`` dict, or ``None``."""
    from shazamio import Shazam  # type: ignore
    shazam = Shazam()
    try:
        result = await shazam.recognize(audio_bytes)
        return result.get("track")
    except Exception as exc:
        logger.debug("Shazam error: %s", exc)
        return None


async def identify_segment_async(segment) -> dict | None:
    """Identify an audio segment by sampling three 20-second windows.

    Tries the start, first-third, and two-thirds positions to maximise
    the chance of a match (e.g. long intros on vinyl recordings).

    Returns the Shazam ``track`` dict on success, or ``None``.
    """
    duration_ms = len(segment)
    offsets = [0, duration_ms // 3, 2 * duration_ms // 3]
    for offset in offsets:
        window = segment[offset: offset + 20_000]
        if len(window) < 5_000:
            continue
        track = await _shazam_recognize(_segment_to_bytes(window))
        if track:
            return track
    return None


def identify_segment(segment) -> dict | None:
    """Synchronous wrapper around :func:`identify_segment_async`."""
    return asyncio.run(identify_segment_async(segment))


def print_track_info(track_info: dict) -> None:
    """Pretty-print a Shazam track dict to stdout."""
    title  = track_info.get("title", "?")
    artist = track_info.get("subtitle", "?")
    print(f"    Title  : {title}")
    print(f"    Artist : {artist}")
    for section in track_info.get("sections", []):
        for meta in section.get("metadata", []):
            key = meta.get("title", "")
            val = meta.get("text", "")
            if key and val:
                print(f"    {key:<8}: {val}")
    genres = track_info.get("genres", {})
    if genres.get("primary"):
        print(f"    Genre  : {genres['primary']}")
