"""Tests for music_vault.identify.spotify_search."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from music_vault.identify.spotify_search import spotify_search_track


# ── spotify_search_track ──────────────────────────────────────────────────────


class TestSpotifySearchTrack:
    def _mock_spotiflac(self, results=None, raise_exc=None):
        mock_client = MagicMock()
        if raise_exc:
            mock_client.search_tracks.side_effect = raise_exc
        else:
            mock_client.search_tracks.return_value = results or []
        mock_client_cls = MagicMock(return_value=mock_client)
        mock_metadata = MagicMock(SpotifyMetadataClient=mock_client_cls)
        mock_spotiflac = MagicMock()
        return mock_spotiflac, mock_metadata, mock_client

    def test_returns_spotify_url_on_success(self):
        expected_url = "https://open.spotify.com/track/abc123"
        results = [{"external_urls": {"spotify": expected_url}}]
        mock_spotiflac, mock_metadata, _ = self._mock_spotiflac(results=results)
        with patch.dict("sys.modules", {
            "spotiflac": mock_spotiflac,
            "spotiflac.metadata": mock_metadata,
        }):
            result = spotify_search_track("Bohemian Rhapsody", "Queen")
        assert result == expected_url

    def test_returns_none_when_no_results(self):
        mock_spotiflac, mock_metadata, _ = self._mock_spotiflac(results=[])
        with patch.dict("sys.modules", {
            "spotiflac": mock_spotiflac,
            "spotiflac.metadata": mock_metadata,
        }):
            result = spotify_search_track("Unknown Song", "Unknown Artist")
        assert result is None

    def test_returns_none_when_result_has_no_spotify_url(self):
        results = [{"external_urls": {}}]
        mock_spotiflac, mock_metadata, _ = self._mock_spotiflac(results=results)
        with patch.dict("sys.modules", {
            "spotiflac": mock_spotiflac,
            "spotiflac.metadata": mock_metadata,
        }):
            result = spotify_search_track("Song", "Artist")
        assert result is None

    def test_returns_none_on_search_exception(self):
        mock_spotiflac, mock_metadata, _ = self._mock_spotiflac(
            raise_exc=Exception("API error")
        )
        with patch.dict("sys.modules", {
            "spotiflac": mock_spotiflac,
            "spotiflac.metadata": mock_metadata,
        }):
            result = spotify_search_track("Song", "Artist")
        assert result is None

    def test_returns_none_on_import_error(self):
        # Simulate spotiflac not being installed
        with patch.dict("sys.modules", {
            "spotiflac": None,
            "spotiflac.metadata": None,
        }):
            result = spotify_search_track("Song", "Artist")
        assert result is None

    def test_search_query_includes_title_and_artist(self):
        mock_spotiflac, mock_metadata, mock_client = self._mock_spotiflac(results=[])
        with patch.dict("sys.modules", {
            "spotiflac": mock_spotiflac,
            "spotiflac.metadata": mock_metadata,
        }):
            spotify_search_track("My Song", "My Artist")
        call_args = mock_client.search_tracks.call_args
        query = call_args[0][0]
        assert "My Song" in query
        assert "My Artist" in query

    def test_search_limit_is_one(self):
        mock_spotiflac, mock_metadata, mock_client = self._mock_spotiflac(results=[])
        with patch.dict("sys.modules", {
            "spotiflac": mock_spotiflac,
            "spotiflac.metadata": mock_metadata,
        }):
            spotify_search_track("Song", "Artist")
        call_kwargs = mock_client.search_tracks.call_args[1]
        assert call_kwargs.get("limit") == 1
