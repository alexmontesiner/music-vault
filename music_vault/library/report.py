"""Human-readable library health report."""

from __future__ import annotations

from music_vault.library.scanner import Track

_ISSUE_LABELS: dict[str, str] = {
    "missing_title":    "Missing title",
    "missing_artist":   "Missing artist",
    "missing_album":    "Missing album",
    "missing_year":     "Missing year",
    "missing_genre":    "Missing genre",
    "missing_cover":    "No cover art",
    "filename_mismatch":"Filename mismatch",
    "duplicate":        "Duplicate",
    "lossy_redundant":  "Lossy (lossless exists)",
}

_WIDTH = 70


def print_report(tracks: list[Track]) -> None:
    """Print a full library health report to stdout."""
    healthy   = [t for t in tracks if not t.issues]
    unhealthy = [t for t in tracks if t.issues]

    print("═" * _WIDTH)
    print(f"  Library scan  ·  {len(tracks)} track(s) found")
    print("═" * _WIDTH)

    if not tracks:
        print("  No audio files found.")
        print("═" * _WIDTH)
        return

    if unhealthy:
        print()
        for track in unhealthy:
            print(f"  {track.path.name}")
            for issue in track.issues:
                print(f"    [x] {_ISSUE_LABELS.get(issue, issue)}")
        print()

    print(f"  Healthy   : {len(healthy)}")
    print(f"  Issues    : {len(unhealthy)}")

    freq: dict[str, int] = {}
    for t in unhealthy:
        for issue in t.issues:
            freq[issue] = freq.get(issue, 0) + 1

    if freq:
        print()
        print("  Issue breakdown:")
        for issue, count in sorted(freq.items(), key=lambda x: -x[1]):
            label = _ISSUE_LABELS.get(issue, issue)
            print(f"    {label:<28} {count:>4}")

    print("═" * _WIDTH)
