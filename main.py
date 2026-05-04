"""Entry point for the Spotify Downloader CLI.

All application logic lives in the ``music_vault`` package.
Run:  python main.py <subcommand> [options]
"""

from __future__ import annotations

import sys


def main() -> None:
    # Backward compat: bare Spotify URL without subcommand → treat as 'download'
    if len(sys.argv) > 1 and "spotify.com" in sys.argv[1] and sys.argv[1] != "download":
        sys.argv.insert(1, "download")

    from music_vault.cli.parser import build_parser
    from music_vault.cli.download_cmd import cmd_download
    from music_vault.cli.identify_cmd import cmd_identify

    parser = build_parser()
    args   = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "identify":
        cmd_identify(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
