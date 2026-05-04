"""Tests for main.py entry point."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

import main as main_module


class TestMainUrlInjection:
    """Bare Spotify URLs without a subcommand should get 'download' injected."""

    def test_spotify_url_without_subcommand_injects_download(self):
        argv = ["music-vault", "https://open.spotify.com/track/123"]
        with patch.object(sys, "argv", argv[:]):  # copy so original isn't mutated
            with patch("music_vault.cli.download_cmd.cmd_download") as mock_cmd, \
                 patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
                 patch("music_vault.cli.download_cmd._run_spotiflac"):
                main_module.main()
            assert sys.argv[1] == "download"

    def test_non_spotify_url_is_not_modified(self):
        """When 'download' is already the subcommand, it should not be inserted again."""
        argv = ["music-vault", "download", "https://open.spotify.com/track/123"]
        captured = {}
        with patch.object(sys, "argv", argv):
            with patch("music_vault.cli.download_cmd.cmd_download"), \
                 patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
                 patch("music_vault.cli.download_cmd._run_spotiflac"):
                main_module.main()
                captured["argv"] = sys.argv[:]
        # 'download' appears exactly once at index 1
        assert captured["argv"][1] == "download"
        assert captured["argv"].count("download") == 1


class TestMainDispatch:
    def test_download_command_dispatched_to_cmd_download(self):
        with patch.object(sys, "argv", ["music-vault", "download",
                                        "https://open.spotify.com/track/1"]):
            with patch("music_vault.cli.download_cmd.cmd_download") as mock_cmd, \
                 patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
                 patch("music_vault.cli.download_cmd._run_spotiflac"):
                main_module.main()
        mock_cmd.assert_called_once()

    def test_identify_command_dispatched_to_cmd_identify(self, tmp_path):
        audio = tmp_path / "song.mp3"
        audio.touch()
        with patch.object(sys, "argv", ["music-vault", "identify", str(audio)]):
            with patch("music_vault.cli.identify_cmd.cmd_identify") as mock_cmd, \
                 patch("music_vault.cli.identify_cmd.inject_ffmpeg"):
                main_module.main()
        mock_cmd.assert_called_once()

    def test_no_command_prints_help(self, capsys):
        with patch.object(sys, "argv", ["music-vault"]):
            main_module.main()
        out = capsys.readouterr().out
        assert "music-vault" in out or "usage" in out.lower()
