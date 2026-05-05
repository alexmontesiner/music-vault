"""Auto-fix safe issues on Track objects."""

from __future__ import annotations

import logging
import unicodedata

from music_vault.core.utils import safe_filename
from music_vault.library.scanner import Track

logger = logging.getLogger(__name__)

_TAG_ISSUES: frozenset[str] = frozenset({
    "missing_title", "missing_artist", "missing_album",
    "missing_year", "missing_genre", "missing_cover",
})


def fix_library(
    tracks: list[Track],
    dry_run: bool = False,
) -> list[tuple[Track, str]] | None:
    """Apply all safe auto-fixes to *tracks*.

    Returns ``None`` when there are no fixable tracks (nothing to do).
    Returns a list of ``(track, description)`` pairs for every action taken
    (or that would be taken in dry-run mode); the list may be empty if all
    Shazam identification attempts failed.
    """
    fixable = [
        t for t in tracks
        if any(i in t.issues for i in _TAG_ISSUES) or "filename_mismatch" in t.issues
    ]
    if not fixable:
        return None
    total = len(fixable)
    actions: list[tuple[Track, str]] = []
    for idx, track in enumerate(fixable, 1):
        print(f"[{idx}/{total}] {track.path.name}", flush=True)
        for description in _fix_track(track, dry_run=dry_run):
            actions.append((track, description))
    return actions


def _fix_track(track: Track, dry_run: bool = False) -> list[str]:
    actions: list[str] = []

    # 1. Fix missing tags via Shazam identification
    if any(issue in track.issues for issue in _TAG_ISSUES):
        action = _fix_missing_tags(track, dry_run=dry_run)
        if action:
            actions.append(action)
            # After real identification re-evaluate filename: tags now exist
            if not dry_run and track.title and track.artist:
                expected = safe_filename(f"{track.title} - {track.artist}")
                if track.path.stem != expected and "filename_mismatch" not in track.issues:
                    track.issues.append("filename_mismatch")

    # 2. Fix filename mismatch (may have been there before, or just added above)
    if "filename_mismatch" in track.issues:
        action = _fix_filename(track, dry_run=dry_run)
        if action:
            actions.append(action)

    return actions


def _fix_missing_tags(track: Track, dry_run: bool = False) -> str | None:
    """Identify *track* via Shazam and embed the returned metadata."""
    if dry_run:
        return f"identify  {track.path.name}  (Shazam — run without --dry-run to apply)"

    from music_vault.core.utils import inject_ffmpeg
    inject_ffmpeg()

    try:
        from pydub import AudioSegment  # type: ignore
        segment = AudioSegment.from_file(str(track.path))
    except Exception as exc:
        logger.debug("Could not load %s for identification: %s", track.path.name, exc)
        return None

    from music_vault.identify.recognizer import identify_segment
    track_info = identify_segment(segment)
    if not track_info:
        print(f"    [?] Shazam: no match found for {track.path.name}", flush=True)
        return None

    from music_vault.core.metadata import embed_metadata, _parse_shazam_track
    embed_metadata(str(track.path), track_info)

    parsed = _parse_shazam_track(track_info)
    if parsed["title"]:  track.title  = parsed["title"]
    if parsed["artist"]: track.artist = parsed["artist"]
    if parsed["album"]:  track.album  = parsed["album"]
    if parsed["year"]:   track.year   = parsed["year"]
    if parsed["genre"]:  track.genre  = parsed["genre"]
    if parsed["cover"]:  track.has_cover = True

    track.issues = [i for i in track.issues if i not in _TAG_ISSUES]

    return f"identified  {track.path.name}  →  {track.title} - {track.artist}"


def _fix_filename(track: Track, dry_run: bool = False) -> str | None:
    """Rename the file so its stem matches ``{title} - {artist}``."""
    new_name = safe_filename(f"{track.title} - {track.artist}") + track.path.suffix
    new_path = track.path.parent / new_name
    # Normalize both sides to NFC before comparing: macOS APFS/HFS+ stores
    # filenames in NFD (decomposed Unicode), so characters like ñ, é, ü will
    # differ from the NFC string produced by safe_filename even though they
    # look identical when printed.
    if unicodedata.normalize("NFC", str(new_path)) == unicodedata.normalize("NFC", str(track.path)):
        return None
    description = f"rename  {track.path.name}  →  {new_name}"
    if not dry_run:
        track.path = track.path.rename(new_path)
        track.issues.remove("filename_mismatch")
    return description
