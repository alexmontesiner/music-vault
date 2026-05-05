# Contributing to music-vault

Thanks for taking the time to contribute!

## Branch Policy

**Direct pushes to `main` are not allowed.** Every change must go through a pull request.

`@alexmontesiner` is the required reviewer on all PRs (enforced via [CODEOWNERS](.github/CODEOWNERS)). A PR can only be merged once it has been approved.

> To fully enforce this, enable branch protection in the repository settings:
> **Settings → Branches → Add rule** for `main` with *Require a pull request before merging* and *Require review from Code Owners* checked.

## Getting Started

### Collaborators (direct repo access)

1. Clone the repository:
   ```bash
   git clone https://github.com/alexmontesiner/music-vault.git
   cd music-vault
   ```

2. Create a branch for your change:
   ```bash
   git checkout -b feat/your-feature-name
   ```

3. Create a virtual environment and install the package in editable mode:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   pip install pytest
   ```

### External contributors

1. Fork the repository on GitHub, then clone your fork:
   ```bash
   git clone https://github.com/<your-username>/music-vault.git
   cd music-vault
   git remote add upstream https://github.com/alexmontesiner/music-vault.git
   ```

2. Create a branch and install the package as above (steps 2–3 from collaborators).

Once your changes are ready, open a pull request against `main` from your fork.

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
- The output of `music-vault --help` and any error messages.
- Your Python version (`python3 --version`).
