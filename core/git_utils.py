import subprocess
import os
import sys
import re
from PySide6.QtCore import QThread, Signal, QFileSystemWatcher, QMutex, QMutexLocker
from core.state import GitState

class GitRepoLock:
    """全局仓库级互斥锁，协调前台写操作与后台轮询，防止 .git/index.lock 并发冲突"""
    _mutex = QMutex()
    _locked = False

    @classmethod
    def lock(cls):
        cls._mutex.lock()
        cls._locked = True

    @classmethod
    def unlock(cls):
        cls._locked = False
        cls._mutex.unlock()

    @classmethod
    def try_lock(cls) -> bool:
        success = cls._mutex.tryLock()
        if success:
            cls._locked = True
        return success

    @classmethod
    def is_locked(cls) -> bool:
        return cls._locked

def normalize_repo_path(path: str) -> str:
    """统一转换为正斜杠；在 Windows 与 macOS（默认不区分大小写）折叠小写，在 Linux 下保留原始大小写"""
    if not path:
        return ""
    real = os.path.realpath(path).replace('\\', '/')
    if os.name == 'nt' or sys.platform == 'darwin':
        return real.lower()
    return real

class GitPoller(QThread):
    state_updated = Signal(GitState)
    _update_watcher_paths = Signal(list)
    _clear_watcher_paths = Signal()

    def __init__(self, repo_path=""):
        super().__init__()
        self.repo_path = repo_path
        self._is_running = True
        self._refresh_mutex = QMutex()
        self._force_refresh = False
        self.current_state = GitState()
        self._last_head_hash = None
        self._last_branch = None

        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(lambda _: self.trigger_update())
        self.watcher.fileChanged.connect(lambda _: self.trigger_update())
        self._update_watcher_paths.connect(self._do_update_watcher)
        self._clear_watcher_paths.connect(self._do_clear_watcher)

    @property
    def force_refresh(self) -> bool:
        with QMutexLocker(self._refresh_mutex):
            return self._force_refresh

    @force_refresh.setter
    def force_refresh(self, val: bool):
        with QMutexLocker(self._refresh_mutex):
            self._force_refresh = val

    def _do_update_watcher(self, paths):
        if not paths:
            return
        existing = set(self.watcher.directories() + self.watcher.files())
        to_add = [p for p in paths if os.path.exists(p) and p not in existing]
        if to_add:
            try:
                self.watcher.addPaths(to_add)
            except Exception:
                pass

    def _do_clear_watcher(self):
        old_paths = self.watcher.directories() + self.watcher.files()
        if old_paths:
            try:
                self.watcher.removePaths(old_paths)
            except Exception:
                pass

    def reset_watcher(self):
        """切换仓库时清空所有旧的监听句柄"""
        self._clear_watcher_paths.emit()

    def run(self):
        while self._is_running:
            state = self._poll_git()
            self.state_updated.emit(state)
            
            # 空闲时等待约 2.5 秒，若 force_refresh 则立即打断进入下一轮
            wait_cycles = 10 if self.force_refresh else 25
            for _ in range(wait_cycles):
                if not self._is_running or self.force_refresh:
                    break
                self.msleep(100)

    def trigger_update(self):
        self.force_refresh = True

    def stop(self):
        self._is_running = False

    def _run_git(self, args, timeout=15):
        if not self.repo_path or not os.path.exists(self.repo_path):
            return ""
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_PAGER"] = "cat"

        try:
            result = subprocess.run(
                ["git", "--no-pager"] + args,
                cwd=self.repo_path,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                timeout=timeout,
                startupinfo=startupinfo
            )
            return result.stdout.rstrip()
        except Exception:
            return ""

    def _poll_git(self) -> GitState:
        # 尝试获取仓库锁，若前台正在进行写操作（commit/add/checkout等），则跳过本轮轮询
        if not GitRepoLock.try_lock():
            return self.current_state

        try:
            state = GitState()
            if not self.repo_path or not os.path.exists(self.repo_path):
                return state

            # 跨线程安全发射 watcher 需要监听的路径（支持普通 .git 目录、Worktree 及 Submodule）
            watch_paths = [self.repo_path]
            git_dir_raw = self._run_git(["rev-parse", "--git-dir"])
            if git_dir_raw:
                real_git_dir = os.path.realpath(
                    os.path.join(self.repo_path, git_dir_raw) if not os.path.isabs(git_dir_raw) else git_dir_raw
                )
                if os.path.exists(real_git_dir):
                    watch_paths.append(real_git_dir)
                    for sub in ["index", "HEAD"]:
                        p = os.path.join(real_git_dir, sub)
                        if os.path.exists(p):
                            watch_paths.append(p)
            self._update_watcher_paths.emit(watch_paths)

            # 检查是否在 git 工作区
            is_repo = self._run_git(["rev-parse", "--is-inside-work-tree"])
            if is_repo != "true":
                self._last_head_hash = None
                self._last_branch = None
                return state
            
            state.isRepo = True

            # 检查当前分支
            state.currentBranch = self._run_git(["branch", "--show-current"])

            # 检查文件改动状态
            status_out = self._run_git(["-c", "core.quotepath=false", "status", "--porcelain"])
            file_statuses = {}
            dir_priority_map = {}
            priority_val = {'conflicted': 4, 'unstaged': 3, 'staged': 2, 'untracked': 1}
            conflict_codes = {'DD', 'AU', 'UD', 'UA', 'DU', 'AA', 'UU'}

            repo_real = normalize_repo_path(self.repo_path)

            if status_out:
                for line in status_out.splitlines():
                    if len(line) < 2:
                        continue
                    code = line[0:2]
                    raw_path = line[3:].strip()
                    # 仅在明确为重命名或拷贝状态时提取新文件路径，避免普通带箭头文件名被截断
                    if code[0] in ('R', 'C') and " -> " in raw_path:
                        if raw_path.startswith('"'):
                            end_quote = raw_path.find('"', 1)
                            if end_quote != -1 and raw_path[end_quote:].startswith('" -> '):
                                rel_path = raw_path[end_quote + 5:].strip().strip('"')
                            else:
                                parts = raw_path.split(" -> ", 1)
                                rel_path = parts[1].strip().strip('"') if len(parts) > 1 else raw_path
                        else:
                            parts = raw_path.split(" -> ", 1)
                            rel_path = parts[1].strip().strip('"') if len(parts) > 1 else raw_path
                    else:
                        rel_path = raw_path.strip().strip('"')
                    
                    abs_path = normalize_repo_path(os.path.join(self.repo_path, rel_path))
                    rel_key = rel_path.replace('\\', '/').strip('/')
                    if os.name == 'nt' or sys.platform == 'darwin':
                        rel_key = rel_key.lower()

                    # 1. 冲突状态判定
                    if code in conflict_codes:
                        state.hasConflict = True
                        state.hasModified = True
                        state.conflictFiles.append(rel_path)
                        status = 'conflicted'
                    # 2. 未跟踪判定 (必须在工作区修改检查前判定，避免 '?' 误判)
                    elif code == '??':
                        state.hasModified = True
                        status = 'untracked'
                    # 3. 忽略文件
                    elif code == '!!':
                        status = 'ignored'
                    # 4. 暂存与未暂存判定
                    elif code[0] in ('M', 'A', 'D', 'R', 'C'):
                        state.hasStaged = True
                        if code[1] in ('M', 'D'):
                            state.hasModified = True
                        status = 'staged' if code[1] not in ('M', 'D') else 'unstaged'
                    elif code[1] in ('M', 'D'):
                        state.hasModified = True
                        status = 'unstaged'
                    else:
                        status = 'unknown'
                    
                    file_statuses[abs_path] = status
                    file_statuses[rel_key] = status

                    # 预计算目录冒泡状态（向上递归计算父级目录冒泡）
                    p_val = priority_val.get(status, 0)
                    if p_val > 0:
                        curr = abs_path
                        while len(curr) > len(repo_real):
                            curr = normalize_repo_path(os.path.dirname(curr))
                            if curr not in dir_priority_map or p_val > dir_priority_map[curr][0]:
                                dir_priority_map[curr] = (p_val, status)
            
            state.fileStatuses = file_statuses
            state.dirStatuses = {d: val[1] for d, val in dir_priority_map.items()}

            # 检查 HEAD commit
            head_hash = self._run_git(["rev-parse", "--verify", "HEAD"])
            need_heavy_refresh = (
                self.force_refresh or
                head_hash != self._last_head_hash or
                state.currentBranch != self._last_branch or
                not self.current_state.commitHistory
            )

            # 跟踪与超前提交检查
            ahead = self._run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"])
            if ahead:
                parts = ahead.split()
                if len(parts) >= 1 and parts[0].isdigit():
                    state.commitsAhead = int(parts[0])
                state.hasUpstream = True
            else:
                state.commitsAhead = 0
                state.hasUpstream = False

            # Can undo：只要存在有效 HEAD（哪怕是第 1 个提交），就支持撤销
            state.canUndo = bool(head_hash)

            if need_heavy_refresh:
                self._last_head_hash = head_hash
                self._last_branch = state.currentBranch

                # 分支列表
                branches_out = self._run_git(["branch", "--format=%(refname:short)"])
                state.branches = [b.strip() for b in branches_out.splitlines() if b.strip()] if branches_out else []

                # 提交历史（限制到 200 条以兼顾性能与展示）
                log_out = self._run_git(["log", "--all", "--graph", "--color=always", "--pretty=format:%C(auto)%h%C(auto)%d %Creset%s%n", "-n", "200"])
                state.commitHistory = log_out.splitlines() if log_out else []
            else:
                state.branches = self.current_state.branches
                state.commitHistory = self.current_state.commitHistory

            self.force_refresh = False
            self.current_state = state
            return state
        finally:
            GitRepoLock.unlock()
