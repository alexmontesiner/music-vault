"""Tests for music_vault.identify.processor."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from music_vault.identify.processor import process_identified_track


def _make_segment() -> MagicMock:
    seg = MagicMock()
    seg.export = MagicMock()
    return seg


TRACK_INFO = {"title": "Bohemian Rhapsody", "subtitle": "Queen"}


def _kwargs(**overrides) -> dict:
    defaults = dict(
        segment=_make_segment(),
        track_info=TRACK_INFO,
        label="Track 01",
        output_dir="",          # overridden per test using tmp_path
        src_ext=".mp3",
        download_lossless=False,
        services=["qobuz"],
        keep_segments=False,
        verbose=False,
    )
    defaults.update(overrides)
    return defaults


# ── process_identified_track ──────────────────────────────────────────────────


class TestProcessIdentifiedTrack:
    def test_exports_segment_to_output_dir(self, tmp_path):
        seg = _make_segment()
        with patch("music_vault.identify.processor.embed_metadata"):
            process_identified_track(**_kwargs(segment=seg, output_dir=str(tmp_path)))
        seg.export.assert_called_once()
        export_path = seg.export.call_args[0][0]
        assert str(tmp_path) in export_path

    def test_calls_embed_metadata(self, tmp_path):
        with patch("music_vault.identify.processor.embed_metadata") as mock_embed:
            process_identified_track(**_kwargs(output_dir=str(tmp_path)))
        mock_embed.assert_called_once()

    def test_filename_uses_artist_and_title(self, tmp_path):
        seg = _make_segment()
        with patch("music_vault.identify.processor.embed_metadata"):
            process_identified_track(**_kwargs(
                segment=seg,
                output_dir=str(tmp_path),
                track_info={"title": "My Song", "subtitle": "My Artist"},
            ))
        export_path = seg.export.call_args[0][0]
        assert "My Artist" in export_path
        assert "My Song" in export_path

    def test_filename_uses_fallbacks_for_empty_track_info(self, tmp_path):
        seg = _make_segment()
        with patch("music_vault.identify.processor.embed_metadata"):
            process_identified_track(**_kwargs(
                segment=seg, track_info={}, output_dir=str(tmp_path)
            ))
        export_path = seg.export.call_args[0][0]
        assert "Unknown" in export_path

    def test_creates_output_directory(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        with patch("music_vault.identify.processor.embed_metadata"):
            process_identified_track(**_kwargs(output_dir=str(nested)))
        assert nested.exists()

    def test_no_download_when_flag_false(self, tmp_path):
        with patch("music_vault.identify.processor.embed_metadata"), \
             patch("music_vault.identify.processor._download_lossless") as mock_dl:
            process_identified_track(**_kwargs(
                output_dir=str(tmp_path), download_lossless=False
            ))
        mock_dl.assert_not_called()

    def test_calls_download_lossless_when_flag_true(self, tmp_path):
        with patch("music_vault.identify.processor.embed_metadata"), \
             patch("music_vault.identify.processor._download_lossless") as mock_dl:
            process_identified_track(**_kwargs(
                output_dir=str(tmp_path), download_lossless=True
            ))
        mock_dl.assert_called_once()

    def test_segment_exported_before_metadata_embedded(self, tmp_path):
        order = []
        seg = _make_segment()
        seg.export.side_effect = lambda *a, **kw: order.append("export")
        with patch("music_vault.identify.processor.embed_metadata",
                   side_effect=lambda *a, **kw: order.append("embed")):
            process_identified_track(**_kwargs(segment=seg, output_dir=str(tmp_path)))
        assert order == ["export", "embed"]

    def test_src_ext_determines_export_format(self, tmp_path):
        seg = _make_segment()
        with patch("music_vault.identify.processor.embed_metadata"):
            process_identified_track(**_kwargs(
                segment=seg, output_dir=str(tmp_path), src_ext=".flac"
            ))
        export_kwargs = seg.export.call_args[1]
        assert export_kwargs.get("format") == "flac"


# ── _download_lossless ────────────────────────────────────────────────────────


class TestDownloadLossless:
    from music_vault.identify.processor import _download_lossless as _dl

    def _run(self, spotify_url=None, download_raises=None, **overrides):
        from music_vault.identify.processor import _download_lossless
        from pathlib import Path

        defaults = dict(
            title="My Track",
            artist="My Artist",
            output_dir="/tmp/out",
            segment_path=Path("/tmp/out/seg.mp3"),
            services=["qobuz"],
            keep_segments=False,
            verbose=False,
        )
        defaults.update(overrides)

        with patch("music_vault.identify.processor.spotify_search_track",
                   return_value=spotify_url), \
             patch("music_vault.identify.processor.inject_ffmpeg"), \
             patch("music_vault.identify.processor.download_url",
                   side_effect=download_raises) as mock_dl:
            _download_lossless(**defaults)
        return mock_dl

    def test_no_spotify_url_skips_download(self):
        mock_dl = self._run(spotify_url=None)
        mock_dl.assert_not_called()

    def test_calls_download_url_with_lossless_quality(self):
        mock_dl = self._run(spotify_url="https://open.spotify.com/track/1")
        assert mock_dl.call_args[1]["quality"] == "LOSSLESS"

    def test_calls_download_url_with_correct_url(self):
        url = "https://open.spotify.com/track/abc"
        mock_dl = self._run(spotify_url=url)
        assert mock_dl.call_args[1]["url"] == url

    def test_download_exception_is_caught(self):
        # Must not raise
        self._run(
            spotify_url="https://open.spotify.com/track/1",
            download_raises=Exception("network error"),
        )

    def test_segment_removed_when_download_succeeds_and_keep_false(self, tmp_path):
        from music_vault.identify.processor import _download_lossless

        seg_path = tmp_path / "seg.mp3"
        seg_path.touch()

        with patch("music_vault.identify.processor.spotify_search_track",
                   return_value="https://open.spotify.com/track/1"), \
             patch("music_vault.identify.processor.inject_ffmpeg"), \
             patch("music_vault.identify.processor.download_url"):
            _download_lossless(
                title="T", artist="A", output_dir=str(tmp_path),
                segment_path=seg_path, services=[], keep_segments=False, verbose=False,
            )
        assert not seg_path.exists()

    def test_segment_kept_when_keep_segments_true(self, tmp_path):
        from music_vault.identify.processor import _download_lossless

        seg_path = tmp_path / "seg.mp3"
        seg_path.touch()

        with patch("music_vault.identify.processor.spotify_search_track",
                   return_value="https://open.spotify.com/track/1"), \
             patch("music_vault.identify.processor.inject_ffmpeg"), \
             patch("music_vault.identify.processor.download_url"):
            _download_lossless(
                title="T", artist="A", output_dir=str(tmp_path),
                segment_path=seg_path, services=[], keep_segments=True, verbose=False,
            )
        assert seg_path.exists()
