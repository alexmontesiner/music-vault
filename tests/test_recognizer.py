"""Tests for music_vault.identify.recognizer."""

from __future__ import annotations

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from music_vault.identify.recognizer import (
    _segment_to_bytes,
    identify_segment,
    identify_segment_async,
    print_track_info,
)


# ── _segment_to_bytes ─────────────────────────────────────────────────────────


class TestSegmentToBytes:
    def _make_segment(self, data: bytes = b"audio") -> MagicMock:
        seg = MagicMock()
        def fake_export(buf, **kwargs):
            buf.write(data)
        seg.export = fake_export
        return seg

    def test_returns_bytes(self):
        result = _segment_to_bytes(self._make_segment(b"hello"))
        assert isinstance(result, bytes)

    def test_returns_segment_data(self):
        result = _segment_to_bytes(self._make_segment(b"audio_data"))
        assert result == b"audio_data"

    def test_default_format_is_mp3(self):
        seg = MagicMock()
        captured_kwargs = {}
        def fake_export(buf, **kwargs):
            captured_kwargs.update(kwargs)
        seg.export = fake_export
        _segment_to_bytes(seg)
        assert captured_kwargs.get("format") == "mp3"

    def test_default_bitrate_is_128k(self):
        seg = MagicMock()
        captured_kwargs = {}
        def fake_export(buf, **kwargs):
            captured_kwargs.update(kwargs)
        seg.export = fake_export
        _segment_to_bytes(seg)
        assert captured_kwargs.get("bitrate") == "128k"

    def test_custom_format(self):
        seg = MagicMock()
        captured_kwargs = {}
        def fake_export(buf, **kwargs):
            captured_kwargs.update(kwargs)
        seg.export = fake_export
        _segment_to_bytes(seg, fmt="ogg")
        assert captured_kwargs["format"] == "ogg"


# ── identify_segment_async ────────────────────────────────────────────────────


def _make_audio_segment(duration_ms: int) -> MagicMock:
    seg = MagicMock()
    seg.__len__ = lambda s: duration_ms

    def _getitem(s, key):
        if isinstance(key, slice):
            start = key.start or 0
            stop = min(key.stop or duration_ms, duration_ms)
            window = MagicMock()
            window.__len__ = lambda w: max(0, stop - start)
            window.export = lambda buf, **kwargs: buf.write(b"fake")
            return window
        return MagicMock()

    seg.__getitem__ = _getitem
    return seg


class TestIdentifySegmentAsync:
    def test_returns_track_when_shazam_matches(self):
        track = {"title": "Test Song", "subtitle": "Test Artist"}
        seg = _make_audio_segment(30_000)

        async def run():
            with patch("music_vault.identify.recognizer._shazam_recognize",
                       new=AsyncMock(return_value=track)), \
                 patch("music_vault.identify.recognizer._segment_to_bytes", return_value=b"bytes"):
                return await identify_segment_async(seg)

        assert asyncio.run(run()) == track

    def test_returns_none_when_no_match(self):
        seg = _make_audio_segment(30_000)

        async def run():
            with patch("music_vault.identify.recognizer._shazam_recognize",
                       new=AsyncMock(return_value=None)), \
                 patch("music_vault.identify.recognizer._segment_to_bytes", return_value=b"bytes"):
                return await identify_segment_async(seg)

        assert asyncio.run(run()) is None

    def test_stops_after_first_match(self):
        track = {"title": "Found"}
        seg = _make_audio_segment(60_000)
        call_count = 0

        async def fake_recognize(audio_bytes):
            nonlocal call_count
            call_count += 1
            return track if call_count == 1 else None

        async def run():
            with patch("music_vault.identify.recognizer._shazam_recognize",
                       side_effect=fake_recognize), \
                 patch("music_vault.identify.recognizer._segment_to_bytes", return_value=b"b"):
                return await identify_segment_async(seg)

        asyncio.run(run())
        assert call_count == 1

    def test_skips_windows_shorter_than_5_seconds(self):
        # A very short audio segment: windows will be < 5 000 ms
        seg = _make_audio_segment(3_000)
        call_count = 0

        async def fake_recognize(audio_bytes):
            nonlocal call_count
            call_count += 1
            return None

        async def run():
            with patch("music_vault.identify.recognizer._shazam_recognize",
                       side_effect=fake_recognize), \
                 patch("music_vault.identify.recognizer._segment_to_bytes", return_value=b"b"):
                return await identify_segment_async(seg)

        result = asyncio.run(run())
        assert result is None
        assert call_count == 0


# ── identify_segment (sync wrapper) ──────────────────────────────────────────


class TestIdentifySegment:
    def test_synchronous_wrapper_returns_result(self):
        track = {"title": "Sync Test"}
        with patch("music_vault.identify.recognizer.identify_segment_async",
                   new=AsyncMock(return_value=track)):
            result = identify_segment(MagicMock())
        assert result == track


# ── print_track_info ──────────────────────────────────────────────────────────


class TestPrintTrackInfo:
    def test_prints_title(self, capsys):
        print_track_info({"title": "Bohemian Rhapsody", "subtitle": "Queen"})
        assert "Bohemian Rhapsody" in capsys.readouterr().out

    def test_prints_artist(self, capsys):
        print_track_info({"title": "Song", "subtitle": "The Band"})
        assert "The Band" in capsys.readouterr().out

    def test_missing_fields_shown_as_question_mark(self, capsys):
        print_track_info({})
        out = capsys.readouterr().out
        assert "?" in out

    def test_prints_section_metadata(self, capsys):
        track = {
            "title": "T",
            "subtitle": "A",
            "sections": [
                {"metadata": [
                    {"title": "Album", "text": "My Album"},
                    {"title": "Label", "text": "Some Label"},
                ]}
            ],
        }
        print_track_info(track)
        out = capsys.readouterr().out
        assert "My Album" in out
        assert "Some Label" in out

    def test_prints_primary_genre(self, capsys):
        track = {"title": "T", "subtitle": "A", "genres": {"primary": "Electronic"}}
        print_track_info(track)
        assert "Electronic" in capsys.readouterr().out

    def test_no_genre_key_no_error(self, capsys):
        print_track_info({"title": "T", "subtitle": "A"})
        # Should complete without raising

    def test_empty_metadata_values_not_printed(self, capsys):
        track = {
            "sections": [{"metadata": [{"title": "", "text": ""}]}]
        }
        print_track_info(track)
        # Should not raise; output for empty key/val is suppressed
