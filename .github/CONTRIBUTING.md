# Contributing to SyncTree

Thank you for your interest in contributing to SyncTree! We welcome contributions of all forms: bug fixes, feature proposals, UI enhancements, documentation improvements, and localization additions.

---

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md) in all community spaces.

---

## Development Setup

### 1. Prerequisites
- **Git**: Ensure Git is installed and accessible via command line (`git --version`).
- **Python**: Python 3.10 or higher is required.

### 2. Fork and Clone
```bash
git clone https://github.com/<your-username>/SyncTree.git
cd SyncTree
```

### 3. Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-cov flake8
```

### 5. Run Local Tests
SyncTree includes a comprehensive automated test suite. Verify that all tests pass:
```bash
python -m pytest tests -v
```

---

## Engineering Guidelines

- **PEP 8 Compliance**: Follow Python standards. Keep lines clean and logically organized.
- **Qt / PySide6 Threading**:
  - Never execute blocking commands (network fetching, heavy operations) directly in the Qt GUI main thread.
  - Coordinate foreground write operations and background polling using `GitRepoLock` to eliminate `.git/index.lock` collisions.
  - Pass subprocess arguments as sanitized lists (`["git", "status"]`); **never** pass raw concatenated shell strings with `shell=True`.
- **Test-Driven**: Every bug fix or new feature must be accompanied by corresponding unit or integration tests in the `tests/` directory.

---

## Commit Message Conventions

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```text
<type>(<scope>): <short description>

[optional detailed body]

[optional footer / issue references]
```

### Allowed Types:
- `feat`: A new user-facing feature.
- `fix`: A bug fix.
- `docs`: Documentation updates.
- `style`: Formatting, missing semicolons, whitespace (no code logic changes).
- `refactor`: Code refactoring that neither fixes a bug nor adds a feature.
- `perf`: Performance optimizations.
- `test`: Adding missing tests or improving existing test suites.
- `ci`: CI/CD workflows and automation scripts.
- `chore`: Dependency updates, auxiliary tooling, or maintenance.

---

## Submitting a Pull Request

1. Create a descriptive feature/fix branch:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```
2. Commit your atomic changes following the commit conventions.
3. Verify that all 28+ unit tests pass:
   ```bash
   python -m pytest tests -v
   ```
4. Push your branch to your fork and submit a PR against `main`.
5. Fill in the [Pull Request Template](PULL_REQUEST_TEMPLATE.md) completely to facilitate code review.
