"""Silence-based audio splitter for vinyl side recordings."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


class VinylSplitter:
    """Detect and extract individual track segments from a full vinyl-side recording.

    Detection is based on periods of silence between tracks.  The parameters
    can be tuned via the ``identify --split`` CLI flags.

    Args:
        min_silence_len: Minimum silence duration in milliseconds to treat as a
            track boundary (default 1 500 ms).
        silence_thresh:  Silence threshold in dBFS; anything quieter than this
            value is considered silence (default -50 dBFS).
        min_track_len:   Minimum segment length in *seconds* to keep.  Shorter
            segments (e.g. side noise) are discarded (default 30 s).
        pad_ms:          Milliseconds of padding to add around each segment so
            that hard cuts at boundaries are avoided (default 300 ms).
    """

    def __init__(
        self,
        min_silence_len: int = 1_500,
        silence_thresh:  int = -50,
        min_track_len:   int = 30,
        pad_ms:          int = 300,
    ) -> None:
        self.min_silence_len = min_silence_len
        self.silence_thresh  = silence_thresh
        self.min_track_len   = min_track_len
        self.pad_ms          = pad_ms

    def split(self, audio) -> list:
        """Split *audio* into a list of non-silent segments.

        Returns a list of pydub ``AudioSegment`` objects, one per detected
        track.  Exits with an error message if no valid segments are found.
        """
        from pydub.silence import detect_nonsilent  # type: ignore

        logger.info(
            "Detecting boundaries (thresh=%d dBFS, min_silence=%d ms)…",
            self.silence_thresh, self.min_silence_len,
        )

        non_silent = detect_nonsilent(
            audio,
            min_silence_len=self.min_silence_len,
            silence_thresh=self.silence_thresh,
        )

        if not non_silent:
            print(
                "[!] No non-silent regions detected. "
                "Try raising --silence-thresh (e.g. -40).",
                file=sys.stderr,
            )
            sys.exit(1)

        # Merge regions separated by gaps shorter than min_silence_len
        # (these are likely noise bursts inside a track, not inter-track gaps).
        merged: list[list[int]] = []
        for start, end in non_silent:
            if merged and (start - merged[-1][1]) < self.min_silence_len:
                merged[-1][1] = end
            else:
                merged.append([start, end])

        min_ms   = self.min_track_len * 1_000
        segments_ranges = [(s, e) for s, e in merged if (e - s) >= min_ms]

        if not segments_ranges:
            print(
                f"[!] No segments ≥ {self.min_track_len}s found. "
                f"Try lowering --min-track-len or adjusting --silence-thresh.",
                file=sys.stderr,
            )
            sys.exit(1)

        total_len = len(audio)
        segments  = [
            audio[max(0, s - self.pad_ms): min(total_len, e + self.pad_ms)]
            for s, e in segments_ranges
        ]

        self._print_detected(segments_ranges)
        return segments

    @staticmethod
    def _print_detected(ranges: list[tuple[int, int]]) -> None:
        print(f"[*] Detected {len(ranges)} track segment(s):")
        for i, (s, e) in enumerate(ranges, 1):
            print(
                f"    Track {i:02d}:  {s / 1000:6.1f}s – {e / 1000:6.1f}s  "
                f"({(e - s) / 1000:.1f}s)"
            )
        print()
