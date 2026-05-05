"""Tests for music_vault.library.scanner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from music_vault.library.scanner import Track, _detect_cover, _read_tags, scan_library


# ── scan_library ──────────────────────────────────────────────────────────────


class TestScanLibrary:
    def test_nonexistent_directory_returns_empty(self):
        assert scan_library("/nonexistent/path/xyz") == []

    def test_empty_directory_returns_empty(self, tmp_path):
        assert scan_library(tmp_path) == []

    def test_non_audio_files_ignored(self, tmp_path):
        (tmp_path / "cover.jpg").touch()
        (tmp_path / "info.txt").touch()
        with patch("music_vault.library.scanner._read_tags", return_value={
            "title": "", "artist": "", "album": "", "year": "",
            "genre": "", "has_cover": False, "duration_sec": 0.0,
        }):
            result = scan_library(tmp_path)
        assert result == []

    @pytest.mark.parametrize("ext", [".flac", ".mp3", ".wav", ".m4a", ".ogg", ".aiff", ".aif"])
    def test_audio_file_creates_track(self, tmp_path, ext):
        (tmp_path / f"song{ext}").touch()
        with patch("music_vault.library.scanner._read_tags", return_value={
            "title": "Song", "artist": "Artist", "album": "Album",
            "year": "2020", "genre": "Rock", "has_cover": True, "duration_sec": 180.0,
        }):
            result = scan_library(tmp_path)
        assert len(result) == 1
        assert isinstance(result[0], Track)

    def test_track_format_set_from_extension(self, tmp_path):
        (tmp_path / "song.flac").touch()
        with patch("music_vault.library.scanner._read_tags", return_value={
            "title": "", "artist": "", "album": "", "year": "",
            "genre": "", "has_cover": False, "duration_sec": 0.0,
        }):
            result = scan_library(tmp_path)
        assert result[0].format == "flac"

    def test_track_path_is_set(self, tmp_path):
        f = tmp_path / "song.mp3"
        f.touch()
        with patch("music_vault.library.scanner._read_tags", return_value={
            "title": "", "artist": "", "album": "", "year": "",
            "genre": "", "has_cover": False, "duration_sec": 0.0,
        }):
            result = scan_library(tmp_path)
        assert result[0].path == f

    def test_recursive_scan(self, tmp_path):
        sub = tmp_path / "artist" / "album"
        sub.mkdir(parents=True)
        (sub / "track.flac").touch()
        with patch("music_vault.library.scanner._read_tags", return_value={
            "title": "", "artist": "", "album": "", "year": "",
            "genre": "", "has_cover": False, "duration_sec": 0.0,
        }):
            result = scan_library(tmp_path)
        assert len(result) == 1

    def test_multiple_files_sorted(self, tmp_path):
        for name in ["c.mp3", "a.mp3", "b.mp3"]:
            (tmp_path / name).touch()
        with patch("music_vault.library.scanner._read_tags", return_value={
            "title": "", "artist": "", "album": "", "year": "",
            "genre": "", "has_cover": False, "duration_sec": 0.0,
        }):
            result = scan_library(tmp_path)
        names = [t.path.name for t in result]
        assert names == sorted(names)

    def test_issues_starts_empty(self, tmp_path):
        (tmp_path / "song.flac").touch()
        with patch("music_vault.library.scanner._read_tags", return_value={
            "title": "", "artist": "", "album": "", "year": "",
            "genre": "", "has_cover": False, "duration_sec": 0.0,
        }):
            result = scan_library(tmp_path)
        assert result[0].issues == []


# ── _read_tags ────────────────────────────────────────────────────────────────


def _make_mutagen_mock(
    length=180.0,
    pictures=None,
    tags=None,
    easy_tags=None,
):
    """Build (full_mock, easy_mock) pair for mutagen.File side_effect."""
    full = MagicMock()
    full.info.length = length
    full.pictures = pictures or []
    full.tags = tags or {}

    easy = MagicMock()
    easy.tags = easy_tags

    def side_effect(path, **kwargs):
        return easy if kwargs.get("easy") else full

    return full, easy, side_effect


class TestReadTags:
    def test_mutagen_returns_none_gives_defaults(self, tmp_path):
        f = tmp_path / "song.flac"
        f.touch()
        with patch("music_vault.library.scanner.mutagen") as m:
            m.File.return_value = None
            result = _read_tags(f)
        assert result["title"] == ""
        assert result["duration_sec"] == 0.0
        assert result["has_cover"] is False

    def test_duration_extracted(self, tmp_path):
        f = tmp_path / "song.flac"
        f.touch()
        _, _, side_effect = _make_mutagen_mock(length=240.0, easy_tags=None)
        with patch("music_vault.library.scanner.mutagen") as m:
            m.File.side_effect = side_effect
            result = _read_tags(f)
        assert result["duration_sec"] == 240.0

    def test_title_extracted_from_easy_tags(self, tmp_path):
        f = tmp_path / "song.mp3"
        f.touch()
        easy_tags = {"title": ["My Song"], "artist": ["My Artist"],
                     "album": ["My Album"], "date": ["2020"], "genre": ["Rock"]}
        _, _, side_effect = _make_mutagen_mock(easy_tags=easy_tags)
        with patch("music_vault.library.scanner.mutagen") as m:
            m.File.side_effect = side_effect
            result = _read_tags(f)
        assert result["title"]  == "My Song"
        assert result["artist"] == "My Artist"
        assert result["album"]  == "My Album"
        assert result["year"]   == "2020"
        assert result["genre"]  == "Rock"

    def test_empty_easy_tags_give_empty_strings(self, tmp_path):
        f = tmp_path / "song.flac"
        f.touch()
        _, _, side_effect = _make_mutagen_mock(easy_tags={})
        with patch("music_vault.library.scanner.mutagen") as m:
            m.File.side_effect = side_effect
            result = _read_tags(f)
        assert result["title"] == ""

    def test_no_easy_tags_object_gives_defaults(self, tmp_path):
        f = tmp_path / "song.flac"
        f.touch()
        full = MagicMock()
        full.info.length = 120.0
        full.pictures = []
        full.tags = {}

        easy = MagicMock()
        easy.tags = None  # no tags

        with patch("music_vault.library.scanner.mutagen") as m:
            m.File.side_effect = lambda path, **kwargs: easy if kwargs.get("easy") else full
            result = _read_tags(f)
        assert result["title"] == ""

    def test_exception_returns_defaults(self, tmp_path):
        f = tmp_path / "song.mp3"
        f.touch()
        with patch("music_vault.library.scanner.mutagen") as m:
            m.File.side_effect = Exception("corrupt")
            result = _read_tags(f)
        assert result["title"] == ""
        assert result["duration_sec"] == 0.0


# ── _detect_cover ─────────────────────────────────────────────────────────────


class TestDetectCover:
    def test_flac_with_pictures_returns_true(self):
        mock_file = MagicMock(spec=["pictures", "tags"])
        mock_file.pictures = [MagicMock()]
        assert _detect_cover(mock_file) is True

    def test_flac_empty_pictures_returns_false(self):
        mock_file = MagicMock(spec=["pictures", "tags"])
        mock_file.pictures = []
        assert _detect_cover(mock_file) is False

    def test_mp4_with_covr_returns_true(self):
        mock_file = MagicMock(spec=["tags"])
        mock_file.tags = {"covr": [b"data"]}
        assert _detect_cover(mock_file) is True

    def test_mp4_without_covr_returns_false(self):
        mock_file = MagicMock(spec=["tags"])
        mock_file.tags = {"\xa9nam": ["Song"]}
        assert _detect_cover(mock_file) is False

    def test_id3_with_apic_returns_true(self):
        mock_file = MagicMock(spec=["tags"])
        mock_file.tags = {"APIC:": MagicMock(), "TIT2": MagicMock()}
        assert _detect_cover(mock_file) is True

    def test_id3_without_apic_returns_false(self):
        mock_file = MagicMock(spec=["tags"])
        mock_file.tags = {"TIT2": MagicMock(), "TPE1": MagicMock()}
        assert _detect_cover(mock_file) is False

    def test_none_tags_returns_false(self):
        mock_file = MagicMock(spec=["tags"])
        mock_file.tags = None
        assert _detect_cover(mock_file) is False

    def test_exception_returns_false(self):
        mock_file = MagicMock()
        mock_file.pictures = MagicMock(side_effect=Exception("boom"))
        # should not raise
        result = _detect_cover(mock_file)
        assert isinstance(result, bool)
