import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

from core.git_actions import GitActions
from core.git_utils import GitPoller, normalize_repo_path
from core.state import GitState
from core.network_diag import EnvDiagThread
from ui.panel_view import PanelView, mask_remote_url
from ui.window import MainWindow

def test_blocked_extensions_expansion():
    """【SEC-01 验证】扩充后的危险扩展名黑名单必须包含 .hta, .reg, .msi, .lnk, .cpl 等"""
    dangerous_exts = ['.hta', '.reg', '.msi', '.msp', '.lnk', '.url', '.cpl', '.jar', '.vbe', '.wsf']
    for ext in dangerous_exts:
        assert ext in MainWindow.BLOCKED_EXTS, f"Extension {ext} must be blocked!"

    window = MainWindow()
    try:
        window.poller.stop()
        window.poller.wait()
        with patch("ui.window.show_result_modal") as mock_modal, \
             patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
            
            with tempfile.NamedTemporaryFile(suffix=".hta", delete=False) as f:
                hta_path = f.name
            with tempfile.NamedTemporaryFile(suffix=".reg", delete=False) as f:
                reg_path = f.name
            try:
                window._safe_open_file(hta_path)
                mock_modal.assert_called_once()
                mock_open.assert_not_called()

                mock_modal.reset_mock()
                window._safe_open_file(reg_path)
                mock_modal.assert_called_once()
                mock_open.assert_not_called()
            finally:
                os.remove(hta_path)
                os.remove(reg_path)
    finally:
        window.close()

def test_ssh_strict_host_key_checking_yes():
    """【SEC-02 验证】SSH 诊断必须使用 StrictHostKeyChecking=yes，禁止 accept-new 的全局已知主机写副作用"""
    diag = EnvDiagThread()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Hi user! You've successfully authenticated", stderr="")
        status, msg = diag.check_ssh()
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "StrictHostKeyChecking=yes" in cmd
        assert "StrictHostKeyChecking=accept-new" not in cmd
        assert status == 1

def test_push_pr_sniffer_ansi_strip_and_domain_whitelist():
    """【SEC-03 验证】Push 嗅探 PR 链接必须剔除尾部 ANSI 序列且校验域名白名单"""
    poller = GitPoller()
    actions = GitActions(poller)

    # 1. 包含 ANSI 控制码的合法 GitHub URL
    raw_output = 'remote: \x1b[32mhttps://github.com/AndrewWangDev/SyncTree/pull/new/feat-1\x1b[0m\n'
    with patch.object(actions, "run_cmd", return_value=(raw_output, None)), \
         patch.object(actions, "get_remotes", return_value=["origin"]), \
         patch("webbrowser.open") as mock_browser:
        
        actions.push("feat-1")
        mock_browser.assert_called_once_with("https://github.com/AndrewWangDev/SyncTree/pull/new/feat-1")

    # 2. 钓鱼/非白名单域名必须被拒绝打开
    phishing_output = 'remote: https://phishing-attacker.com/pull/new/evil\n'
    with patch.object(actions, "run_cmd", return_value=(phishing_output, None)), \
         patch.object(actions, "get_remotes", return_value=["origin"]), \
         patch("webbrowser.open") as mock_browser:
        
        actions.push("feat-1")
        mock_browser.assert_not_called()

def test_remote_url_token_masking():
    """【SEC-05 验证】Remote URL 包含明文 Token/密码时，UI 渲染必须脱敏掩码"""
    token_url = "https://ghp_secretToken12345@github.com/org/repo.git"
    masked = mask_remote_url(token_url)
    assert "ghp_secretToken12345" not in masked
    assert masked == "https://***@github.com/org/repo.git"

    user_pass_url = "https://andrew:password123@gitlab.com/group/project.git"
    masked_pass = mask_remote_url(user_pass_url)
    assert "password123" not in masked_pass
    assert masked_pass == "https://***@gitlab.com/group/project.git"

def test_abort_merge_action_and_ui_button():
    """【DATA-03 验证】冲突状态下展示放弃合并按钮，且底层支持 abort_merge"""
    panel = PanelView()
    conflict_state = GitState(
        isRepo=True,
        hasConflict=True,
        conflictFiles=["conflict.txt"],
        currentBranch="main"
    )
    panel.update_state(conflict_state)

    # 放弃合并按钮必须处于可见且可用状态
    assert panel.btn_abort_merge.isHidden() is False
    assert panel.btn_abort_merge.isEnabled() is True
    assert panel.btn_sync.isEnabled() is False

    # 解决冲突后必须隐藏
    clean_state = GitState(isRepo=True, hasConflict=False, currentBranch="main")
    panel.update_state(clean_state)
    assert panel.btn_abort_merge.isHidden() is True

    # 底层 abort_merge 命令验证
    poller = GitPoller()
    actions = GitActions(poller)
    with patch.object(actions, "run_cmd", return_value=("", None)) as mock_run:
        actions.abort_merge()
        mock_run.assert_called_once_with(["merge", "--abort"])

def test_status_porcelain_non_rename_arrow_and_quoted_parsing():
    """【PARS-01 验证】普通文件含有箭头符号不被截断；重命名含引号路径精确解析"""
    tmp_dir = tempfile.mkdtemp()
    try:
        poller = GitPoller(tmp_dir)
        status_lines = "\n".join([
            "?? notes -> guide.txt", # 未跟踪文件本身含有 " -> "
            'R  "old a -> b.txt" -> "new file.txt"' # 带引号和箭头的重命名
        ])
        with patch.object(poller, "_run_git") as mock_git:
            def side_effect(cmd, timeout=15):
                if "--is-inside-work-tree" in cmd:
                    return "true"
                if "status" in cmd:
                    return status_lines
                if "rev-parse" in cmd:
                    return "hash"
                if "branch" in cmd:
                    return "main"
                return ""
            mock_git.side_effect = side_effect
            state = poller._poll_git()

            # 普通文件必须保留全名 "notes -> guide.txt"
            assert "notes -> guide.txt" in state.fileStatuses
            assert state.fileStatuses["notes -> guide.txt"] == "untracked"

            # 重命名文件必须提取出 "new file.txt"
            assert "new file.txt" in state.fileStatuses
            assert state.fileStatuses["new file.txt"] == "staged"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def test_branch_history_validation():
    """【ENG-03 验证】从历史提交创建分支时必须进行分支名称合法性预校验"""
    window = MainWindow()
    try:
        window.poller.stop()
        window.poller.wait()
        with patch("ui.window.show_result_modal") as mock_modal, \
             patch.object(window.actions, "create_branch") as mock_create:
            
            # 模拟用户在历史弹窗输入非法分支名（如含有连续点号或特殊符号）
            window._handle_panel_action("branch_history", {})
            # 触发历史分支创建函数
            is_valid, msg = window.actions.is_valid_branch_name("invalid..name")
            assert is_valid is False
            assert ".." in msg
    finally:
        window.close()
