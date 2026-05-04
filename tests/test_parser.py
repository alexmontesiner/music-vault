"""Tests for music_vault.cli.parser."""

from __future__ import annotations

import pytest

from music_vault.cli.parser import build_parser


@pytest.fixture
def parser():
    return build_parser()


class TestParserBasics:
    def test_prog_name(self, parser):
        assert parser.prog == "music-vault"

    def test_no_subcommand_returns_none_command(self, parser):
        args = parser.parse_args([])
        assert args.command is None

    def test_download_command_name(self, parser):
        args = parser.parse_args(["download", "https://open.spotify.com/track/1"])
        assert args.command == "download"

    def test_identify_command_name(self, parser):
        args = parser.parse_args(["identify", "file.mp3"])
        assert args.command == "identify"


class TestDownloadSubcommand:
    URL = "https://open.spotify.com/track/abc123"

    def _parse(self, *extra, parser=None):
        p = parser or build_parser()
        return p.parse_args(["download", self.URL, *extra])

    def test_url_positional(self):
        args = self._parse()
        assert args.url == self.URL

    def test_default_output(self):
        assert self._parse().output == "downloads/spotify"

    def test_custom_output_short(self):
        assert self._parse("-o", "/tmp/out").output == "/tmp/out"

    def test_custom_output_long(self):
        assert self._parse("--output", "/tmp/out").output == "/tmp/out"

    def test_default_quality(self):
        assert self._parse().quality == "flac"

    def test_quality_flac(self):
        assert self._parse("-q", "flac").quality == "flac"

    def test_quality_hi_res(self):
        assert self._parse("-q", "hi-res").quality == "hi-res"

    def test_invalid_quality_exits(self):
        with pytest.raises(SystemExit):
            self._parse("-q", "invalid")

    def test_default_services(self):
        assert self._parse().services == ["qobuz", "amazon", "youtube"]

    def test_custom_services(self):
        args = self._parse("-s", "qobuz", "youtube")
        assert args.services == ["qobuz", "youtube"]

    def test_update_default_false(self):
        assert self._parse().update is False

    def test_update_flag(self):
        assert self._parse("--update").update is True

    def test_verbose_default_false(self):
        assert self._parse().verbose is False

    def test_verbose_flag(self):
        assert self._parse("--verbose").verbose is True

    def test_lyrics_default_true(self):
        assert self._parse().lyrics is True


class TestIdentifySubcommand:
    FILE = "recording.mp3"

    def _parse(self, *extra):
        return build_parser().parse_args(["identify", self.FILE, *extra])

    def test_input_positional(self):
        assert self._parse().input == self.FILE

    def test_default_output(self):
        assert self._parse().output == "downloads/identified"

    def test_custom_output_short(self):
        assert self._parse("-o", "/tmp/id").output == "/tmp/id"

    def test_default_services(self):
        assert self._parse().services == ["qobuz", "amazon", "youtube"]

    def test_custom_services(self):
        assert self._parse("-s", "qobuz").services == ["qobuz"]

    def test_split_default_false(self):
        assert self._parse().split is False

    def test_split_flag(self):
        assert self._parse("--split").split is True

    def test_default_min_silence_len(self):
        assert self._parse().min_silence_len == 1500

    def test_custom_min_silence_len(self):
        assert self._parse("--min-silence-len", "2000").min_silence_len == 2000

    def test_default_silence_thresh(self):
        assert self._parse().silence_thresh == -50

    def test_custom_silence_thresh(self):
        assert self._parse("--silence-thresh", "-40").silence_thresh == -40

    def test_default_min_track_len(self):
        assert self._parse().min_track_len == 30

    def test_custom_min_track_len(self):
        assert self._parse("--min-track-len", "20").min_track_len == 20

    def test_download_lossless_default_false(self):
        assert self._parse().download_lossless is False

    def test_download_lossless_flag(self):
        assert self._parse("--download-lossless").download_lossless is True

    def test_keep_segments_default_false(self):
        assert self._parse().keep_segments is False

    def test_keep_segments_flag(self):
        assert self._parse("--keep-segments").keep_segments is True

    def test_verbose_default_false(self):
        assert self._parse().verbose is False

    def test_verbose_flag(self):
        assert self._parse("--verbose").verbose is True
