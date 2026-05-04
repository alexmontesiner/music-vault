"""Tests for music_vault.identify.splitter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from music_vault.identify.splitter import VinylSplitter


def _make_audio(duration_ms: int = 200_000) -> MagicMock:
    """Build a minimal pydub-like AudioSegment mock."""
    audio = MagicMock()
    audio.__len__ = lambda s: duration_ms
    # Slicing returns a new mock whose len is the slice width (capped to duration)
    def _getitem(s, key):
        if isinstance(key, slice):
            start = key.start or 0
            stop = min(key.stop or duration_ms, duration_ms)
            window = MagicMock()
            window.__len__ = lambda w: max(0, stop - start)
            return window
        return MagicMock()
    audio.__getitem__ = _getitem
    return audio


# ── __init__ ──────────────────────────────────────────────────────────────────


class TestVinylSplitterInit:
    def test_default_min_silence_len(self):
        assert VinylSplitter().min_silence_len == 1_500

    def test_default_silence_thresh(self):
        assert VinylSplitter().silence_thresh == -50

    def test_default_min_track_len(self):
        assert VinylSplitter().min_track_len == 30

    def test_default_pad_ms(self):
        assert VinylSplitter().pad_ms == 300

    def test_custom_params_stored(self):
        s = VinylSplitter(min_silence_len=2000, silence_thresh=-40, min_track_len=20, pad_ms=500)
        assert s.min_silence_len == 2000
        assert s.silence_thresh == -40
        assert s.min_track_len == 20
        assert s.pad_ms == 500


# ── split ─────────────────────────────────────────────────────────────────────


class TestVinylSplitterSplit:
    PYDUB_MODULE = "pydub.silence"

    def _split(self, non_silent, min_track_len=10, min_silence_len=1500, duration_ms=200_000):
        splitter = VinylSplitter(min_silence_len=min_silence_len, min_track_len=min_track_len)
        audio = _make_audio(duration_ms)
        mock_silence = MagicMock()
        mock_silence.detect_nonsilent.return_value = non_silent
        with patch.dict("sys.modules", {"pydub": MagicMock(), "pydub.silence": mock_silence}):
            return splitter.split(audio)

    def test_no_nonsilent_regions_exits(self):
        splitter = VinylSplitter()
        audio = _make_audio()
        mock_silence = MagicMock()
        mock_silence.detect_nonsilent.return_value = []
        with patch.dict("sys.modules", {"pydub": MagicMock(), "pydub.silence": mock_silence}):
            with pytest.raises(SystemExit):
                splitter.split(audio)

    def test_two_valid_segments_returned(self):
        # Two 60 s tracks with a 5 s silence gap
        non_silent = [[0, 60_000], [65_000, 125_000]]
        segments = self._split(non_silent, min_track_len=10)
        assert len(segments) == 2

    def test_short_segment_filtered_out(self):
        # First segment: 5 s (below 30 s threshold), second: 60 s
        non_silent = [[0, 5_000], [40_000, 100_000]]
        segments = self._split(non_silent, min_track_len=30)
        assert len(segments) == 1

    def test_all_segments_too_short_exits(self):
        splitter = VinylSplitter(min_track_len=60)
        audio = _make_audio()
        mock_silence = MagicMock()
        mock_silence.detect_nonsilent.return_value = [[0, 10_000]]  # 10 s < 60 s
        with patch.dict("sys.modules", {"pydub": MagicMock(), "pydub.silence": mock_silence}):
            with pytest.raises(SystemExit):
                splitter.split(audio)

    def test_close_regions_merged(self):
        # Gap between regions (500 ms) is less than min_silence_len (1500 ms) → merged
        non_silent = [[0, 30_000], [30_500, 60_000]]
        segments = self._split(non_silent, min_silence_len=1500, min_track_len=10)
        assert len(segments) == 1

    def test_far_apart_regions_not_merged(self):
        # Gap (5 000 ms) > min_silence_len (1 500 ms) → two separate segments
        non_silent = [[0, 30_000], [35_000, 65_000]]
        segments = self._split(non_silent, min_silence_len=1500, min_track_len=10)
        assert len(segments) == 2

    def test_single_valid_segment(self):
        non_silent = [[1_000, 61_000]]  # 60 s
        segments = self._split(non_silent, min_track_len=10)
        assert len(segments) == 1

    def test_returns_list(self):
        non_silent = [[0, 60_000]]
        segments = self._split(non_silent, min_track_len=10)
        assert isinstance(segments, list)


# ── _print_detected ───────────────────────────────────────────────────────────


class TestPrintDetected:
    def test_prints_segment_count(self, capsys):
        VinylSplitter._print_detected([(0, 60_000), (70_000, 130_000)])
        assert "2 track segment(s)" in capsys.readouterr().out

    def test_prints_track_labels(self, capsys):
        VinylSplitter._print_detected([(0, 60_000), (70_000, 130_000)])
        out = capsys.readouterr().out
        assert "Track 01" in out
        assert "Track 02" in out

    def test_prints_timestamps(self, capsys):
        VinylSplitter._print_detected([(0, 30_000)])
        out = capsys.readouterr().out
        assert "0.0" in out
        assert "30.0" in out

    def test_single_segment(self, capsys):
        VinylSplitter._print_detected([(5_000, 65_000)])
        assert "1 track segment(s)" in capsys.readouterr().out
