"""Build the top-level argument parser with all sub-commands."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music-vault",
        description="Download Spotify playlists/tracks in lossless quality, or identify audio files.",
    )
    sub = parser.add_subparsers(dest="command")

    _add_download_parser(sub)
    _add_identify_parser(sub)

    return parser


# ── download sub-command ──────────────────────────────────────────────────────

def _add_download_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("download", help="Download a Spotify playlist or track.")

    p.add_argument("url",  help="Spotify playlist or track URL.")
    p.add_argument("-o", "--output",   default="downloads/spotify", metavar="DIR",
                   help="Output directory (default: downloads/spotify).")
    p.add_argument("-q", "--quality",  default="flac",
                   choices=["flac", "hi-res"],
                   help="Audio quality (default: flac).")
    p.add_argument("-s", "--services", nargs="+",
                   default=["qobuz", "amazon", "youtube"],
                   metavar="SVC",
                   help="Providers to try in order (default: qobuz amazon youtube).")
    p.add_argument("--lyrics",  action="store_true", default=True,
                   help="Embed lyrics when available (default: on).")
    p.add_argument("--update",  action="store_true",
                   help="Skip already-downloaded tracks and report new additions.")
    p.add_argument("--verbose", action="store_true",
                   help="Enable verbose SpotiFLAC output.")


# ── identify sub-command ──────────────────────────────────────────────────────

def _add_identify_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "identify",
        help="Identify audio file(s) via Shazam and optionally download lossless versions.",
    )

    p.add_argument("input", help="Audio file to identify.")
    p.add_argument("-o", "--output",  default="downloads/identified", metavar="DIR",
                   help="Output directory (default: downloads/identified).")
    p.add_argument("-s", "--services", nargs="+",
                   default=["qobuz", "amazon", "youtube"],
                   metavar="SVC",
                   help="Providers for --download-lossless (default: qobuz amazon youtube).")
    p.add_argument("--split",  action="store_true",
                   help="Treat input as a vinyl side: detect silence and identify each track.")
    p.add_argument("--min-silence-len", type=int, default=1500, metavar="MS",
                   help="Min silence length in ms for vinyl splitting (default: 1500).")
    p.add_argument("--silence-thresh",  type=int, default=-50,  metavar="dBFS",
                   help="Silence threshold in dBFS (default: -50).")
    p.add_argument("--min-track-len",   type=int, default=30,   metavar="SECS",
                   help="Minimum segment length in seconds to keep (default: 30).")
    p.add_argument("--download-lossless", action="store_true",
                   help="After identification search Spotify and download lossless version.")
    p.add_argument("--keep-segments", action="store_true",
                   help="Keep the extracted audio segments even when --download-lossless is set.")
    p.add_argument("--verbose", action="store_true",
                   help="Enable verbose output.")
