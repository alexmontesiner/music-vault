"""Low-level SpotiFLAC invocation helper, shared by the download and identify pipelines."""

from __future__ import annotations


def download_url(
    url: str,
    output: str,
    services: list[str],
    quality: str,
    lyrics: bool = True,
    verbose: bool = False,
) -> None:
    """Invoke SpotiFLAC to download *url*.

    Raises any exception produced by SpotiFLAC — callers are responsible for
    deciding how to handle errors (sys.exit, log and continue, etc.).
    """
    from spotiflac import SpotiFLAC  # type: ignore

    SpotiFLAC(
        url=url,
        output=output,
        services=services,
        quality=quality,
        lyrics=lyrics,
        verbose=verbose,
    ).download()
