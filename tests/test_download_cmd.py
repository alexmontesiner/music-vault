"""Tests for music_vault.cli.download_cmd."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from music_vault.cli.download_cmd import cmd_download, _run_spotiflac


def _args(**overrides) -> Namespace:
    defaults = dict(
        url="https://open.spotify.com/track/abc123",
        output="downloads/spotify",
        quality="flac",
        format="flac",
        services=["qobuz", "amazon", "youtube"],
        lyrics=True,
        verbose=False,
        update=False,
    )
    defaults.update(overrides)
    return Namespace(**defaults)


# ── cmd_download ──────────────────────────────────────────────────────────────


class TestCmdDownload:
    def test_non_spotify_url_exits_with_code_1(self):
        with pytest.raises(SystemExit) as exc:
            cmd_download(_args(url="https://example.com/not-spotify"))
        assert exc.value.code == 1

    def test_non_spotify_url_prints_error(self, capsys):
        with pytest.raises(SystemExit):
            cmd_download(_args(url="https://example.com/not-spotify"))
        assert "Invalid Spotify URL" in capsys.readouterr().err

    def test_calls_inject_ffmpeg(self):
        with patch("music_vault.cli.download_cmd.inject_ffmpeg") as mock_inject, \
             patch("music_vault.cli.download_cmd._run_spotiflac"):
            cmd_download(_args())
        mock_inject.assert_called_once()

    def test_calls_run_spotiflac(self):
        with patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
             patch("music_vault.cli.download_cmd._run_spotiflac") as mock_run:
            cmd_download(_args())
        mock_run.assert_called_once()

    def test_passes_lossless_quality_for_flac(self):
        with patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
             patch("music_vault.cli.download_cmd._run_spotiflac") as mock_run:
            cmd_download(_args(quality="flac"))
        _, quality_arg, _ = mock_run.call_args[0]
        assert quality_arg == "LOSSLESS"

    def test_passes_hi_res_quality(self):
        with patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
             patch("music_vault.cli.download_cmd._run_spotiflac") as mock_run:
            cmd_download(_args(quality="hi-res"))
        _, quality_arg, _ = mock_run.call_args[0]
        assert quality_arg == "HI_RES"

    def test_update_mode_calls_snapshot_before_and_after(self, tmp_path):
        with patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
             patch("music_vault.cli.download_cmd._run_spotiflac"), \
             patch("music_vault.cli.download_cmd.snapshot_audio_files",
                   return_value=set()) as mock_snap, \
             patch("music_vault.cli.download_cmd.print_update_summary"):
            cmd_download(_args(update=True, output=str(tmp_path)))
        assert mock_snap.call_count == 2

    def test_update_mode_calls_print_summary(self, tmp_path):
        with patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
             patch("music_vault.cli.download_cmd._run_spotiflac"), \
             patch("music_vault.cli.download_cmd.snapshot_audio_files", return_value=set()), \
             patch("music_vault.cli.download_cmd.print_update_summary") as mock_summary:
            cmd_download(_args(update=True, output=str(tmp_path)))
        mock_summary.assert_called_once()

    def test_no_update_mode_skips_snapshot(self):
        with patch("music_vault.cli.download_cmd.inject_ffmpeg"), \
             patch("music_vault.cli.download_cmd._run_spotiflac"), \
             patch("music_vault.cli.download_cmd.snapshot_audio_files") as mock_snap:
            cmd_download(_args(update=False))
        mock_snap.assert_not_called()


# ── _run_spotiflac ────────────────────────────────────────────────────────────


class TestRunSpotiflac:
    def test_instantiates_spotiflac_and_calls_download(self):
        mock_spotiflac_cls = MagicMock()
        mock_instance = MagicMock()
        mock_spotiflac_cls.return_value = mock_instance
        mock_module = MagicMock(SpotiFLAC=mock_spotiflac_cls)
        with patch.dict("sys.modules", {"spotiflac": mock_module}):
            _run_spotiflac(_args(), "LOSSLESS", "downloads/spotify/flac")
        mock_instance.download.assert_called_once()

    def test_passes_correct_kwargs_to_spotiflac(self):
        args = _args(
            url="https://open.spotify.com/track/x",
            output="/tmp/out",
            services=["qobuz"],
            lyrics=True,
            verbose=False,
        )
        mock_spotiflac_cls = MagicMock()
        mock_module = MagicMock(SpotiFLAC=mock_spotiflac_cls)
        with patch.dict("sys.modules", {"spotiflac": mock_module}):
            _run_spotiflac(args, "LOSSLESS", "/tmp/out/flac")
        call_kwargs = mock_spotiflac_cls.call_args[1]
        assert call_kwargs["url"] == args.url
        assert call_kwargs["output"] == "/tmp/out/flac"
        assert call_kwargs["quality"] == "LOSSLESS"
        assert call_kwargs["services"] == ["qobuz"]

    def test_keyboard_interrupt_exits_cleanly(self):
        mock_spotiflac_cls = MagicMock(side_effect=KeyboardInterrupt)
        mock_module = MagicMock(SpotiFLAC=mock_spotiflac_cls)
        with patch.dict("sys.modules", {"spotiflac": mock_module}):
            with pytest.raises(SystemExit) as exc:
                _run_spotiflac(_args(), "LOSSLESS", "downloads/spotify/flac")
        assert exc.value.code == 0

    def test_generic_exception_exits_with_code_1(self):
        mock_spotiflac_cls = MagicMock(side_effect=Exception("Download error"))
        mock_module = MagicMock(SpotiFLAC=mock_spotiflac_cls)
        with patch.dict("sys.modules", {"spotiflac": mock_module}):
            with pytest.raises(SystemExit) as exc:
                _run_spotiflac(_args(), "LOSSLESS", "downloads/spotify/flac")
        assert exc.value.code == 1
