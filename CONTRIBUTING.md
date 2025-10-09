# Contributing to Myring Profile Explorer

Thanks for your interest in improving the project! This document summarises how to build, test, and
submit changes so that reviews stay fast and friendly.

## Getting Started

1. Fork the repository on GitHub and clone your fork.
2. Create a virtual environment (or reuse the bundled `.venv`) and install the dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Run the application locally to verify your setup:
   ```powershell
   python -m src.app.main
   ```

## Branching & Commits

- Use short-lived feature branches named `feature/<topic>` or `fix/<issue>`.
- Keep commits focused. If you need to reorganise history, prefer `git rebase -i` before pushing.
- Reference GitHub issues in your commit message or PR body using `Fixes #123` when applicable.

## Code Style

- Follow PEP 8 and Python typing best practices.
- Keep numerical logic inside `src/app/core/` where possible; maintain a thin UI layer.
- Add docstrings or inline comments when behaviour is non-obvious, especially around the solver.
- Use ASCII characters in source files unless Unicode is essential.

## Testing

The project ships with a placeholder `pytest` suite. Before opening a PR:

```powershell
python -m pytest
```

Add regression tests alongside new features or bug fixes. Prefer deterministic tests that do not
depend on GUI interaction; numerical modules are straightforward to cover.

## UI Changes

- Include screenshots or short clips in the PR description when visual output changes.
- Update `README.md` if the workflow or setup instructions change.
- Ensure legends, scaling sliders, and defaults behave gracefully for a wide parameter range.

## Documentation

- Update `CHANGELOG.md` with a short entry under the “Unreleased” heading.
- Mention new dependencies or tooling in the README and `requirements.txt`.
- If you add CLI hooks, document them in a new “Command-line Usage” section.

## Pull Requests

1. Rebase your branch on the latest `main`.
2. Run tests and linting (if applicable).
3. Push and open a PR. Provide:
   - Summary of changes
   - Testing performed
   - Screenshots (if UI updates)
4. Address review feedback promptly; feel free to start a discussion if major changes are suggested.

Thanks again for contributing! If you have questions or want feedback before implementing a large
feature, open a draft PR or start an issue for brainstorming.
