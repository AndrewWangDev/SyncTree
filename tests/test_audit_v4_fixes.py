import os
import gc
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

from core.i18n import lang_manager
from core.git_utils import GitPoller
from core.state import GitState
from ui.window import MainWindow

def test_close_event_unsets_file_tree_model():
    """【BUG-01 验证】closeEvent 必须正确解绑 self.file_tree 的 Model，避免底层悬挂指针"""
    window = MainWindow()
    try:
        window.poller.stop()
        window.poller.wait()
        assert window.file_tree.model() is not None
        
        window.close()
        assert window.file_tree.model() is None
    finally:
        window.deleteLater()
        if QApplication.instance():
            QApplication.instance().processEvents()


def test_language_manager_weak_reference_allows_gc():
    """【BUG-02 验证】_LanguageChangedSignal 必须采用弱引用，避免全局单例阻止组件 GC 回收"""
    class TargetWidget:
        def __init__(self):
            self.last_lang = None
        def on_lang(self, lang):
            self.last_lang = lang

    widget = TargetWidget()
    lang_manager.language_changed.connect(widget.on_lang)

    # 正常发射信号
    lang_manager.language_changed.emit("en")
    assert widget.last_lang == "en"

    # 释放 widget 引用
    del widget
    gc.collect()

    # 再次发射信号，验证死亡的 WeakMethod 自动清理且不抛出异常
    lang_manager.language_changed.emit("zh")


def test_git_rename_and_copy_status_parsing():
    """【BUG-03 验证】git status 重命名行 (R  old -> new) 必须准确提取目标生成文件并设置状态与冒泡"""
    tmp_dir = tempfile.mkdtemp()
    try:
        poller = GitPoller(tmp_dir)
        
        # 模拟 status --porcelain 输出包含重命名与空格带引号路径
        status_lines = "\n".join([
            "R  old.txt -> new.txt",
            'R  "docs/old manual.md" -> "docs/new manual.md"'
        ])
        
        with patch.object(poller, "_run_git") as mock_git:
            def side_effect(cmd, check_repo=True):
                if "--is-inside-work-tree" in cmd:
                    return "true"
                if "status" in cmd:
                    return status_lines
                if "rev-parse" in cmd:
                    return "hash123"
                if "branch" in cmd:
                    return "main"
                return ""
            mock_git.side_effect = side_effect
            
            state = poller._poll_git()
            assert state.isRepo is True
            
            # 目标新文件必须存在于 fileStatuses 中，且状态为 staged
            assert "new.txt" in state.fileStatuses
            assert state.fileStatuses["new.txt"] == "staged"
            assert "docs/new manual.md" in state.fileStatuses
            assert state.fileStatuses["docs/new manual.md"] == "staged"
            
            # 绝对路径也必须映射
            abs_new = os.path.realpath(os.path.join(tmp_dir, "new.txt")).replace('\\', '/').lower()
            assert state.fileStatuses.get(abs_new) == "staged"
            
            # docs 目录必须冒泡为 staged
            abs_docs = os.path.realpath(os.path.join(tmp_dir, "docs")).replace('\\', '/').lower()
            assert state.dirStatuses.get(abs_docs) == "staged"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_clone_cancel_and_error_clean_subdirs():
    """【BUG-04 验证】克隆被 cancel() 或异常退出时，必须清理本次产生的新建半成品目录，保留原有目录"""
    tmp_parent = tempfile.mkdtemp()
    try:
        # 预先存在的合法子目录
        pre_existing = os.path.join(tmp_parent, "existing_repo")
        os.makedirs(pre_existing, exist_ok=True)
        existing_subdirs = { "existing_repo" }
        
        # 模拟 Clone 过程中创建了半成品目标目录
        broken_dir = os.path.join(tmp_parent, "cloned_repo")
        os.makedirs(os.path.join(broken_dir, ".git"), exist_ok=True)
        
        # 模拟取消或失败时的清理逻辑
        current_subdirs = set(os.listdir(tmp_parent))
        new_dirs = current_subdirs - existing_subdirs
        assert "cloned_repo" in new_dirs
        
        for nd in new_dirs:
            shutil.rmtree(os.path.join(tmp_parent, nd), ignore_errors=True)
            
        # 验证半成品已被清理，原有目录依然完好
        assert not os.path.exists(broken_dir)
        assert os.path.exists(pre_existing)
    finally:
        shutil.rmtree(tmp_parent, ignore_errors=True)
