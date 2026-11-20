# Changelog

All notable changes to the **SyncTree** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-11-20

### 🚀 Major Architectural Hardening & Open Source Release

This milestone marks a major transformation of SyncTree into a production-grade, secure, and beginner-friendly Git graphical desktop client with robust engineering standards, automated CI/CD pipelines, and comprehensive multi-platform support.

#### 🛡️ Security Hardening (安全与应用防护)
- **Executable Blocking Expansion**: Expanded double-click blacklist to 24 dangerous extension types (`.exe`, `.com`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.vbe`, `.js`, `.jse`, `.wsf`, `.wsh`, `.hta`, `.cpl`, `.msi`, `.msp`, `.lnk`, `.url`, `.reg`, `.jar`, `.scf`, `.settingcontent-ms`, `.desktop`, `.scr`, `.pif`) to prevent accidental native code execution.
- **SSH Diagnostic Hardening**: Enforced `StrictHostKeyChecking=yes` in network diagnostics to avoid unwanted modification of the user's global `known_hosts` file.
- **Anti-Phishing PR URL Sniffer**: Stripped ANSI escape terminal sequences before scanning Pull Request / Merge Request URLs and added strict domain whitelisting (`github.com`, `gitlab.com`, `gitee.com`, or configured remote host).
- **Command Argument Injection Defense**: Added explicit `"--"` delimiters in `git mv` and `git clone` invocations to prevent path parameters from being misinterpreted as CLI flags.
- **Credential Masking & Smart Edit**: Masked sensitive embedded tokens in remote repository URLs (`https://***@...`) with smart credential preservation when editing repository targets.
- **Directory Traversal & Symlink Guards**: Standardized path validation using `os.path.realpath` and `os.path.normcase` across file delete and rename operations.

#### ⚡ Concurrency & Lifecycle (并发控制与生命周期管理)
- **Asynchronous Sync & Push**: Decoupled `sync_latest` (pull) and `push` from the main UI thread into a dedicated `GitTaskThread`, eliminating UI freezing during slow or high-latency network calls.
- **Subprocess Non-Interactive Isolation**: Injected `stdin=subprocess.DEVNULL`, `GIT_TERMINAL_PROMPT="0"`, and `GIT_PAGER="cat"` with 60-second timeouts across all Git CLI commands to eliminate credential popup deadlocks.
- **Graceful Thread Cancellation**: Enhanced `GitTaskThread` to track active child process handles, safely terminating background processes and disconnecting signals during `MainWindow.closeEvent` to eliminate teardown segmentation faults.
- **Repository Switch Concurrency Guard**: Disabled repository switching while asynchronous sync/push operations are in-flight and anchored the target repository path for the duration of the task.
- **Weak Reference Signal Architecture**: Decoupled `LanguageManager` into a pure Python Observer using `weakref.WeakMethod`, allowing Qt window instances to be properly garbage collected.
- **Dangling Pointer Prevention**: Safely unset the file tree model (`setModel(None)`) before destroying the underlying model during window close events.

#### 🌿 Git Flow & State Machine (Git 状态机与工作流)
- **Merge Conflict Recovery**: Added native support for `git merge --abort` with a dedicated, context-sensitive "Abort Merge" UI button.
- **Intelligent Push Error Routing**: Categorized push failure outputs to clearly distinguish between non-fast-forward conflicts (fetch/pull needed), authentication failures, and network timeouts.
- **Safe Working Tree Cleanup**: Resurrected repository garbage cleanup (`git clean -df`) with an interactive dry-run preview modal.
- **Robust Status Porcelain Parsing**: Resolved filename parsing edge cases, restricting arrow splitting (`" -> "`) strictly to rename/copy statuses (`R`, `C`) and preserving filenames containing arrows.
- **Cross-Platform Case Normalization**: Implemented `normalize_repo_path` to handle Windows/macOS case-insensitivity while strictly preserving Linux casing.
- **Worktree & Submodule Support**: Resolved the physical Git directory via `git rev-parse --git-dir` for multi-worktree repositories.

#### 🏛️ Governance & CI/CD (开源治理与工程规范)
- **GPL-2.0 License**: Formally adopted the GNU General Public License v2.0.
- **Community Standards**: Completed `.github/` suite including `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `PULL_REQUEST_TEMPLATE.md`, and structured YAML issue templates.
- **Cross-Platform CI Matrix**: Built full GitHub Actions automated test matrix across Ubuntu (with Xvfb), Windows, and macOS on Python 3.10, 3.11, and 3.12.
- **CodeQL Advanced Security Analysis**: Integrated automated AST security scanning and static analysis.
- **Test Suite Expansion**: Comprehensive test suite expanded to 43 automated unit and integration tests with 100% passing rate.
- **Git History Purification**: Purged all historical `.pyc`, `__pycache__`, and temporary binary assets using `git-filter-repo`.

---

## [1.2.0-beta] - 2026-08-11
- Expanded interface documentation and preview graphic assets in `README.md`.
- Refined window dimensions and dark theme contrast.

## [1.1.0-beta] - 2026-07-28
- Updated brand visual assets and high-resolution logo iconography (`logo.png`, `logo.ico`).
- Added color-coded Git graph rendering with ANSI escape code interpretation.

## [1.0.0-beta] - 2026-03-19
- Initial beta release of SyncTree.
- Core Git operations: Stage, Unstage, Commit, Undo, Branch, History, Sync, Push.
- PySide6 Material You dark theme interface with custom modal overlays and toast notifications.
