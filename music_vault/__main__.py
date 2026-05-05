"""Entry point for the music-vault CLI (used by the installed console script)."""

from __future__ import annotations

import sys


def main() -> None:
    # Convenience: allow passing a bare Spotify URL without typing the 'download' subcommand
    if len(sys.argv) > 1 and "spotify.com" in sys.argv[1] and sys.argv[1] != "download":
        sys.argv.insert(1, "download")

    from music_vault.cli.parser import build_parser
    from music_vault.cli.download_cmd import cmd_download
    from music_vault.cli.identify_cmd import cmd_identify
    from music_vault.cli.library_cmd import cmd_library

    parser = build_parser()
    args   = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "identify":
        cmd_identify(args)
    elif args.command == "library":
        cmd_library(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
