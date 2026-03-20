import webbrowser
import re
from PySide6.QtCore import QThread, Signal
from core.git_utils import GitPoller

class GitActions:
    def __init__(self, poller: GitPoller):
        self.poller = poller

    def run_cmd(self, args, get_stderr=False):
        import subprocess, os
        repo_path = self.poller.repo_path
        if not repo_path or not os.path.exists(repo_path):
            return "", "No repo"

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

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

    def init_repo(self):
        return self.run_cmd(["init"])

    def set_remote(self, url):
        out, err = self.run_cmd(["remote"])
        if err is None and "origin" in out:
            return self.run_cmd(["remote", "set-url", "origin", url])
        else:
            return self.run_cmd(["remote", "add", "origin", url])

    def sync_latest(self):
        # User specified: Remote is always main.
        return self.run_cmd(["pull", "origin", "main"])

    def create_branch(self, name, commit_hash=None):
        if commit_hash:
            return self.run_cmd(["checkout", "-b", name, commit_hash])
        return self.run_cmd(["checkout", "-b", name])

    def is_valid_branch_name(self, name):
        if not name or not name.strip():
            return False, "Branch name cannot be empty"
        # git check-ref-format --branch <name>
        # returns 0 if valid, non-zero if invalid
        out, err = self.run_cmd(["check-ref-format", "--branch", name])
        if err:
            return False, f"Invalid branch name: {name}\n(No spaces, no '..', no special symbols like ~^:?*)"
        return True, None

    def switch_branch(self, name):
        return self.run_cmd(["checkout", name])

    def stage_all(self):
        return self.run_cmd(["add", "."])

    def unstage_all(self):
        return self.run_cmd(["reset", "--mixed", "HEAD"])

    def commit(self, msg):
        return self.run_cmd(["commit", "-m", msg])

    def undo_commit(self):
        return self.run_cmd(["reset", "--soft", "HEAD^"])

    def push(self, branch):
        out, err = self.run_cmd(["push", "-u", "origin", branch], get_stderr=True)
        if out is None:
            return None, err
        # Parse output for PR url
        output = (out or "") + "\n" + (err or "")
        match = re.search(r'https?://[^\s]+/(?:pull/new|merge_requests/new)[^\s]*', output)
        if match:
            url = match.group(0)
            webbrowser.open(url)
        return out, None

    def diff_file(self, file_path, staged=False):
        args = ["diff"]
        if staged:
            args.append("--cached")
        args.append("--")
        args.append(file_path)
        return self.run_cmd(args)

    def cleanup_garbage(self):
        # git clean -fd removes untracked files/directories
        # git gc runs garbage collection
        out1, err1 = self.run_cmd(["clean", "-fd"])
        out2, err2 = self.run_cmd(["gc"])
        return (out1 or "") + (out2 or ""), (err1 or err2)

class CleanupThread(QThread):
    finished = Signal(str, str) # result_msg, error_msg

    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.actions = actions

    def run(self):
        out, err = self.actions.cleanup_garbage()
        self.finished.emit(out, err)
