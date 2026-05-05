"""download sub-command implementation."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from music_vault.core.utils import (
    QUALITY_MAP,
    inject_ffmpeg,
    snapshot_audio_files,
    print_update_summary,
    convert_audio_files,
)


def cmd_download(args: Namespace) -> None:
    """Entry point for the ``download`` sub-command."""
    if "spotify.com" not in args.url:
        print(f"[!] Invalid Spotify URL: {args.url}", file=sys.stderr)
        sys.exit(1)

    quality = QUALITY_MAP.get(args.quality, "LOSSLESS")
    inject_ffmpeg()

    target_format = getattr(args, "format", "flac")
    needs_conversion = target_format != "flac"

    # Append a format subfolder so different formats stay separated,
    # e.g. downloads/spotify/aiff or downloads/spotify/flac.
    output = str(Path(args.output) / target_format)

    # Snapshot before downloading so we can identify new files for conversion
    # and/or --update reporting.
    before: set[Path] = set()
    if args.update or needs_conversion:
        before = snapshot_audio_files(output)
        if args.update:
            print(f"[*] Update mode: found {len(before)} existing file(s) in {output}")

    _run_spotiflac(args, quality, output)

    if args.update or needs_conversion:
        after     = snapshot_audio_files(output)
        new_files = after - before

        if needs_conversion and new_files:
            print(f"[*] Converting {len(new_files)} file(s) to {target_format.upper()}...")
            new_files = convert_audio_files(new_files, target_format)

        if args.update:
            print_update_summary(new_files, output)


def _run_spotiflac(args: Namespace, quality: str, output: str) -> None:
    """Invoke SpotiFLAC and exit with a friendly message on failure."""
    from music_vault.download.spotiflac import download_url
    try:
        download_url(
            url=args.url,
            output=output,
            services=args.services,
            quality=quality,
            lyrics=args.lyrics,
            verbose=args.verbose,
        )
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        print(f"[!] Download failed: {exc}", file=sys.stderr)
        sys.exit(1)
