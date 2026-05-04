"""Spotify search integration for identified tracks, and lossless download trigger."""

from __future__ import annotations

import io
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def spotify_search_track(title: str, artist: str) -> str | None:
    """Search Spotify for a track by title and artist using SpotiFLAC's internal client.

    Returns the Spotify track URL on success, or ``None`` if nothing was found.
    """
    try:
        from spotiflac.metadata import SpotifyMetadataClient  # type: ignore
        client = SpotifyMetadataClient()
        results = client.search_tracks(f"{title} {artist}", limit=1)
        if results:
            return results[0].get("external_urls", {}).get("spotify")
    except Exception as exc:
        logger.debug("Spotify search failed: %s", exc)
    return None


def process_identified_track(
    *,
    segment,
    track_info: dict,
    label: str,
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
    3. If ``download_lossless`` is True, search Spotify and trigger a SpotiFLAC
       download that will overwrite/supplement the saved segment.
    4. Remove the saved segment if ``download_lossless`` succeeded and
       ``keep_segments`` is False.
    """
    from music_vault.core.utils import safe_filename, inject_ffmpeg
    from music_vault.identify.metadata import embed_metadata

    title  = track_info.get("title",    "Unknown Title")
    artist = track_info.get("subtitle", "Unknown Artist")

    filename   = safe_filename(f"{artist} - {title}") + src_ext
    out_path   = Path(output_dir) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Export segment
    fmt = src_ext.lstrip(".")
    segment.export(str(out_path), format=fmt)
    print(f"    Saved: {out_path.name}")

    # Embed metadata
    embed_metadata(str(out_path), track_info)

    if download_lossless:
        _download_lossless(
            track_info=track_info,
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
    track_info: dict,
    title: str,
    artist: str,
    output_dir: str,
    segment_path: Path,
    services: list[str],
    keep_segments: bool,
    verbose: bool,
) -> None:
    from music_vault.core.utils import inject_ffmpeg

    spotify_url = spotify_search_track(title, artist)
    if not spotify_url:
        print(f"    [!] Could not find '{title}' on Spotify — keeping segment file.")
        return

    print(f"    Downloading lossless: {spotify_url}")
    inject_ffmpeg()
    try:
        from spotiflac import SpotiFLAC  # type: ignore
        SpotiFLAC(
            url=spotify_url,
            output=output_dir,
            services=services,
            quality="LOSSLESS",
            lyrics=True,
            verbose=verbose,
        ).download()
        if not keep_segments:
            try:
                segment_path.unlink()
            except OSError:
                pass
    except Exception as exc:
        print(f"    [!] Lossless download failed: {exc}", file=sys.stderr)
