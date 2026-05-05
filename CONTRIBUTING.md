# Contributing to music-vault

Thanks for taking the time to contribute!

## Getting Started

1. Fork the repository and clone your fork:
   ```bash
   git clone https://github.com/<your-username>/music-vault.git
   cd music-vault
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install mutagen pydub shazamio static-ffmpeg pytest
   ```

3. Create a branch for your change:
   ```bash
   git checkout -b feat/your-feature-name
   ```

## Running Tests

The test suite uses [pytest](https://pytest.org) and requires no external services — all network calls are mocked.

```bash
python3 -m pytest tests/ -v
```

All 293 tests should pass before you open a pull request. If you add new functionality, add corresponding tests.

## Code Style

- Follow the conventions already present in the module you are editing.
- Keep modules single-responsibility — see the existing separation between `recognizer`, `splitter`, `processor`, and `spotify_search` for reference.
- Use `from __future__ import annotations` at the top of every new module.
- Prefer keyword-only arguments (`*` separator) for functions with more than three parameters.
- Do not commit secrets, credentials, or personal API keys.

## Submitting a Pull Request

1. Make sure all tests pass and no new linting errors are introduced.
2. Write a clear PR description explaining *what* changed and *why*.
3. Keep commits focused — one logical change per commit.
4. Reference any related issues in the PR description (e.g., `Closes #12`).

## Reporting Issues

Open a GitHub issue with:
- A clear description of the problem.
- Steps to reproduce.
- The output of `python main.py --help` and any error messages.
- Your Python version (`python3 --version`).
