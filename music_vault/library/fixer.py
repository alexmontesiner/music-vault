"""Auto-fix safe issues on Track objects."""

from __future__ import annotations

from pathlib import Path

from music_vault.core.utils import safe_filename
from music_vault.library.scanner import Track


def fix_library(
    tracks: list[Track],
    dry_run: bool = False,
) -> list[tuple[Track, str]]:
    """Apply all safe auto-fixes to *tracks*.

    Returns a list of ``(track, description)`` pairs for every action taken
    (or that would be taken in dry-run mode).
    """
    actions: list[tuple[Track, str]] = []
    for track in tracks:
        for description in _fix_track(track, dry_run=dry_run):
            actions.append((track, description))
    return actions


def _fix_track(track: Track, dry_run: bool = False) -> list[str]:
    actions: list[str] = []
    if "filename_mismatch" in track.issues:
        action = _fix_filename(track, dry_run=dry_run)
        if action:
            actions.append(action)
    return actions


def _fix_filename(track: Track, dry_run: bool = False) -> str | None:
    """Rename the file so its stem matches ``{artist} - {title}``."""
    new_name = safe_filename(f"{track.artist} - {track.title}") + track.path.suffix
    new_path = track.path.parent / new_name
    if new_path == track.path:
        return None
    description = f"rename  {track.path.name}  →  {new_name}"
    if not dry_run:
        track.path = track.path.rename(new_path)
        track.issues.remove("filename_mismatch")
    return description
