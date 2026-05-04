"""Post-identification processing: export segment, embed metadata, optionally download lossless."""

from __future__ import annotations

import sys
from pathlib import Path

from music_vault.core.metadata import embed_metadata
from music_vault.core.utils import inject_ffmpeg, safe_filename
from music_vault.download.spotiflac import download_url
from music_vault.identify.spotify_search import spotify_search_track


def process_identified_track(
    *,
    segment,
    track_info: dict,
    output_dir: str,
    src_ext: str,
    download_lossless: bool,
    services: list[str],
    keep_segments: bool,
    verbose: bool,
) -> None:
    """Save the identified audio segment and optionally download the lossless master.

    Steps:
    1. Export the pydub segment to *output_dir* using *src_ext* as the format.
    2. Embed Shazam metadata into the saved file.
    3. If ``download_lossless`` is True, search Spotify and trigger a download.
    4. Remove the saved segment if the lossless download succeeded and
       ``keep_segments`` is False.
    """
    title  = track_info.get("title",    "Unknown Title")
    artist = track_info.get("subtitle", "Unknown Artist")

    filename = safe_filename(f"{artist} - {title}") + src_ext
    out_path = Path(output_dir) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = src_ext.lstrip(".")
    segment.export(str(out_path), format=fmt)
    print(f"    Saved: {out_path.name}")

    embed_metadata(str(out_path), track_info)

    if download_lossless:
        _download_lossless(
            title=title,
            artist=artist,
            output_dir=output_dir,
            segment_path=out_path,
            services=services,
            keep_segments=keep_segments,
            verbose=verbose,
        )


def _download_lossless(
    *,
    title: str,
    artist: str,
    output_dir: str,
    segment_path: Path,
    services: list[str],
    keep_segments: bool,
    verbose: bool,
) -> None:
    spotify_url = spotify_search_track(title, artist)
    if not spotify_url:
        print(f"    [!] Could not find '{title}' on Spotify — keeping segment file.")
        return

    print(f"    Downloading lossless: {spotify_url}")
    inject_ffmpeg()
    try:
        download_url(
            url=spotify_url,
            output=output_dir,
            services=services,
            quality="LOSSLESS",
            lyrics=True,
            verbose=verbose,
        )
        if not keep_segments:
            try:
                segment_path.unlink()
            except OSError:
                pass
    except Exception as exc:
        print(f"    [!] Lossless download failed: {exc}", file=sys.stderr)
