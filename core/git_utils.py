import subprocess
import os
import re
from PySide6.QtCore import QThread, Signal, QTimer, QFileSystemWatcher
from core.state import GitState

class GitPoller(QThread):
    state_updated = Signal(GitState)

    def __init__(self, repo_path=""):
        super().__init__()
        self._is_running = True
        self.force_refresh = False
        self.current_state = GitState()
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(lambda _: self.trigger_update())
        self.watcher.fileChanged.connect(lambda _: self.trigger_update())

    def run(self):
        while self._is_running:
            state = self._poll_git()
            self.state_updated.emit(state)
            
            # Simple wait loop to allow interrupting via force_refresh or stop
            for _ in range(10): 
                if not self._is_running or self.force_refresh:
                    break
                self.msleep(100)
            self.force_refresh = False

    def trigger_update(self):
        self.force_refresh = True

    def stop(self):
        self._is_running = False

    def _run_git(self, args):
        if not self.repo_path or not os.path.exists(self.repo_path):
            return ""
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            result = subprocess.run(
                ["git", "--no-pager"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
            )
            return result.stdout.rstrip()
        except Exception as e:
            return ""

    def _poll_git(self) -> GitState:
        state = GitState()
        if not self.repo_path or not os.path.exists(self.repo_path):
            return state

        # Refresh watcher if path changed or not set
        watch_paths = [self.repo_path]
        git_path = os.path.join(self.repo_path, ".git")
        if os.path.exists(git_path):
            watch_paths.append(git_path)
            # Also watch index and HEAD for common ops
            for sub in ["index", "HEAD"]:
                p = os.path.join(git_path, sub)
                if os.path.exists(p): watch_paths.append(p)
                
        existing = self.watcher.directories() + self.watcher.files()
        to_add = [p for p in watch_paths if p not in existing]
        if to_add:
            self.watcher.addPaths(to_add)

        # Check if repo
        is_repo = self._run_git(["rev-parse", "--is-inside-work-tree"])
        if is_repo != "true":
            return state
        
        state.isRepo = True

        # Check git status for modified/staged files and precise path status
        status_out = self._run_git(["-c", "core.quotepath=false", "status", "--porcelain", "--ignored"])
        file_statuses = {}
        if status_out:
            for line in status_out.split('\n'):
                if len(line) < 2: continue
                code = line[0:2]
                
                if code[0] in ('M', 'A', 'D', 'R', 'C'):
                    state.hasStaged = True
                if code[1] in ('M', 'D', '?'):
                    state.hasModified = True
                    
                rel_path = line[3:].strip()
                if rel_path.startswith('"') and rel_path.endswith('"'):
                    rel_path = rel_path[1:-1]
                
                # Resolve realpath to handle junctions/symlinks/OneDrive paths
                abs_path = os.path.realpath(os.path.join(self.repo_path, rel_path)).replace('\\', '/').lower()
                
                # Also support a relative key just in case realpath resolution is inconsistent
                rel_key = rel_path.replace('\\', '/').lower().strip('/')
                
                if code[1] in ('M', 'D'):
                    status = 'unstaged'
                elif code[0] in ('M', 'A', 'D', 'R', 'C'):
                    status = 'staged'
                elif code == '??':
                    status = 'untracked'
                elif code == '!!':
                    status = 'ignored'
                else:
                    status = 'unknown'
                
                file_statuses[abs_path] = status
                file_statuses[rel_key] = status
        
        state.fileStatuses = file_statuses

        # Branch
        state.currentBranch = self._run_git(["branch", "--show-current"])
        
        branches_out = self._run_git(["branch", "--format=%(refname:short)"])
        state.branches = [b.strip() for b in branches_out.split('\n') if b.strip()] if branches_out else []

        # Commits ahead
        ahead = self._run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"])
        if ahead:
            parts = ahead.split()
            if len(parts) >= 1 and parts[0].isdigit():
                state.commitsAhead = int(parts[0])
        else:
            state.commitsAhead = 0

        # Can undo (check if HEAD has a parent)
        undo_check = self._run_git(["rev-parse", "--verify", "HEAD^"])
        state.canUndo = bool(undo_check)

        # Log history with newline to draw connected vertical lines
        log_out = self._run_git(["log", "--all", "--graph", "--color=always", "--pretty=format:%C(auto)%h%C(auto)%d %Creset%s%n", "-n", "1000"])
        state.commitHistory = log_out.split('\n') if log_out else []

        self.current_state = state
        return state
