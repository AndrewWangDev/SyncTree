import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from ui.window import MainWindow
from ui.panel_view import PanelView

def test_delete_root_and_traversal_protection():
    """【缺陷 3 验证】严禁删除仓库根目录或仓库外部的文件"""
    tmp_dir = tempfile.mkdtemp()
    outside_dir = tempfile.mkdtemp()
    try:
        window = MainWindow()
        window.poller.repo_path = tmp_dir
        
        # 模拟展示弹窗的 mock
        with patch("ui.window.show_result_modal") as mock_modal:
            # 1. 尝试删除仓库根目录 -> 必须被拦截并弹出警告
            fake_index_root = MagicMock()
            window.file_model.filePath = MagicMock(return_value=tmp_dir)
            window._delete_item(fake_index_root)
            
            mock_modal.assert_called_once()
            args, _ = mock_modal.call_args
            assert args[1] is False # is_success == False
            
            mock_modal.reset_mock()
            
            # 2. 尝试删除仓库外路径 -> 必须被拦截并弹出警告
            outside_file = os.path.join(outside_dir, "secret.txt")
            window.file_model.filePath = MagicMock(return_value=outside_file)
            window._delete_item(fake_index_root)
            
            mock_modal.assert_called_once()
            args, _ = mock_modal.call_args
            assert args[1] is False
            
        window.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.rmtree(outside_dir, ignore_errors=True)

def test_terminal_open_special_characters():
    """【缺陷 2 验证】路径中包含系统特殊控制符（如 &, |, ^, 空格）时，Popen 不走 Shell 字符串拼接"""
    panel = PanelView()
    special_path = r"C:\Code\C & C++\Project | Test"
    panel.line_local.setText(special_path)
    
    with patch("os.path.exists", return_value=True), patch("subprocess.Popen") as mock_popen:
        panel._open_terminal()
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        cmd_args = args[0]
        
        # 验证传入的是参数列表，且在 Windows 下使用 cmd.exe /K
        if os.name == 'nt':
            assert isinstance(cmd_args, list)
            assert cmd_args[0] == "cmd.exe"
            assert cmd_args[1] == "/K"
            assert special_path in cmd_args[2]
            # 确保没有使用 shell=True
            assert kwargs.get("shell") is not True
