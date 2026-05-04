"""Tests for music_vault.cli.identify_cmd."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from music_vault.cli.identify_cmd import _print_vinyl_summary


def _args(**overrides) -> Namespace:
    defaults = dict(
        input="recording.mp3",
        output="downloads/identified",
        services=["qobuz", "amazon", "youtube"],
        split=False,
        min_silence_len=1500,
        silence_thresh=-50,
        min_track_len=30,
        download_lossless=False,
        keep_segments=False,
        verbose=False,
    )
    defaults.update(overrides)
    return Namespace(**defaults)


# ── _print_vinyl_summary ──────────────────────────────────────────────────────


class TestPrintVinylSummary:
    def test_prints_total_segments(self, capsys):
        results = [("Track 01", {"title": "A"}), ("Track 02", None)]
        _print_vinyl_summary(results)
        assert "2" in capsys.readouterr().out

    def test_prints_identified_count(self, capsys):
        results = [("Track 01", {"title": "A"}), ("Track 02", {"title": "B"})]
        _print_vinyl_summary(results)
        out = capsys.readouterr().out
        assert "Identified" in out
        assert "2" in out

    def test_prints_unidentified_count_when_present(self, capsys):
        results = [("Track 01", {"title": "A"}), ("Track 02", None)]
        _print_vinyl_summary(results)
        out = capsys.readouterr().out
        assert "Unidentified" in out
        assert "Track 02" in out

    def test_no_unidentified_section_when_all_identified(self, capsys):
        results = [("Track 01", {"title": "A"})]
        _print_vinyl_summary(results)
        assert "Unidentified" not in capsys.readouterr().out

    def test_all_unidentified(self, capsys):
        results = [("Track 01", None), ("Track 02", None)]
        _print_vinyl_summary(results)
        out = capsys.readouterr().out
        assert "Track 01" in out
        assert "Track 02" in out

    def test_empty_results(self, capsys):
        _print_vinyl_summary([])
        out = capsys.readouterr().out
        assert "0" in out


# ── cmd_identify ──────────────────────────────────────────────────────────────


class TestCmdIdentify:
    def test_nonexistent_file_exits_with_code_1(self, tmp_path):
        from music_vault.cli.identify_cmd import cmd_identify

        args = _args(input=str(tmp_path / "does_not_exist.mp3"))
        with patch("music_vault.cli.identify_cmd.inject_ffmpeg"):
            with pytest.raises(SystemExit) as exc:
                cmd_identify(args)
        assert exc.value.code == 1

    def test_nonexistent_file_prints_error(self, tmp_path, capsys):
        from music_vault.cli.identify_cmd import cmd_identify

        args = _args(input=str(tmp_path / "missing.mp3"))
        with patch("music_vault.cli.identify_cmd.inject_ffmpeg"):
            with pytest.raises(SystemExit):
                cmd_identify(args)
        assert "File not found" in capsys.readouterr().err

    def test_audio_load_failure_exits_with_code_1(self, tmp_path):
        from music_vault.cli.identify_cmd import cmd_identify

        audio_file = tmp_path / "bad.mp3"
        audio_file.touch()
        args = _args(input=str(audio_file))
        mock_audio_segment = MagicMock()
        mock_audio_segment.from_file.side_effect = Exception("Corrupt file")
        mock_pydub = MagicMock(AudioSegment=mock_audio_segment)
        with patch("music_vault.cli.identify_cmd.inject_ffmpeg"), \
             patch.dict("sys.modules", {"pydub": mock_pydub}):
            with pytest.raises(SystemExit) as exc:
                cmd_identify(args)
        assert exc.value.code == 1

    def test_single_mode_calls_identify_segment(self, tmp_path):
        from music_vault.cli.identify_cmd import cmd_identify

        audio_file = tmp_path / "track.mp3"
        audio_file.touch()
        args = _args(input=str(audio_file), split=False)

        mock_audio = MagicMock()
        mock_audio.__len__ = lambda s: 60_000
        mock_audio_segment = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_pydub = MagicMock(AudioSegment=mock_audio_segment)

        with patch("music_vault.cli.identify_cmd.inject_ffmpeg"), \
             patch.dict("sys.modules", {"pydub": mock_pydub}), \
             patch("music_vault.cli.identify_cmd.identify_segment", return_value=None) as mock_id, \
             patch("music_vault.cli.identify_cmd.process_identified_track"):
            cmd_identify(args)
        mock_id.assert_called_once_with(mock_audio)

    def test_split_mode_uses_vinyl_splitter(self, tmp_path):
        from music_vault.cli.identify_cmd import cmd_identify

        audio_file = tmp_path / "side_a.mp3"
        audio_file.touch()
        args = _args(input=str(audio_file), split=True)

        mock_audio = MagicMock()
        mock_audio.__len__ = lambda s: 120_000
        mock_audio_segment = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_pydub = MagicMock(AudioSegment=mock_audio_segment)

        mock_splitter = MagicMock()
        mock_splitter.split.return_value = []

        with patch("music_vault.cli.identify_cmd.inject_ffmpeg"), \
             patch.dict("sys.modules", {"pydub": mock_pydub}), \
             patch("music_vault.cli.identify_cmd.VinylSplitter", return_value=mock_splitter):
            cmd_identify(args)
        mock_splitter.split.assert_called_once_with(mock_audio)
