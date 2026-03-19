import webbrowser
import re
from core.git_utils import GitPoller

class GitActions:
    def __init__(self, poller: GitPoller):
        self.poller = poller

    def run_cmd(self, args, get_stderr=False):
        # reuse poller's internal git runner but wait for it
        # Actually better to redefine it to capture stderr if needed
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
        branch = self.poller.current_state.currentBranch if self.poller.current_state and self.poller.current_state.currentBranch else "main"
        out, err = self.run_cmd(["checkout", branch])
        if err is not None: return None, err
        return self.run_cmd(["pull", "origin", branch])

    def create_branch(self, name, commit_hash=None):
        if commit_hash:
            return self.run_cmd(["checkout", "-b", name, commit_hash])
        return self.run_cmd(["checkout", "-b", name])

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
