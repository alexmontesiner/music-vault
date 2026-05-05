"""Tests for music_vault.library.fixer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from music_vault.library.fixer import _fix_filename, _fix_missing_tags, fix_library
from music_vault.library.scanner import Track


def _track(name: str, title: str, artist: str, issues: list[str] | None = None) -> Track:
    return Track(
        path=Path(f"/lib/{name}"),
        title=title,
        artist=artist,
        issues=issues or [],
    )


# ── _fix_filename ─────────────────────────────────────────────────────────────


class TestFixFilename:
    def test_dry_run_returns_description_without_renaming(self, tmp_path):
        f = tmp_path / "wrong_name.mp3"
        f.touch()
        track = Track(path=f, title="My Song", artist="My Artist",
                      issues=["filename_mismatch"])
        description = _fix_filename(track, dry_run=True)
        assert description is not None
        assert "rename" in description
        assert f.exists()  # not renamed

    def test_dry_run_does_not_modify_issues(self, tmp_path):
        f = tmp_path / "wrong_name.mp3"
        f.touch()
        track = Track(path=f, title="My Song", artist="My Artist",
                      issues=["filename_mismatch"])
        _fix_filename(track, dry_run=True)
        assert "filename_mismatch" in track.issues

    def test_fix_renames_file(self, tmp_path):
        f = tmp_path / "wrong_name.mp3"
        f.touch()
        track = Track(path=f, title="My Song", artist="My Artist",
                      issues=["filename_mismatch"])
        _fix_filename(track, dry_run=False)
        assert (tmp_path / "My Song - My Artist.mp3").exists()
        assert not f.exists()

    def test_fix_updates_track_path(self, tmp_path):
        f = tmp_path / "wrong_name.mp3"
        f.touch()
        track = Track(path=f, title="My Song", artist="My Artist",
                      issues=["filename_mismatch"])
        _fix_filename(track, dry_run=False)
        assert track.path.name == "My Song - My Artist.mp3"

    def test_fix_removes_issue_from_track(self, tmp_path):
        f = tmp_path / "wrong_name.mp3"
        f.touch()
        track = Track(path=f, title="My Song", artist="My Artist",
                      issues=["filename_mismatch"])
        _fix_filename(track, dry_run=False)
        assert "filename_mismatch" not in track.issues

    def test_already_correct_name_returns_none(self, tmp_path):
        f = tmp_path / "My Song - My Artist.mp3"
        f.touch()
        track = Track(path=f, title="My Song", artist="My Artist",
                      issues=["filename_mismatch"])
        assert _fix_filename(track, dry_run=False) is None

    def test_description_shows_old_and_new_names(self, tmp_path):
        f = tmp_path / "old.flac"
        f.touch()
        track = Track(path=f, title="Song", artist="Artist",
                      issues=["filename_mismatch"])
        desc = _fix_filename(track, dry_run=True)
        assert "old.flac" in desc
        assert "Song - Artist.flac" in desc

    def test_illegal_chars_in_title_sanitized(self, tmp_path):
        f = tmp_path / "old.mp3"
        f.touch()
        track = Track(path=f, title="Song: The Remix", artist="Artist",
                      issues=["filename_mismatch"])
        _fix_filename(track, dry_run=False)
        # The colon should be replaced by safe_filename
        assert ":" not in track.path.name


# ── fix_library ───────────────────────────────────────────────────────────────


class TestFixLibrary:
    def test_no_issues_returns_empty_list(self, tmp_path):
        track = Track(path=tmp_path / "Song - Artist.flac",
                      title="Song", artist="Artist", issues=[])
        result = fix_library([track])
        assert result == []

    def test_returns_actions_for_fixable_tracks(self, tmp_path):
        f = tmp_path / "wrong.mp3"
        f.touch()
        track = Track(path=f, title="Song", artist="Artist",
                      issues=["filename_mismatch"])
        result = fix_library([track], dry_run=True)
        assert len(result) == 1

    def test_action_tuple_contains_track_and_description(self, tmp_path):
        f = tmp_path / "wrong.mp3"
        f.touch()
        track = Track(path=f, title="Song", artist="Artist",
                      issues=["filename_mismatch"])
        result = fix_library([track], dry_run=True)
        returned_track, description = result[0]
        assert returned_track is track
        assert isinstance(description, str)

    def test_non_fixable_issues_not_actioned(self, tmp_path):
        # duplicate and lossy_redundant are not auto-fixable
        track = Track(path=tmp_path / "Song - Artist.flac",
                      title="Song", artist="Artist",
                      issues=["duplicate", "lossy_redundant"])
        result = fix_library([track])
        assert result == []

    def test_multiple_tracks_processed(self, tmp_path):
        f1 = tmp_path / "wrong1.mp3"
        f2 = tmp_path / "wrong2.mp3"
        f1.touch()
        f2.touch()
        tracks = [
            Track(path=f1, title="Song 1", artist="Artist",
                  issues=["filename_mismatch"]),
            Track(path=f2, title="Song 2", artist="Artist",
                  issues=["filename_mismatch"]),
        ]
        result = fix_library(tracks, dry_run=True)
        assert len(result) == 2

    def test_dry_run_does_not_rename_files(self, tmp_path):
        f = tmp_path / "wrong.flac"
        f.touch()
        track = Track(path=f, title="Song", artist="Artist",
                      issues=["filename_mismatch"])
        fix_library([track], dry_run=True)
        assert f.exists()

    def test_non_dry_run_renames_files(self, tmp_path):
        f = tmp_path / "wrong.flac"
        f.touch()
        track = Track(path=f, title="Song", artist="Artist",
                      issues=["filename_mismatch"])
        fix_library([track], dry_run=False)
        assert (tmp_path / "Song - Artist.flac").exists()


# ── _fix_missing_tags ─────────────────────────────────────────────────────────

_SHAZAM_TRACK = {
    "title": "Acid Tracks",
    "subtitle": "Phuture",
    "sections": [{"metadata": [
        {"title": "Album", "text": "Trax Classics"},
        {"title": "Released", "text": "1987"},
        {"title": "Genre", "text": "Electronic"},
    ]}],
    "images": {},
}

_PARSED = {
    "title": "Acid Tracks", "artist": "Phuture",
    "album": "Trax Classics", "year": "1987", "genre": "Electronic", "cover": None,
}


class TestFixMissingTags:
    def test_dry_run_returns_description_without_loading(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title", "missing_artist"])
        with patch("pydub.AudioSegment.from_file") as mock_load:
            result = _fix_missing_tags(track, dry_run=True)
        mock_load.assert_not_called()
        assert result is not None
        assert "identify" in result

    def test_dry_run_does_not_modify_track(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title"])
        _fix_missing_tags(track, dry_run=True)
        assert track.title == ""
        assert "missing_title" in track.issues

    def test_pydub_load_error_returns_none(self, tmp_path):
        f = tmp_path / "bad.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title"])
        with patch("pydub.AudioSegment.from_file", side_effect=Exception("bad file")):
            result = _fix_missing_tags(track, dry_run=False)
        assert result is None

    def test_shazam_no_match_returns_none(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title"])
        mock_segment = MagicMock()
        with patch("pydub.AudioSegment.from_file", return_value=mock_segment), \
             patch("music_vault.identify.recognizer.identify_segment", return_value=None):
            result = _fix_missing_tags(track, dry_run=False)
        assert result is None

    def test_successful_identification_embeds_metadata(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title", "missing_artist"])
        mock_segment = MagicMock()
        with patch("pydub.AudioSegment.from_file", return_value=mock_segment), \
             patch("music_vault.identify.recognizer.identify_segment", return_value=_SHAZAM_TRACK), \
             patch("music_vault.core.metadata.embed_metadata") as mock_embed, \
             patch("music_vault.core.metadata._parse_shazam_track", return_value=_PARSED):
            _fix_missing_tags(track, dry_run=False)
        mock_embed.assert_called_once_with(str(f), _SHAZAM_TRACK)

    def test_successful_identification_updates_track_fields(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title", "missing_artist"])
        mock_segment = MagicMock()
        with patch("pydub.AudioSegment.from_file", return_value=mock_segment), \
             patch("music_vault.identify.recognizer.identify_segment", return_value=_SHAZAM_TRACK), \
             patch("music_vault.core.metadata.embed_metadata"), \
             patch("music_vault.core.metadata._parse_shazam_track", return_value=_PARSED):
            _fix_missing_tags(track, dry_run=False)
        assert track.title == "Acid Tracks"
        assert track.artist == "Phuture"
        assert track.album == "Trax Classics"
        assert track.year == "1987"
        assert track.genre == "Electronic"

    def test_successful_identification_removes_tag_issues(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="",
                      issues=["missing_title", "missing_artist", "missing_cover"])
        mock_segment = MagicMock()
        with patch("pydub.AudioSegment.from_file", return_value=mock_segment), \
             patch("music_vault.identify.recognizer.identify_segment", return_value=_SHAZAM_TRACK), \
             patch("music_vault.core.metadata.embed_metadata"), \
             patch("music_vault.core.metadata._parse_shazam_track", return_value=_PARSED):
            _fix_missing_tags(track, dry_run=False)
        assert "missing_title" not in track.issues
        assert "missing_artist" not in track.issues
        assert "missing_cover" not in track.issues

    def test_description_contains_title_and_artist(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title"])
        mock_segment = MagicMock()
        with patch("pydub.AudioSegment.from_file", return_value=mock_segment), \
             patch("music_vault.identify.recognizer.identify_segment", return_value=_SHAZAM_TRACK), \
             patch("music_vault.core.metadata.embed_metadata"), \
             patch("music_vault.core.metadata._parse_shazam_track", return_value=_PARSED):
            result = _fix_missing_tags(track, dry_run=False)
        assert "Acid Tracks" in result
        assert "Phuture" in result

    def test_after_identification_filename_mismatch_also_fixed(self, tmp_path):
        f = tmp_path / "unknown.flac"
        f.touch()
        track = Track(path=f, title="", artist="", issues=["missing_title", "missing_artist"])
        mock_segment = MagicMock()
        with patch("pydub.AudioSegment.from_file", return_value=mock_segment), \
             patch("music_vault.identify.recognizer.identify_segment", return_value=_SHAZAM_TRACK), \
             patch("music_vault.core.metadata.embed_metadata"), \
             patch("music_vault.core.metadata._parse_shazam_track", return_value=_PARSED):
            actions = fix_library([track], dry_run=False)
        descriptions = [d for _, d in actions]
        assert any("identified" in d for d in descriptions)
        assert any("rename" in d for d in descriptions)
        assert (tmp_path / "Acid Tracks - Phuture.flac").exists()

