import subprocess
import os
import re
from PySide6.QtCore import QThread, Signal, QTimer
from core.state import GitState

class GitPoller(QThread):
    state_updated = Signal(GitState)

    def __init__(self, repo_path=""):
        super().__init__()
        self.repo_path = repo_path
        self._is_running = True
        self.force_refresh = False

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
            return result.stdout.strip()
        except Exception as e:
            return ""

    def _poll_git(self) -> GitState:
        state = GitState()
        if not self.repo_path or not os.path.exists(self.repo_path):
            return state

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
                abs_path = os.path.normpath(os.path.join(self.repo_path, rel_path))
                
                if code == '!!':
                    status = 'ignored'
                elif code == '??':
                    status = 'untracked'
                elif code[0] in ('M', 'A', 'D', 'R', 'C') and code[1] in (' ', 'M', 'D'):
                    status = 'staged'
                elif code[1] in ('M', 'D'):
                    status = 'unstaged'
                else:
                    status = 'unknown'
                file_statuses[abs_path] = status
        
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

        # Log history with newline to draw connected vertical lines
        log_out = self._run_git(["log", "--all", "--graph", "--color=always", "--pretty=format:%C(auto)%h%C(auto)%d %Creset%s%n", "-n", "1000"])
        state.commitHistory = log_out.split('\n') if log_out else []

        return state
