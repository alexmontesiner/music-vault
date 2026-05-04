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
)


def cmd_download(args: Namespace) -> None:
    """Entry point for the ``download`` sub-command."""
    if "spotify.com" not in args.url:
        print(f"[!] Invalid Spotify URL: {args.url}", file=sys.stderr)
        sys.exit(1)

    quality = QUALITY_MAP.get(args.quality, "LOSSLESS")
    inject_ffmpeg()

    # --update: snapshot the output dir before downloading
    before: set[Path] = set()
    if args.update:
        before = snapshot_audio_files(args.output)
        print(f"[*] Update mode: found {len(before)} existing file(s) in {args.output}")

    _run_spotiflac(args, quality)

    # --update: compare snapshots and report
    if args.update:
        after     = snapshot_audio_files(args.output)
        new_files = after - before
        print_update_summary(new_files, args.output)


def _run_spotiflac(args: Namespace, quality: str) -> None:
    """Invoke SpotiFLAC and exit with a friendly message on failure."""
    from music_vault.download.spotiflac import download_url
    try:
        download_url(
            url=args.url,
            output=args.output,
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
