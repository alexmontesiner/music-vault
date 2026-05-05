"""library sub-command implementation."""

from __future__ import annotations

from argparse import Namespace

from music_vault.library.scanner import scan_library
from music_vault.library.health import check_all
from music_vault.library.fixer import fix_library
from music_vault.library.report import print_report


def cmd_library(args: Namespace) -> None:
    """Entry point for the ``library`` sub-command."""
    print(f"[*] Scanning {args.path} …", flush=True)
    tracks = scan_library(args.path)
    print(f"[*] Found {len(tracks)} track(s). Running health checks …", flush=True)
    check_all(tracks)
    print_report(tracks)

    if args.fix or args.dry_run:
        actions = fix_library(tracks, dry_run=args.dry_run)
        if actions is None:
            print("[=] Nothing to fix.")
            return
        prefix = "[DRY RUN]" if args.dry_run else "[FIX]"
        for _track, description in actions:
            print(f"  {prefix} {description}")
