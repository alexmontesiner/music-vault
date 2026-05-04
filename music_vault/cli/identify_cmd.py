"""identify sub-command implementation."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from music_vault.core.utils import inject_ffmpeg
from music_vault.identify.recognizer import identify_segment, print_track_info
from music_vault.identify.splitter import VinylSplitter
from music_vault.identify.processor import process_identified_track


def cmd_identify(args: Namespace) -> None:
    """Entry point for the ``identify`` sub-command."""
    inject_ffmpeg()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[!] File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    src_ext = input_path.suffix.lower() or ".mp3"

    try:
        from pydub import AudioSegment  # type: ignore
        audio = AudioSegment.from_file(str(input_path))
    except Exception as exc:
        print(f"[!] Could not load audio file: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Loaded: {input_path.name}  ({len(audio) / 1000:.1f}s)")

    if args.split:
        _identify_vinyl(args, audio, src_ext, args.output)
    else:
        _identify_single(args, audio, src_ext, args.output)


# ── Single-file identification ────────────────────────────────────────────────

def _identify_single(args: Namespace, audio, src_ext: str, output_dir: str) -> None:
    print("[~] Identifying…")
    track_info = identify_segment(audio)
    if not track_info:
        print("[!] Could not identify the audio.")
        return

    print("[+] Identified:")
    print_track_info(track_info)

    process_identified_track(
        segment=audio,
        track_info=track_info,
        output_dir=output_dir,
        src_ext=src_ext,
        download_lossless=args.download_lossless,
        services=args.services,
        keep_segments=args.keep_segments,
        verbose=args.verbose,
    )


# ── Vinyl-side identification ─────────────────────────────────────────────────

def _identify_vinyl(args: Namespace, audio, src_ext: str, output_dir: str) -> None:
    splitter = VinylSplitter(
        min_silence_len=args.min_silence_len,
        silence_thresh=args.silence_thresh,
        min_track_len=args.min_track_len,
    )
    segments = splitter.split(audio)

    results: list[tuple[str, dict | None]] = []
    for i, seg in enumerate(segments, 1):
        label = f"Track {i:02d}"
        print(f'[~] Identifying "{label}"…')
        track_info = identify_segment(seg)
        if track_info:
            print(f"[+] {label} → {track_info.get('subtitle', '?')} – {track_info.get('title', '?')}")
            if args.verbose:
                print_track_info(track_info)
        else:
            print(f"[?] {label} → unidentified")

        process_identified_track(
            segment=seg,
            track_info=track_info or {},
            output_dir=output_dir,
            src_ext=src_ext,
            download_lossless=args.download_lossless,
            services=args.services,
            keep_segments=args.keep_segments,
            verbose=args.verbose,
        ) if track_info else None

        results.append((label, track_info))

    _print_vinyl_summary(results)


def _print_vinyl_summary(results: list[tuple[str, dict | None]]) -> None:
    identified   = [(l, t) for l, t in results if t]
    unidentified = [(l, t) for l, t in results if not t]

    print("═" * 62)
    print(f"  Segments total : {len(results)}")
    print(f"  Identified     : {len(identified)}")
    if unidentified:
        print(f"  Unidentified   : {len(unidentified)}")
        for label, _ in unidentified:
            print(f"    - {label}")
    print("═" * 62)
