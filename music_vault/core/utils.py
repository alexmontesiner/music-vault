"""Shared constants and utility helpers used across the package."""

from __future__ import annotations

import re
from pathlib import Path

QUALITY_MAP: dict[str, str] = {
    "flac":   "LOSSLESS",
    "hi-res": "HI_RES",
}

AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".flac", ".wav", ".mp3", ".m4a", ".ogg", ".aiff", ".aif"}
)


def inject_ffmpeg() -> None:
    """Add the venv-bundled static ffmpeg binary to PATH.

    Uses the ``static-ffmpeg`` pip package so no system installation is needed.
    Falls back silently if the package is not present (system ffmpeg will be
    used if available).
    """
    try:
        import static_ffmpeg  # type: ignore
        static_ffmpeg.add_paths()
    except ImportError:
        pass


def safe_filename(text: str) -> str:
    """Strip characters that are illegal in file names on common OSes."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip()


def snapshot_audio_files(directory: str) -> set[Path]:
    """Return the resolved paths of all audio files found recursively under *directory*."""
    root = Path(directory)
    if not root.exists():
        return set()
    return {
        p.resolve()
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    }


def print_update_summary(new_files: set[Path], output_dir: str) -> None:
    """Print a human-readable list of files that were added during an --update run."""
    root = Path(output_dir).resolve()
    if not new_files:
        print("\n[=] No new tracks were added.")
        return
    print(f"\n[+] {len(new_files)} new track(s) added to {output_dir}:")
    for path in sorted(new_files):
        try:
            relative = path.relative_to(root)
        except ValueError:
            relative = path
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"    + {relative}  ({size_mb:.1f} MB)")
