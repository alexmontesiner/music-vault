"""Tests for music_vault.core.utils."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from music_vault.core.utils import (
    AUDIO_EXTENSIONS,
    QUALITY_MAP,
    inject_ffmpeg,
    print_update_summary,
    safe_filename,
    snapshot_audio_files,
)


# ── Constants ─────────────────────────────────────────────────────────────────


class TestQualityMap:
    def test_flac_maps_to_lossless(self):
        assert QUALITY_MAP["flac"] == "LOSSLESS"

    def test_hi_res_maps_to_hi_res(self):
        assert QUALITY_MAP["hi-res"] == "HI_RES"

    def test_has_exactly_two_entries(self):
        assert len(QUALITY_MAP) == 2


class TestAudioExtensions:
    def test_is_frozenset(self):
        assert isinstance(AUDIO_EXTENSIONS, frozenset)

    @pytest.mark.parametrize("ext", [".flac", ".wav", ".mp3", ".m4a", ".ogg", ".aiff", ".aif"])
    def test_contains_expected_extension(self, ext):
        assert ext in AUDIO_EXTENSIONS

    def test_does_not_contain_non_audio(self):
        for ext in [".jpg", ".png", ".txt", ".pdf"]:
            assert ext not in AUDIO_EXTENSIONS


# ── safe_filename ─────────────────────────────────────────────────────────────


class TestSafeFilename:
    def test_clean_name_unchanged(self):
        assert safe_filename("Hello World") == "Hello World"

    @pytest.mark.parametrize("char", ['<', '>', ':', '"', '/', '\\', '|', '?', '*'])
    def test_illegal_char_replaced_with_underscore(self, char):
        result = safe_filename(f"A{char}B")
        assert char not in result
        assert "_" in result

    def test_leading_trailing_whitespace_stripped(self):
        assert safe_filename("  hello  ") == "hello"

    def test_control_characters_removed(self):
        result = safe_filename("Hello\x00World\x1f")
        assert "\x00" not in result
        assert "\x1f" not in result

    def test_empty_string(self):
        assert safe_filename("") == ""

    def test_normal_artist_title(self):
        result = safe_filename("Queen - Bohemian Rhapsody")
        assert result == "Queen - Bohemian Rhapsody"

    def test_colon_in_title(self):
        result = safe_filename("Title: Subtitle")
        assert ":" not in result


# ── snapshot_audio_files ──────────────────────────────────────────────────────


class TestSnapshotAudioFiles:
    def test_nonexistent_directory_returns_empty_set(self):
        assert snapshot_audio_files("/nonexistent/path/xyz_does_not_exist") == set()

    def test_empty_directory_returns_empty_set(self, tmp_path):
        assert snapshot_audio_files(str(tmp_path)) == set()

    @pytest.mark.parametrize("ext", [".flac", ".wav", ".mp3", ".m4a", ".ogg", ".aiff", ".aif"])
    def test_finds_audio_file_by_extension(self, tmp_path, ext):
        (tmp_path / f"track{ext}").touch()
        result = snapshot_audio_files(str(tmp_path))
        assert len(result) == 1

    def test_excludes_non_audio_files(self, tmp_path):
        (tmp_path / "cover.jpg").touch()
        (tmp_path / "info.txt").touch()
        result = snapshot_audio_files(str(tmp_path))
        assert result == set()

    def test_finds_nested_audio_files(self, tmp_path):
        subdir = tmp_path / "album"
        subdir.mkdir()
        (subdir / "track.flac").touch()
        result = snapshot_audio_files(str(tmp_path))
        assert len(result) == 1

    def test_returns_absolute_resolved_paths(self, tmp_path):
        (tmp_path / "track.mp3").touch()
        result = snapshot_audio_files(str(tmp_path))
        for p in result:
            assert p.is_absolute()

    def test_mixed_audio_and_non_audio(self, tmp_path):
        (tmp_path / "song.flac").touch()
        (tmp_path / "song.mp3").touch()
        (tmp_path / "cover.jpg").touch()
        result = snapshot_audio_files(str(tmp_path))
        names = {p.name for p in result}
        assert "song.flac" in names
        assert "song.mp3" in names
        assert "cover.jpg" not in names


# ── print_update_summary ──────────────────────────────────────────────────────


class TestPrintUpdateSummary:
    def test_no_new_files_prints_no_new_tracks(self, capsys):
        print_update_summary(set(), "/some/dir")
        assert "No new tracks" in capsys.readouterr().out

    def test_one_new_file_reports_count(self, tmp_path, capsys):
        f = tmp_path / "new_track.flac"
        f.write_bytes(b"x" * 1024)
        print_update_summary({f.resolve()}, str(tmp_path))
        out = capsys.readouterr().out
        assert "1 new track" in out

    def test_new_file_name_appears_in_output(self, tmp_path, capsys):
        f = tmp_path / "my_song.mp3"
        f.write_bytes(b"x" * 512)
        print_update_summary({f.resolve()}, str(tmp_path))
        assert "my_song.mp3" in capsys.readouterr().out

    def test_multiple_new_files_reports_count(self, tmp_path, capsys):
        files = set()
        for i in range(3):
            f = tmp_path / f"track{i}.flac"
            f.write_bytes(b"x" * 1024)
            files.add(f.resolve())
        print_update_summary(files, str(tmp_path))
        assert "3 new track" in capsys.readouterr().out

    def test_shows_file_size(self, tmp_path, capsys):
        f = tmp_path / "song.flac"
        f.write_bytes(b"x" * 1024 * 1024)  # 1 MB
        print_update_summary({f.resolve()}, str(tmp_path))
        out = capsys.readouterr().out
        assert "MB" in out


# ── inject_ffmpeg ─────────────────────────────────────────────────────────────


class TestInjectFfmpeg:
    def test_handles_missing_static_ffmpeg_gracefully(self):
        with patch.dict("sys.modules", {"static_ffmpeg": None}):
            inject_ffmpeg()  # must not raise

    def test_calls_add_paths_when_package_available(self):
        mock_module = MagicMock()
        with patch.dict("sys.modules", {"static_ffmpeg": mock_module}):
            inject_ffmpeg()
        mock_module.add_paths.assert_called_once()
