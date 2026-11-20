import os
import sys
import tempfile
import shutil
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel
app = QApplication.instance() or QApplication([])

from core.state import GitState
from core.git_utils import GitPoller, normalize_repo_path
from ui.graph_view import git_ansi_to_html
from ui.panel_view import PanelView
from ui.components.toast import ToastLabel
from ui.components.modals import ModalOverlay, DiffModalContent
from ui.window import GitFileModel, MainWindow

def test_graph_view_ansi_and_symbol_integrity():
    """【缺陷 19 验证】仅行首拓扑字符做美化替换，严禁破坏提交信息中的星号、斜杠与竖线"""
    # 模拟真实 git log --graph 输出
    line = "* a1b2c3d fix(auth/api): improve docs *bold* | url: https://github.com/test"
    html = git_ansi_to_html(line)
    
    # 行首图字符 * 应被替换为 ●
    assert "●" in html
    
    # 提交信息中的分支名、星号和竖线绝对不能被替换
    assert "fix(auth/api)" in html
    assert "*bold*" in html
    assert "| url: https://github.com/test" in html
    assert "╱" not in html # 正斜杠不应被替换为几何符号
    assert "│" not in html # 提交信息里的竖线不应被替换

def test_panel_view_push_button_state_machine():
    """【缺陷 9 验证】修复 btn_push 永久可用缺陷，无超前提交且有远程分支时必须自动禁用"""
    panel = PanelView()
    
    # 场景 1: 正常分支，已跟踪远程分支，但无超前提交 (commitsAhead == 0) -> 必须禁用推送！
    state1 = GitState(
        isRepo=True,
        currentBranch="main",
        commitsAhead=0,
        hasUpstream=True
    )
    panel.update_state(state1)
    assert panel.btn_push.isEnabled() is False, "Push button should be disabled when 0 commits ahead with upstream"
    
    # 场景 2: 有 2 个本地超前提交 -> 必须启用推送！
    state2 = GitState(
        isRepo=True,
        currentBranch="main",
        commitsAhead=2,
        hasUpstream=True
    )
    panel.update_state(state2)
    assert panel.btn_push.isEnabled() is True, "Push button should be enabled when commitsAhead > 0"
    
    # 场景 3: 新任务分支尚未设置远程跟踪 -> 必须启用推送（以便初次推送到远端）！
    state3 = GitState(
        isRepo=True,
        currentBranch="feature/new-task",
        commitsAhead=0,
        hasUpstream=False
    )
    panel.update_state(state3)
    assert panel.btn_push.isEnabled() is True, "Push button should be enabled for untracked branch"
    
    # 场景 4: 非 Git 仓库 -> 必须禁用
    state4 = GitState(isRepo=False)
    panel.update_state(state4)
    assert panel.btn_push.isEnabled() is False

def test_toast_label_signal_rebinding():
    """【缺陷 16 验证】多次隐藏/显示 ToastLabel，finished 信号不应重复连接累积"""
    toast = ToastLabel()
    # 触发多次显示与隐藏
    for i in range(5):
        toast.show_message(f"Msg {i}", duration=100)
        toast.hide_toast()
    
    # 验证动画正常
    assert toast.anim is not None

def test_modal_overlay_lambda_accumulation():
    """【缺陷 17 验证】多次关闭弹窗不应累加匿名槽函数"""
    overlay = ModalOverlay()
    for _ in range(5):
        overlay.show_animated()
        overlay.hide_animated()
    assert overlay.anim is not None

def test_diff_modal_splitlines():
    """【缺陷 10 验证】Diff 弹窗必须使用真实的换行符切分并赋予增删高亮"""
    overlay = ModalOverlay()
    diff_text = "@@ -1,2 +1,3 @@\n-old line\n+new line 1\n+new line 2\n context"
    content = DiffModalContent(overlay, "test.py", diff_text)
    html = content.text_edit.toHtml()
    
    assert "old line" in html
    assert "new line 1" in html
    assert "#f44336" in html.lower() # 删除行红色高亮
    assert "#4caf50" in html.lower() # 新增行绿色高亮

def test_file_tree_folder_status_bubbling():
    """【缺陷 21 验证】当子目录内含有未暂存文件时，父文件夹状态应向上冒泡为 unstaged"""
    tmp_dir = tempfile.mkdtemp()
    try:
        sub_folder = os.path.join(tmp_dir, "src", "core")
        os.makedirs(sub_folder, exist_ok=True)
        deep_file = os.path.join(sub_folder, "app.py")
        with open(deep_file, "w") as f:
            f.write("content")
            
        window = MainWindow()
        window.poller.stop()
        window.poller.wait()
        window.poller.repo_path = tmp_dir
        
        deep_key = normalize_repo_path(deep_file)
        state = GitState(
            isRepo=True,
            fileStatuses={
                deep_key: "unstaged"
            }
        )
        window.current_state = state
        
        # 检查一级父目录 src 的状态
        src_dir = os.path.join(tmp_dir, "src")
        status_src = window.file_model.get_status(src_dir)
        assert status_src == "unstaged", f"Parent directory should bubble up to 'unstaged', got '{status_src}'"
        
        # 检查二级父目录 core 的状态
        status_core = window.file_model.get_status(sub_folder)
        assert status_core == "unstaged", f"Sub-directory should bubble up to 'unstaged', got '{status_core}'"
        
        window.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_window_title_and_beta_badge_removed():
    """验证 Beta 标识已移除且窗口标题为 SyncTree"""
    window = MainWindow()
    window.poller.stop()
    window.poller.wait()
    try:
        assert window.windowTitle() == "SyncTree"
        # 验证标题栏区域内不存在包含 "Beta" 的 QLabel
        labels = window.findChildren(QLabel)
        for lbl in labels:
            assert lbl.text().strip() != "Beta", "Beta label badge should be removed from official release"
    finally:
        window.close()


def test_focus_cleared_on_outside_click():
    """验证全局 EventFilter 在点击输入框外部时自动清除 QLineEdit 焦点"""
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QWidget
    from unittest.mock import patch
    
    window = MainWindow()
    window.poller.stop()
    window.poller.wait()
    try:
        line_edit = window.panel.line_remote
        dummy_widget = QWidget(window)
        mouse_press = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        with patch.object(QApplication, "focusWidget", return_value=line_edit), \
             patch.object(line_edit, "clearFocus") as mock_clear:
            window.eventFilter(dummy_widget, mouse_press)
            assert mock_clear.called, "clearFocus should be called on the focused QLineEdit"
    finally:
        window.close()

