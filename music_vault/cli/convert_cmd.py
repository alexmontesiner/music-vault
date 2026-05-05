"""convert sub-command implementation."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from music_vault.core.utils import (
    inject_ffmpeg,
    snapshot_audio_files,
    convert_audio_files,
    FORMAT_EXT,
)


def cmd_convert(args: Namespace) -> None:
    """Entry point for the ``convert`` sub-command."""
    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"[!] Not a directory: {args.input}", file=sys.stderr)
        sys.exit(1)

    files = snapshot_audio_files(args.input)
    if not files:
        print(f"[=] No audio files found in {args.input}")
        return

    target_ext = FORMAT_EXT.get(args.format, f".{args.format}")
    to_convert = {f for f in files if f.suffix.lower() != target_ext}

    if not to_convert:
        print(f"[=] All files are already {args.format.upper()}.")
        return

    # Resolve output directory: explicit -o, or default downloads/<format>
    output_dir = Path(args.output) if args.output else Path("downloads") / args.format

    print(f"[*] {len(to_convert)} file(s) to convert → {args.format.upper()}")
    print(f"[*] Output: {output_dir}" + ("  (originals will be deleted)" if args.delete else ""))

    if args.dry_run:
        for f in sorted(to_convert):
            print(f"    ~ {f.name}  →  {(output_dir / f.with_suffix(target_ext).name)}")
        return

    inject_ffmpeg()
    convert_audio_files(to_convert, args.format, output_dir=output_dir, delete_originals=args.delete)
    print(f"\n[+] Done.")
