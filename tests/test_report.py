"""Tests for music_vault.library.report."""

from __future__ import annotations

from pathlib import Path

import pytest

from music_vault.library.report import print_report
from music_vault.library.scanner import Track


def _track(name="song.flac", issues=None) -> Track:
    return Track(path=Path(f"/lib/{name}"), title="Song", artist="Artist",
                 issues=issues or [])


class TestPrintReport:
    def test_empty_library_prints_not_found_message(self, capsys):
        print_report([])
        assert "No audio files found" in capsys.readouterr().out

    def test_shows_total_track_count(self, capsys):
        tracks = [_track(f"s{i}.flac") for i in range(5)]
        print_report(tracks)
        assert "5 track(s)" in capsys.readouterr().out

    def test_healthy_count_shown(self, capsys):
        tracks = [_track("a.flac", issues=[]), _track("b.flac", issues=[])]
        print_report(tracks)
        out = capsys.readouterr().out
        assert "Healthy" in out
        assert "2" in out

    def test_issues_count_shown(self, capsys):
        tracks = [
            _track("a.flac", issues=[]),
            _track("b.flac", issues=["missing_cover"]),
        ]
        print_report(tracks)
        out = capsys.readouterr().out
        assert "Issues" in out

    def test_issue_file_name_shown(self, capsys):
        tracks = [_track("broken_track.mp3", issues=["missing_title"])]
        print_report(tracks)
        assert "broken_track.mp3" in capsys.readouterr().out

    def test_issue_label_shown(self, capsys):
        tracks = [_track("s.mp3", issues=["missing_title"])]
        print_report(tracks)
        assert "Missing title" in capsys.readouterr().out

    def test_issue_breakdown_shows_frequency(self, capsys):
        tracks = [
            _track("a.flac", issues=["missing_cover"]),
            _track("b.flac", issues=["missing_cover"]),
            _track("c.flac", issues=["missing_year"]),
        ]
        print_report(tracks)
        out = capsys.readouterr().out
        assert "Issue breakdown" in out
        # missing_cover appears twice, missing_year once
        assert "No cover art" in out
        assert "Missing year" in out

    def test_healthy_tracks_not_listed_in_detail(self, capsys):
        tracks = [_track("clean.flac", issues=[])]
        print_report(tracks)
        # A fully healthy track's file name should NOT appear in the detail section
        assert "clean.flac" not in capsys.readouterr().out

    def test_separator_lines_present(self, capsys):
        print_report([])
        assert "═" in capsys.readouterr().out

    def test_unknown_issue_code_falls_back_to_raw_string(self, capsys):
        tracks = [_track("s.flac", issues=["some_future_issue"])]
        print_report(tracks)
        assert "some_future_issue" in capsys.readouterr().out

    def test_multiple_issues_per_track_all_shown(self, capsys):
        tracks = [_track("s.flac", issues=["missing_title", "missing_cover"])]
        print_report(tracks)
        out = capsys.readouterr().out
        assert "Missing title" in out
        assert "No cover art" in out
