"""Health checks for Track objects."""

from __future__ import annotations

from collections import defaultdict

from music_vault.core.utils import safe_filename
from music_vault.library.scanner import Track

LOSSLESS_FORMATS: frozenset[str] = frozenset({"flac", "wav", "aiff", "aif"})
LOSSY_FORMATS:    frozenset[str] = frozenset({"mp3", "m4a", "ogg"})


def check_all(tracks: list[Track]) -> None:
    """Run all health checks on *tracks*, mutating each ``Track.issues`` in-place."""
    for track in tracks:
        track.issues = _check_single(track)
    _flag_duplicates(tracks)
    _flag_lossy_redundant(tracks)


# ── Per-track checks ──────────────────────────────────────────────────────────


def _check_single(track: Track) -> list[str]:
    issues: list[str] = []
    if not track.title:      issues.append("missing_title")
    if not track.artist:     issues.append("missing_artist")
    if not track.album:      issues.append("missing_album")
    if not track.year:       issues.append("missing_year")
    if not track.genre:      issues.append("missing_genre")
    if not track.has_cover:  issues.append("missing_cover")
    if track.title and track.artist:
        expected = safe_filename(f"{track.title} - {track.artist}")
        if track.path.stem != expected:
            issues.append("filename_mismatch")
    return issues


# ── Cross-track checks ────────────────────────────────────────────────────────


def _flag_duplicates(tracks: list[Track]) -> None:
    """Add ``duplicate`` to any track that shares artist + title with another."""
    groups: dict[tuple[str, str], list[Track]] = defaultdict(list)
    for t in tracks:
        if t.title and t.artist:
            groups[(t.artist.lower(), t.title.lower())].append(t)
    for group in groups.values():
        if len(group) > 1:
            for t in group:
                if "duplicate" not in t.issues:
                    t.issues.append("duplicate")


def _flag_lossy_redundant(tracks: list[Track]) -> None:
    """Flag lossy tracks when a lossless version of the same track also exists."""
    groups: dict[tuple[str, str], list[Track]] = defaultdict(list)
    for t in tracks:
        if t.title and t.artist:
            groups[(t.artist.lower(), t.title.lower())].append(t)
    for group in groups.values():
        if any(t.format in LOSSLESS_FORMATS for t in group):
            for t in group:
                if t.format in LOSSY_FORMATS and "lossy_redundant" not in t.issues:
                    t.issues.append("lossy_redundant")
