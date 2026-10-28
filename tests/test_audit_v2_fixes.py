import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from core.state import GitState
from core.git_utils import GitRepoLock
from core.network_diag import EnvDiagThread
from ui.panel_view import PanelView
from ui.window import MainWindow
from ui.components.buttons import MaterialButton
from ui.theme import COLORS

def test_conflict_state_machine():
    """验证当存在代码冲突 (hasConflict=True) 时，面板状态机正确禁用危险按钮并允许暂存/提交"""
    panel = PanelView()
    state = GitState(
        isRepo=True,
        hasModified=True,
        hasStaged=False,
        hasConflict=True,
        conflictFiles=["conflict.txt"],
        currentBranch="main"
    )
    panel.update_state(state)

    assert panel.btn_sync.isEnabled() is False
    assert panel.btn_push.isEnabled() is False
    assert panel.btn_task.isEnabled() is False
    assert panel.btn_history.isEnabled() is False
    assert panel.btn_undo.isEnabled() is False
    assert panel.btn_stage.isEnabled() is True
    assert panel.btn_commit.isEnabled() is False

    # 当解决冲突并暂存后
    state.hasStaged = True
    panel.update_state(state)
    assert panel.btn_stage.isEnabled() is True
    assert panel.btn_unstage.isEnabled() is True
    assert panel.btn_commit.isEnabled() is True
    assert panel.btn_push.isEnabled() is False

def test_executable_files_blocked():
    """验证双击可执行文件或脚本时被安全拦截，不会触发操作系统原生启动"""
    window = MainWindow()
    window.poller.stop()
    window.poller.wait()

    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
        exe_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".bat", delete=False) as f:
        bat_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        txt_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as f:
        js_path = f.name

    try:
        with patch("PySide6.QtGui.QDesktopServices.openUrl") as mock_open:
            with patch("ui.window.show_result_modal") as mock_modal:
                # 尝试打开 .exe
                window._safe_open_file(exe_path)
                mock_open.assert_not_called()
                mock_modal.assert_called_once()
                args, _ = mock_modal.call_args
                assert args[1] is False # is_success is False

                mock_modal.reset_mock()
                # 尝试打开 .bat
                window._safe_open_file(bat_path)
                mock_open.assert_not_called()
                mock_modal.assert_called_once()

                # 打开安全的 .txt
                window._safe_open_file(txt_path)
                mock_open.assert_called_once()

                mock_open.reset_mock()
                # 打开常用源码 .js 文件，不应被拦截误杀
                window._safe_open_file(js_path)
                mock_open.assert_called_once()
    finally:
        os.remove(exe_path)
        os.remove(bat_path)
        os.remove(txt_path)
        os.remove(js_path)

def test_git_repo_lock_mechanism():
    """验证 GitRepoLock 互斥锁机制"""
    # 确保前序测试无残留
    if GitRepoLock.is_locked():
        GitRepoLock.unlock()

    assert GitRepoLock.try_lock() is True
    assert GitRepoLock.is_locked() is True
    # 在持锁状态下非阻塞 try_lock 应返回 False
    assert GitRepoLock.try_lock() is False
    GitRepoLock.unlock()
    assert GitRepoLock.is_locked() is False

def test_network_diag_git_user_both_fields():
    """验证环境诊断必须同时检查 user.name 和 user.email"""
    diag = EnvDiagThread()
    with patch("subprocess.run") as mock_run:
        # 仅配置了 user.name，未配置 user.email
        mock_run.side_effect = [
            MagicMock(stdout="Tester\n"),
            MagicMock(stdout="\n")
        ]
        status, msg = diag.check_git_user()
        assert status == 2 # 失败

        # 两者均配置
        mock_run.side_effect = [
            MagicMock(stdout="Tester\n"),
            MagicMock(stdout="tester@example.com\n")
        ]
        status, msg = diag.check_git_user()
        assert status == 1 # 成功

def test_normcase_and_symlink_deletion_boundary():
    """验证文件删除越界校验支持 Windows 大小写不敏感与符号链接真实路径防护"""
    tmp_dir = tempfile.mkdtemp()
    window = MainWindow()
    window.poller.stop()
    window.poller.wait()

    try:
        window.poller.repo_path = tmp_dir
        outside_file = os.path.join(tempfile.gettempdir(), "outside_test.txt")
        with open(outside_file, "w") as f:
            f.write("sensitive")

        with patch("ui.window.show_result_modal") as mock_modal:
            # 尝试传递外部文件路径
            mock_index = MagicMock()
            window.file_model.filePath = MagicMock(return_value=outside_file)
            window._delete_item(mock_index)
            mock_modal.assert_called_once()
            args, _ = mock_modal.call_args
            assert args[1] is False # cannot_delete_outside
    finally:
        if os.path.exists(outside_file):
            os.remove(outside_file)
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

def test_folder_status_clean_when_other_folders_have_changes():
    """【回归防护】验证当部分目录存在变更时，其他干净的目录仍然显示 'clean' 绿点，不会返回 None 消失"""
    tmp_dir = tempfile.mkdtemp()
    window = MainWindow()
    window.poller.stop()
    window.poller.wait()

    try:
        window.poller.repo_path = tmp_dir
        dir_mod = os.path.join(tmp_dir, "src")
        dir_clean = os.path.join(tmp_dir, "docs")
        os.makedirs(dir_mod, exist_ok=True)
        os.makedirs(dir_clean, exist_ok=True)

        # 模拟 dirStatuses 包含 src 目录的修改
        mod_key = os.path.realpath(dir_mod).replace('\\', '/').lower()
        clean_key = os.path.realpath(dir_clean).replace('\\', '/').lower()

        state = GitState(
            isRepo=True,
            dirStatuses={
                mod_key: "unstaged"
            }
        )
        window.current_state = state

        # src 目录应冒泡为 unstaged
        assert window.file_model.get_status(dir_mod) == "unstaged"
        # docs 目录未改动，必须返回 'clean'，不能返回 None
        assert window.file_model.get_status(dir_clean) == "clean"
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

def test_legend_items_include_conflicted():
    """验证图例条目包含冲突状态，且与 i18n 完全对齐"""
    window = MainWindow()
    window.poller.stop()
    window.poller.wait()

    legend_keys = [key for _, key in window.legend_labels]
    assert "file_conflicted" in legend_keys
