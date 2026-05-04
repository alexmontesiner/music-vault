"""Tests for music_vault.core.metadata."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from music_vault.core.metadata import _fetch_cover, _parse_shazam_track


# ── _fetch_cover ──────────────────────────────────────────────────────────────


class TestFetchCover:
    def test_returns_bytes_on_success(self):
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b"fake_image_data"
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = _fetch_cover("http://example.com/cover.jpg")
        assert result == b"fake_image_data"

    def test_returns_none_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
            assert _fetch_cover("http://example.com/cover.jpg") is None

    def test_returns_none_on_generic_exception(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Unexpected")):
            assert _fetch_cover("http://example.com/cover.jpg") is None


# ── _parse_shazam_track ───────────────────────────────────────────────────────


class TestParseShazamTrack:
    def test_title_extracted(self):
        result = _parse_shazam_track({"title": "Bohemian Rhapsody", "subtitle": "Queen"})
        assert result["title"] == "Bohemian Rhapsody"

    def test_artist_extracted_from_subtitle(self):
        result = _parse_shazam_track({"title": "Song", "subtitle": "The Artist"})
        assert result["artist"] == "The Artist"

    def test_empty_track_returns_defaults(self):
        result = _parse_shazam_track({})
        assert result["title"] == ""
        assert result["artist"] == ""
        assert result["album"] == ""
        assert result["genre"] == ""
        assert result["year"] == ""
        assert result["cover"] is None

    def test_album_extracted_from_sections(self):
        track = {
            "sections": [
                {"metadata": [{"title": "Album", "text": "A Night at the Opera"}]}
            ]
        }
        assert _parse_shazam_track(track)["album"] == "A Night at the Opera"

    def test_year_extracted_from_released(self):
        track = {
            "sections": [
                {"metadata": [{"title": "Released", "text": "1975"}]}
            ]
        }
        assert _parse_shazam_track(track)["year"] == "1975"

    def test_genre_extracted_from_sections(self):
        track = {
            "sections": [
                {"metadata": [{"title": "Genre", "text": "Rock"}]}
            ]
        }
        assert _parse_shazam_track(track)["genre"] == "Rock"

    def test_multiple_metadata_fields(self):
        track = {
            "title": "Song",
            "subtitle": "Artist",
            "sections": [
                {
                    "metadata": [
                        {"title": "Album", "text": "My Album"},
                        {"title": "Released", "text": "2020"},
                        {"title": "Genre", "text": "Electronic"},
                    ]
                }
            ],
        }
        result = _parse_shazam_track(track)
        assert result["album"] == "My Album"
        assert result["year"] == "2020"
        assert result["genre"] == "Electronic"

    def test_cover_fetched_from_coverarthq(self):
        track = {"images": {"coverarthq": "http://example.com/hq.jpg"}}
        with patch("music_vault.core.metadata._fetch_cover", return_value=b"hq_data"):
            result = _parse_shazam_track(track)
        assert result["cover"] == b"hq_data"

    def test_cover_falls_back_to_coverart(self):
        track = {"images": {"coverart": "http://example.com/art.jpg"}}
        with patch("music_vault.core.metadata._fetch_cover", return_value=b"art_data"):
            result = _parse_shazam_track(track)
        assert result["cover"] == b"art_data"

    def test_coverarthq_preferred_over_coverart(self):
        track = {
            "images": {
                "coverarthq": "http://example.com/hq.jpg",
                "coverart": "http://example.com/art.jpg",
            }
        }
        with patch("music_vault.core.metadata._fetch_cover", return_value=b"data") as mock_fetch:
            _parse_shazam_track(track)
        mock_fetch.assert_called_once_with("http://example.com/hq.jpg")

    def test_no_cover_url_skips_fetch(self):
        track = {"images": {}}
        with patch("music_vault.core.metadata._fetch_cover") as mock_fetch:
            result = _parse_shazam_track(track)
        mock_fetch.assert_not_called()
        assert result["cover"] is None

    def test_sections_without_metadata_key_ignored(self):
        track = {"sections": [{"other_key": "value"}]}
        result = _parse_shazam_track(track)
        assert result["album"] == ""

    def test_sections_is_case_insensitive_for_keys(self):
        # The implementation lowercases the key, so "album" matches "Album"
        track = {
            "sections": [{"metadata": [{"title": "album", "text": "Test"}]}]
        }
        assert _parse_shazam_track(track)["album"] == "Test"


# ── embed_metadata dispatch ───────────────────────────────────────────────────


class TestEmbedMetadataDispatch:
    """Ensure embed_metadata calls the right format-specific writer."""

    def _run(self, ext, mock_writer_path):
        from music_vault.core.metadata import embed_metadata

        with patch("music_vault.core.metadata._parse_shazam_track", return_value={
            "title": "T", "artist": "A", "album": "", "genre": "", "year": "", "cover": None,
        }), patch(mock_writer_path) as mock_writer:
            embed_metadata(f"file{ext}", {"title": "T", "subtitle": "A"})
            mock_writer.assert_called_once()

    def test_dispatches_to_flac_writer(self):
        self._run(".flac", "music_vault.core.metadata._embed_flac")

    def test_dispatches_to_mp3_writer(self):
        self._run(".mp3", "music_vault.core.metadata._embed_mp3")

    def test_dispatches_to_mp4_writer(self):
        self._run(".m4a", "music_vault.core.metadata._embed_mp4")

    def test_dispatches_to_wav_writer(self):
        self._run(".wav", "music_vault.core.metadata._embed_wav")

    def test_unknown_extension_does_not_raise(self):
        from music_vault.core.metadata import embed_metadata

        with patch("music_vault.core.metadata._parse_shazam_track", return_value={
            "title": "", "artist": "", "album": "", "genre": "", "year": "", "cover": None,
        }):
            embed_metadata("file.xyz", {})  # should not raise

    def test_writer_exception_is_caught(self):
        from music_vault.core.metadata import embed_metadata

        with patch("music_vault.core.metadata._parse_shazam_track", return_value={
            "title": "T", "artist": "A", "album": "", "genre": "", "year": "", "cover": None,
        }), patch("music_vault.core.metadata._embed_flac", side_effect=Exception("write error")):
            embed_metadata("file.flac", {})  # must not propagate
