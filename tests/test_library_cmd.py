"""Tests for music_vault.cli.library_cmd and the library sub-command in the parser."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from music_vault.cli.library_cmd import cmd_library
from music_vault.cli.parser import build_parser
from music_vault.library.scanner import Track


def _args(**overrides) -> Namespace:
    defaults = dict(path="downloads", fix=False, dry_run=False)
    defaults.update(overrides)
    return Namespace(**defaults)


def _make_track(name="Artist - Song.flac", issues=None) -> Track:
    return Track(path=Path(f"/lib/{name}"), title="Song", artist="Artist",
                 issues=issues or [])


# ── parser ────────────────────────────────────────────────────────────────────


class TestLibraryParser:
    def test_library_command_recognised(self):
        args = build_parser().parse_args(["library"])
        assert args.command == "library"

    def test_default_path(self):
        args = build_parser().parse_args(["library"])
        assert args.path == "downloads"

    def test_custom_path(self):
        args = build_parser().parse_args(["library", "--path", "/music"])
        assert args.path == "/music"

    def test_fix_default_false(self):
        assert build_parser().parse_args(["library"]).fix is False

    def test_fix_flag(self):
        assert build_parser().parse_args(["library", "--fix"]).fix is True

    def test_dry_run_default_false(self):
        assert build_parser().parse_args(["library"]).dry_run is False

    def test_dry_run_flag(self):
        assert build_parser().parse_args(["library", "--dry-run"]).dry_run is True


# ── cmd_library ───────────────────────────────────────────────────────────────


class TestCmdLibrary:
    def _run(self, tracks=None, fix_actions=None, **arg_overrides):
        tracks = tracks or []
        with patch("music_vault.cli.library_cmd.scan_library", return_value=tracks) as mock_scan, \
             patch("music_vault.cli.library_cmd.check_all") as mock_check, \
             patch("music_vault.cli.library_cmd.print_report") as mock_report, \
             patch("music_vault.cli.library_cmd.fix_library", return_value=fix_actions) as mock_fix:
            cmd_library(_args(**arg_overrides))
        return mock_scan, mock_check, mock_report, mock_fix

    def test_calls_scan_library_with_path(self):
        mock_scan, _, _, _ = self._run(path="/my/music")
        mock_scan.assert_called_once_with("/my/music")

    def test_calls_check_all_with_tracks(self):
        tracks = [_make_track()]
        _, mock_check, _, _ = self._run(tracks=tracks)
        mock_check.assert_called_once_with(tracks)

    def test_calls_print_report(self):
        _, _, mock_report, _ = self._run()
        mock_report.assert_called_once()

    def test_no_fix_flag_skips_fix_library(self):
        _, _, _, mock_fix = self._run(fix=False, dry_run=False)
        mock_fix.assert_not_called()

    def test_fix_flag_calls_fix_library_with_dry_run_false(self):
        tracks = [_make_track(issues=["filename_mismatch"])]
        _, _, _, mock_fix = self._run(tracks=tracks, fix=True, dry_run=False)
        mock_fix.assert_called_once_with(tracks, dry_run=False)

    def test_dry_run_flag_calls_fix_library_with_dry_run_true(self):
        tracks = [_make_track(issues=["filename_mismatch"])]
        _, _, _, mock_fix = self._run(tracks=tracks, fix=False, dry_run=True)
        mock_fix.assert_called_once_with(tracks, dry_run=True)

    def test_no_actions_prints_nothing_to_fix(self, capsys):
        self._run(fix=True, fix_actions=None)  # None = no fixable tracks
        assert "Nothing to fix" in capsys.readouterr().out

    def test_fix_action_description_printed(self, capsys):
        track = _make_track(issues=["filename_mismatch"])
        self._run(tracks=[track], fix=True, fix_actions=[(track, "rename  old.mp3  →  new.mp3")])
        assert "rename  old.mp3  →  new.mp3" in capsys.readouterr().out

    def test_dry_run_prefix_in_output(self, capsys):
        track = _make_track(issues=["filename_mismatch"])
        self._run(tracks=[track], dry_run=True, fix_actions=[(track, "rename  old.mp3  →  new.mp3")])
        assert "[DRY RUN]" in capsys.readouterr().out

    def test_fix_prefix_in_output(self, capsys):
        track = _make_track(issues=["filename_mismatch"])
        self._run(tracks=[track], fix=True, fix_actions=[(track, "rename  old.mp3  →  new.mp3")])
        assert "[FIX]" in capsys.readouterr().out

    def test_scanning_message_includes_path(self, capsys):
        self._run(path="/my/music")
        assert "/my/music" in capsys.readouterr().out
