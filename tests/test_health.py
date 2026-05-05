"""Tests for music_vault.library.health."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_vault.library.health import (
    LOSSLESS_FORMATS,
    LOSSY_FORMATS,
    _check_single,
    _flag_duplicates,
    _flag_lossy_redundant,
    check_all,
)
from music_vault.library.scanner import Track


def _track(
    name="Queen - Bohemian Rhapsody.flac",
    fmt="flac",
    title="Bohemian Rhapsody",
    artist="Queen",
    album="A Night at the Opera",
    year="1975",
    genre="Rock",
    has_cover=True,
) -> Track:
    return Track(
        path=Path(f"/lib/{name}"),
        title=title,
        artist=artist,
        album=album,
        year=year,
        genre=genre,
        has_cover=has_cover,
        format=fmt,
        duration_sec=354.0,
    )


# ── _check_single ─────────────────────────────────────────────────────────────


class TestCheckSingle:
    def test_complete_track_no_issues(self):
        assert _check_single(_track()) == []

    def test_missing_title(self):
        assert "missing_title" in _check_single(_track(title=""))

    def test_missing_artist(self):
        assert "missing_artist" in _check_single(_track(artist=""))

    def test_missing_album(self):
        assert "missing_album" in _check_single(_track(album=""))

    def test_missing_year(self):
        assert "missing_year" in _check_single(_track(year=""))

    def test_missing_genre(self):
        assert "missing_genre" in _check_single(_track(genre=""))

    def test_missing_cover(self):
        assert "missing_cover" in _check_single(_track(has_cover=False))

    def test_filename_matches_tags_no_issue(self):
        t = _track(name="Queen - Bohemian Rhapsody.flac",
                   artist="Queen", title="Bohemian Rhapsody")
        assert "filename_mismatch" not in _check_single(t)

    def test_filename_mismatch_flagged(self):
        t = _track(name="wrong_filename.flac",
                   artist="Queen", title="Bohemian Rhapsody")
        assert "filename_mismatch" in _check_single(t)

    def test_no_filename_check_when_title_empty(self):
        t = _track(name="anything.flac", title="", artist="Queen")
        assert "filename_mismatch" not in _check_single(t)

    def test_no_filename_check_when_artist_empty(self):
        t = _track(name="anything.flac", title="Song", artist="")
        assert "filename_mismatch" not in _check_single(t)

    def test_multiple_issues_returned(self):
        t = _track(title="", artist="", has_cover=False)
        issues = _check_single(t)
        assert "missing_title" in issues
        assert "missing_artist" in issues
        assert "missing_cover" in issues


# ── _flag_duplicates ──────────────────────────────────────────────────────────


class TestFlagDuplicates:
    def test_unique_tracks_not_flagged(self):
        tracks = [
            _track(name="a.flac", title="Song A", artist="Artist"),
            _track(name="b.flac", title="Song B", artist="Artist"),
        ]
        _flag_duplicates(tracks)
        assert all("duplicate" not in t.issues for t in tracks)

    def test_duplicate_pair_both_flagged(self):
        tracks = [
            _track(name="a.flac", title="Song", artist="Artist"),
            _track(name="b.mp3",  title="Song", artist="Artist"),
        ]
        _flag_duplicates(tracks)
        assert all("duplicate" in t.issues for t in tracks)

    def test_case_insensitive_matching(self):
        tracks = [
            _track(name="a.flac", title="song", artist="artist"),
            _track(name="b.flac", title="SONG", artist="ARTIST"),
        ]
        _flag_duplicates(tracks)
        assert all("duplicate" in t.issues for t in tracks)

    def test_no_duplicate_flag_for_empty_title(self):
        tracks = [
            _track(name="a.flac", title="", artist="Artist"),
            _track(name="b.flac", title="", artist="Artist"),
        ]
        _flag_duplicates(tracks)
        assert all("duplicate" not in t.issues for t in tracks)

    def test_duplicate_not_added_twice(self):
        tracks = [
            _track(name="a.flac", title="Song", artist="Artist"),
            _track(name="b.flac", title="Song", artist="Artist"),
        ]
        _flag_duplicates(tracks)
        _flag_duplicates(tracks)  # second call
        assert tracks[0].issues.count("duplicate") == 1


# ── _flag_lossy_redundant ─────────────────────────────────────────────────────


class TestFlagLossyRedundant:
    def test_only_lossy_not_flagged(self):
        tracks = [_track(name="a.mp3", fmt="mp3")]
        _flag_lossy_redundant(tracks)
        assert "lossy_redundant" not in tracks[0].issues

    def test_only_lossless_not_flagged(self):
        tracks = [_track(name="a.flac", fmt="flac")]
        _flag_lossy_redundant(tracks)
        assert "lossy_redundant" not in tracks[0].issues

    def test_lossy_flagged_when_lossless_exists(self):
        flac = _track(name="a.flac", fmt="flac", title="Song", artist="Artist")
        mp3  = _track(name="a.mp3",  fmt="mp3",  title="Song", artist="Artist")
        _flag_lossy_redundant([flac, mp3])
        assert "lossy_redundant" in mp3.issues
        assert "lossy_redundant" not in flac.issues

    @pytest.mark.parametrize("lossless_fmt", list(LOSSLESS_FORMATS))
    def test_all_lossless_formats_protect_lossy(self, lossless_fmt):
        lossless = _track(name=f"a.{lossless_fmt}", fmt=lossless_fmt,
                          title="Song", artist="Artist")
        mp3 = _track(name="a.mp3", fmt="mp3", title="Song", artist="Artist")
        _flag_lossy_redundant([lossless, mp3])
        assert "lossy_redundant" in mp3.issues

    def test_different_tracks_not_flagged(self):
        flac = _track(name="a.flac", fmt="flac", title="Song A", artist="Artist")
        mp3  = _track(name="b.mp3",  fmt="mp3",  title="Song B", artist="Artist")
        _flag_lossy_redundant([flac, mp3])
        assert "lossy_redundant" not in mp3.issues


# ── check_all integration ─────────────────────────────────────────────────────


class TestCheckAll:
    def test_check_all_runs_single_checks(self):
        t = _track(title="")
        check_all([t])
        assert "missing_title" in t.issues

    def test_check_all_runs_cross_track_checks(self):
        t1 = _track(name="a.flac", title="Song", artist="Artist")
        t2 = _track(name="b.mp3",  fmt="mp3", title="Song", artist="Artist")
        check_all([t1, t2])
        assert "duplicate" in t1.issues
        assert "lossy_redundant" in t2.issues

    def test_check_all_resets_issues_on_second_call(self):
        t = _track(title="")
        check_all([t])
        assert "missing_title" in t.issues
        t.title = "Now has a title"
        check_all([t])
        assert "missing_title" not in t.issues
