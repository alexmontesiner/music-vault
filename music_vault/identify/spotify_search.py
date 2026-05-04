"""Spotify search integration for identified tracks."""

from __future__ import annotations

import logging

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

