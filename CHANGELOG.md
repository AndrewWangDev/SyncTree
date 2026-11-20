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

#### 🎨 UI & UX Polish (界面体验与布局修复)
- **Input Field Layout & Distortion Fix**: Standardized `QLineEdit` heights (`setFixedHeight(40)`), vertical centering, and column stretch weights in grid layouts, eliminating text clipping and vertical distortion across varying window geometries.
- **Outside-Click Focus Restoration**: Installed an application-wide event filter capturing mouse clicks on non-input areas, immediately clearing `QLineEdit` focus and restoring border styling from active blue highlight to default neutral gray.
- **ComboBox Dropdown Arrow Alignment**: Defined explicit `QComboBox::drop-down` subcontrol sizing (`width: 36px`) and `QComboBox::down-arrow` geometric margins, resolving arrow icon cramping against the right border in modal selection dialogs.
- **Official Release Branding**: Removed `(Beta)` title suffix and top-bar `Beta` pill badge to reflect the official `v2.0.0` general availability release.
- **Search Results List & Contrast Overhaul**: Fixed unintentional ARGB lime-green background parsing bug in list selection by replacing with high-contrast Material dark styling (`rgba(168, 199, 250, 0.18)` background with crisp white text). Introduced `SearchResultDelegate` rendering filename and directory path on two clean visual tiers with middle eliding.
- **Eliminated Unexpected Selection Scrolling**: Disabled `autoScroll` and horizontal scrollbar overflow (`ScrollBarAlwaysOff`), preventing viewport jumping when clicking or navigating search result list items.
- **Context Menu Selection Color Normalization**: Fixed right-click context menu hover/selection color in the file tree from lime-green to consistent translucent primary blue.

#### 🏛️ Governance & CI/CD (开源治理与工程规范)
- **GPL-2.0 License**: Formally adopted the GNU General Public License v2.0.
- **Community Standards**: Completed `.github/` suite including `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `PULL_REQUEST_TEMPLATE.md`, and structured YAML issue templates.
- **Cross-Platform CI Matrix**: Built full GitHub Actions automated test matrix across Ubuntu (with Xvfb), Windows, and macOS on Python 3.10, 3.11, and 3.12.
- **CodeQL Advanced Security Analysis**: Integrated automated AST security scanning and static analysis.
- **Test Suite Expansion**: Comprehensive test suite expanded to 47 automated unit and integration tests with 100% passing rate.
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
