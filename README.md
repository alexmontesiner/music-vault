# music-vault

A command-line tool for downloading Spotify playlists and tracks in lossless quality, identifying audio files via Shazam, and maintaining a healthy local music library.

## Features

- **Download** – Fetch any Spotify track or playlist in lossless (FLAC) or hi-res quality via Qobuz, Amazon Music, and YouTube. Optionally embed lyrics and skip already-downloaded tracks.
- **Identify** – Run Shazam recognition against any audio file. Supports full vinyl-side rips: automatically splits on silence, identifies each track, and embeds metadata.
- **Library** – Scan your local library, detect health issues (missing tags, missing cover art, duplicate tracks, redundant lossy copies), and auto-fix filename mismatches.

## Requirements

- Python 3.11+
- [SpotiFLAC](https://pypi.org/project/spotiflac/) – lossless download back-end
- [shazamio](https://github.com/dotX12/ShazamIO) – async Shazam client
- [mutagen](https://mutagen.readthedocs.io/) – audio tag reading/writing
- [pydub](https://github.com/jiaaro/pydub) – audio segment splitting
- [static-ffmpeg](https://pypi.org/project/static-ffmpeg/) *(optional)* – bundled ffmpeg, no system install needed

## Installation

```bash
git clone https://github.com/alexmontesiner/music-vault.git
cd music-vault
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

This installs a `music-vault` console script into the venv. You can now run `music-vault` directly instead of `python main.py`.

## Usage

### Download

```bash
# Download a Spotify playlist in FLAC (default)
music-vault download "https://open.spotify.com/playlist/..."

# Hi-res quality, custom output directory
music-vault download "https://open.spotify.com/album/..." -q hi-res -o ~/Music/albums

# Skip already-downloaded tracks and print a summary of new additions
music-vault download "https://open.spotify.com/playlist/..." --update

# Pass a bare Spotify URL — the download subcommand is inferred automatically
music-vault "https://open.spotify.com/track/..."
```

**Options**

| Flag | Default | Description |
|---|---|---|
| `url` | — | Spotify playlist or track URL |
| `-o / --output` | `downloads/spotify` | Output directory |
| `-q / --quality` | `flac` | `flac` or `hi-res` |
| `-s / --services` | `qobuz amazon youtube` | Providers to try in order |
| `--lyrics` | on | Embed lyrics when available |
| `--update` | off | Skip existing tracks, report new ones |
| `--verbose` | off | Show SpotiFLAC debug output |

---

### Identify

```bash
# Identify a single file and embed metadata
music-vault identify recording.mp3

# Identify a vinyl-side rip: split on silence, identify each track
music-vault identify side_a.flac --split

# Identify and download a lossless version for each recognised track
music-vault identify side_a.flac --split --download-lossless

# Tune the silence detection for a noisy recording
music-vault identify side_a.flac --split --min-silence-len 2000 --silence-thresh -45
```

**Options**

| Flag | Default | Description |
|---|---|---|
| `input` | — | Audio file to identify |
| `-o / --output` | `downloads/identified` | Output directory |
| `--split` | off | Split vinyl side on silence before identifying |
| `--min-silence-len` | `1500` ms | Minimum silence length for splitting |
| `--silence-thresh` | `-50` dBFS | Silence threshold for splitting |
| `--min-track-len` | `30` s | Ignore segments shorter than this |
| `--download-lossless` | off | Search Spotify and download lossless version |
| `--keep-segments` | off | Keep split segments even after lossless download |
| `-s / --services` | `qobuz amazon youtube` | Providers used by `--download-lossless` |
| `--verbose` | off | Enable verbose output |

---

### Library

```bash
# Scan the default downloads/ directory and print a health report
music-vault library

# Scan a custom directory
music-vault library --path ~/Music

# Preview what would be renamed (dry run)
music-vault library --path ~/Music --dry-run

# Actually rename files whose names don't match their tags
music-vault library --path ~/Music --fix
```

**Options**

| Flag | Default | Description |
|---|---|---|
| `--path` | `downloads` | Root directory of your music library |
| `--fix` | off | Rename files to match `{title} - {artist}` tags |
| `--dry-run` | off | Show what `--fix` would rename without changing anything |

**Health checks**

| Issue | Description |
|---|---|
| `missing_title/artist/album/year/genre` | Required tag is empty |
| `missing_cover` | No embedded cover art |
| `filename_mismatch` | File name doesn't match `{title} - {artist}` (fixable with `--fix`) |
| `duplicate` | Another file with the same artist + title exists |
| `lossy_redundant` | A lossless version of this track already exists |

## Project Structure

```
music-vault/
├── main.py                   # Entry point
├── music_vault/
│   ├── cli/                  # Argument parsing and subcommand handlers
│   │   ├── parser.py
│   │   ├── download_cmd.py
│   │   ├── identify_cmd.py
│   │   └── library_cmd.py
│   ├── core/                 # Shared utilities and metadata embedding
│   │   ├── utils.py
│   │   └── metadata.py
│   ├── download/             # SpotiFLAC download wrapper
│   │   └── spotiflac.py
│   ├── identify/             # Shazam recognition pipeline
│   │   ├── recognizer.py
│   │   ├── splitter.py
│   │   ├── spotify_search.py
│   │   └── processor.py
│   └── library/              # Local library scanner and health checks
│       ├── scanner.py
│       ├── health.py
│       ├── fixer.py
│       └── report.py
└── tests/                    # pytest test suite (293 tests)
```

## Running Tests

```bash
pip install pytest
python3 -m pytest tests/ -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
