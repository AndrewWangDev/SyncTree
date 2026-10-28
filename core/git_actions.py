import webbrowser
import re
import subprocess
import os
from PySide6.QtCore import QThread, Signal
from core.git_utils import GitPoller, GitRepoLock

class GitActions:
    def __init__(self, poller: GitPoller):
        self.poller = poller

    def run_cmd(self, args, get_stderr=False):
        repo_path = self.poller.repo_path
        if not repo_path or not os.path.exists(repo_path):
            return None, "No repo"

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        # 获取全局仓库锁，排他执行前台命令
        GitRepoLock.lock()
        try:
            result = subprocess.run(
                ["git", "--no-pager"] + args,
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
            )
            self.poller.trigger_update()
            if result.returncode != 0:
                err_msg = result.stderr.strip() if result.stderr.strip() else result.stdout.strip()
                return None, err_msg
                
            if get_stderr:
                return result.stdout.strip(), result.stderr.strip()
            return result.stdout.strip(), None
        except Exception as e:
            return None, str(e)
        finally:
            GitRepoLock.unlock()

    def init_repo(self):
        return self.run_cmd(["init"])

    def get_remotes(self):
        out, err = self.run_cmd(["remote"])
        if err or not out:
            return []
        return [r.strip() for r in out.splitlines() if r.strip()]

    def set_remote(self, url, remote_name="origin"):
        url = url.strip() if url else ""
        remotes = self.get_remotes()
        has_remote = remote_name in remotes

        if not url:
            if has_remote:
                return self.run_cmd(["remote", "remove", remote_name])
            return "", None

        if has_remote:
            return self.run_cmd(["remote", "set-url", remote_name, url])
        else:
            return self.run_cmd(["remote", "add", remote_name, url])

    def sync_latest(self, branch=None):
        if not branch:
            upstream, err = self.run_cmd(["rev-parse", "--abbrev-ref", "@{upstream}"])
            if upstream and not err:
                parts = upstream.split("/", 1)
                if len(parts) == 2:
                    return self.run_cmd(["pull", parts[0], parts[1]])
            current, _ = self.run_cmd(["branch", "--show-current"])
            branch = current if current else "main"
            
        remotes = self.get_remotes()
        remote_name = "origin" if "origin" in remotes else (remotes[0] if remotes else "origin")
        return self.run_cmd(["pull", remote_name, branch])

    def create_branch(self, name, commit_hash=None):
        if commit_hash:
            return self.run_cmd(["checkout", "-b", name, commit_hash])
        return self.run_cmd(["checkout", "-b", name])

    def is_valid_branch_name(self, name):
        if not name or not name.strip():
            return False, "Branch name cannot be empty"
        out, err = self.run_cmd(["check-ref-format", "--branch", name])
        if err:
            return False, f"Invalid branch name: {name}\n(No spaces, no '..', no special symbols like ~^:?*)"
        return True, None

    def switch_branch(self, name):
        return self.run_cmd(["checkout", name])

    def stage_all(self):
        return self.run_cmd(["add", "."])

    def unstage_all(self):
        check, _ = self.run_cmd(["rev-parse", "--verify", "HEAD"])
        if check is None:
            return self.run_cmd(["rm", "--cached", "-r", "."])
        return self.run_cmd(["reset", "--mixed", "HEAD"])

    def commit(self, msg):
        return self.run_cmd(["commit", "-m", msg])

    def undo_commit(self):
        check, _ = self.run_cmd(["rev-parse", "--verify", "HEAD~1"])
        if check is None:
            return self.run_cmd(["update-ref", "-d", "HEAD"])
        return self.run_cmd(["reset", "--soft", "HEAD^"])

    def push(self, branch):
        remotes = self.get_remotes()
        remote_name = "origin" if "origin" in remotes else (remotes[0] if remotes else "origin")
        out, err = self.run_cmd(["push", "-u", remote_name, branch], get_stderr=True)
        if out is None:
            return None, err
        output = (out or "") + "\n" + (err or "")
        match = re.search(r'https?://[^\s]+/(?:pull/new|merge_requests/new)[^\s]*', output)
        if match:
            url = re.sub(r'[.,);"\']+$', '', match.group(0))
            try:
                webbrowser.open(url)
            except Exception:
                pass
        return out, None

    def diff_file(self, file_path, staged=False):
        args = ["diff"]
        if staged:
            args.append("--cached")
        args.append("--")
        args.append(file_path)
        return self.run_cmd(args)

    def preview_cleanup(self):
        """预览将被清理的文件（dry-run）"""
        return self.run_cmd(["clean", "-fd", "--dry-run"])

    def cleanup_garbage(self):
        out1, err1 = self.run_cmd(["clean", "-fd"])
        out2, err2 = self.run_cmd(["gc"])
        res_out = ((out1 or "") + "\n" + (out2 or "")).strip()
        res_err = (err1 or "") if err1 else (err2 or None)
        return res_out, res_err

class CleanupThread(QThread):
    finished = Signal(str, str) # result_msg, error_msg

    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.actions = actions

    def run(self):
        out, err = self.actions.cleanup_garbage()
        self.finished.emit(out or "", err or "")
