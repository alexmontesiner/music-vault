"""Thin shim for direct execution: python main.py <subcommand> [options]

Prefer using the installed console script after `pip install -e .`:
    music-vault <subcommand> [options]
"""

from music_vault.__main__ import main

if __name__ == "__main__":
    main()
