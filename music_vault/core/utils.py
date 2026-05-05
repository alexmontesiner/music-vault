"""Shared constants and utility helpers used across the package."""

from __future__ import annotations

import re
import subprocess
import sys
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


# Format extension map used by convert_audio_files and the convert sub-command
FORMAT_EXT: dict[str, str] = {
    "flac": ".flac",
    "aiff": ".aiff",
    "wav":  ".wav",
    "mp3":  ".mp3",
    "alac": ".m4a",
}


def convert_audio_files(
    files: set[Path],
    target_format: str,
    output_dir: Path | None = None,
    delete_originals: bool = False,
) -> set[Path]:
    """Convert *files* to *target_format* with ffmpeg.

    *output_dir*: directory to write converted files into. If ``None`` the
    converted file is placed next to the source. The directory is created if
    it does not exist.

    *delete_originals*: remove the source file after a successful conversion.
    Files whose extension already matches *target_format* are copied (or left
    in place when *output_dir* is ``None``) without re-encoding.

    Returns the set of output file paths. Conversion failures are reported to
    stderr but do not abort the loop.
    """
    target_ext = FORMAT_EXT.get(target_format, f".{target_format}")
    converted: set[Path] = set()

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    for src in sorted(files):
        dst = (output_dir / src.with_suffix(target_ext).name) if output_dir else src.with_suffix(target_ext)

        if src.suffix.lower() == target_ext and output_dir is None:
            converted.add(src)
            continue

        try:
            subprocess.run(
                ["ffmpeg", "-i", str(src), "-y", str(dst)],
                check=True,
                capture_output=True,
            )
            if delete_originals and dst.resolve() != src.resolve():
                src.unlink()
            converted.add(dst)
            print(f"    [→] {src.name} → {dst}")
        except subprocess.CalledProcessError as exc:
            print(
                f"    [!] Conversion failed for {src.name}: "
                f"{exc.stderr.decode(errors='replace').strip()}",
                file=sys.stderr,
            )

    return converted
