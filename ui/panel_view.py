from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QLineEdit, QFileDialog, QGridLayout)
from PySide6.QtCore import Qt, Signal
import os
import sys
import subprocess
import webbrowser

from ui.components.buttons import MaterialButton
from ui.theme import COLORS
from core.i18n import tr, lang_manager
from core.config import load_config, save_config

class PanelView(QWidget):
    # Signals for core actions
    action_requested = Signal(str, dict) # action_name, payload

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(16)
        
        self._setup_config_area()
        self._setup_pipeline_area()
        self._setup_i18n()

    def _setup_config_area(self):
        config_widget = QWidget()
        config_widget.setStyleSheet(f"background-color: {COLORS['surface']}; border-radius: 8px;")
        grid = QGridLayout(config_widget)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setSpacing(12)
        
        # Local Path
        self.lbl_local = QLabel(tr("local_repo"))
        self.lbl_local.setStyleSheet(f"color: {COLORS['text_disabled']};")
        self.line_local = QLineEdit(self.config.get("local_path", ""))
        self.line_local.setReadOnly(True)
        self.btn_select = MaterialButton(tr("select_folder"))
        self.btn_select.clicked.connect(self._select_folder)
        
        grid.addWidget(self.lbl_local, 0, 0)
        grid.addWidget(self.line_local, 0, 1)
        grid.addWidget(self.btn_select, 0, 2)
        
        # Remote URL
        self.lbl_remote = QLabel(tr("remote_repo"))
        self.lbl_remote.setStyleSheet(f"color: {COLORS['text_disabled']};")
        self.line_remote = QLineEdit(self.config.get("remote_url", ""))
        self.line_remote.editingFinished.connect(self._save_remote_url)
        
        action_layout_remote = QHBoxLayout()
        action_layout_remote.setSpacing(8)
        self.btn_save_remote = MaterialButton(tr("save_remote"))
        self.btn_save_remote.clicked.connect(self._save_remote_url)
        self.btn_clear_remote = MaterialButton(tr("clear_remote"))
        self.btn_clear_remote.setStyleSheet(f"QPushButton {{ background: transparent; color: {COLORS['error']}; }}")
        self.btn_clear_remote.clicked.connect(self._clear_remote_url)
        
        action_layout_remote.addWidget(self.btn_save_remote)
        action_layout_remote.addWidget(self.btn_clear_remote)
        
        grid.addWidget(self.lbl_remote, 1, 0)
        grid.addWidget(self.line_remote, 1, 1)
        grid.addLayout(action_layout_remote, 1, 2)
        
        # Project URL & Preview actions
        self.lbl_project = QLabel(tr("project_url"))
        self.lbl_project.setStyleSheet(f"color: {COLORS['text_disabled']};")
        self.line_project = QLineEdit(self.config.get("project_url", ""))
        self.line_project.editingFinished.connect(self._save_project_url)
        self.line_project.textChanged.connect(self._update_preview_state)
        
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        self.btn_preview = MaterialButton(tr("preview_project"))
        self.btn_preview.clicked.connect(self._preview_project)
        self.btn_terminal = MaterialButton(tr("open_terminal"))
        self.btn_terminal.clicked.connect(self._open_terminal)
        
        action_layout.addWidget(self.btn_preview)
        action_layout.addWidget(self.btn_terminal)
        
        grid.addWidget(self.lbl_project, 2, 0)
        grid.addWidget(self.line_project, 2, 1)
        grid.addLayout(action_layout, 2, 2)
        
        self.layout.addWidget(config_widget)

    def _setup_pipeline_area(self):
        pipe_widget = QWidget()
        pipe_layout = QVBoxLayout(pipe_widget)
        pipe_layout.setContentsMargins(0, 0, 0, 0)
        pipe_layout.setSpacing(12)
        
        # Top Row
        row1 = QHBoxLayout()
        self.btn_sync = MaterialButton(tr("sync_latest"))
        self.btn_sync.clicked.connect(lambda: self.action_requested.emit("sync", {}))
        
        self.btn_task = MaterialButton(tr("start_task"), is_primary=True)
        self.btn_task.clicked.connect(lambda: self.action_requested.emit("branch", {}))
        
        self.btn_history = MaterialButton(tr("branch_history"))
        self.btn_history.clicked.connect(lambda: self.action_requested.emit("branch_history", {}))
        
        row1.addWidget(self.btn_sync)
        row1.addWidget(self.btn_task)
        row1.addWidget(self.btn_history)
        pipe_layout.addLayout(row1)
        
        # Mid Row
        row2 = QHBoxLayout()
        self.btn_stage = MaterialButton(tr("stage_changes"), is_primary=True)
        self.btn_stage.clicked.connect(lambda: self.action_requested.emit("stage", {}))
        
        self.btn_unstage = MaterialButton(tr("unstage"))
        self.btn_unstage.clicked.connect(lambda: self.action_requested.emit("unstage", {}))
        
        self.btn_commit = MaterialButton(tr("commit"), is_primary=True)
        self.btn_commit.clicked.connect(lambda: self.action_requested.emit("commit", {}))
        
        row2.addWidget(self.btn_stage)
        row2.addWidget(self.btn_unstage)
        row2.addWidget(self.btn_commit)
        pipe_layout.addLayout(row2)
        
        # Bottom Row
        row3 = QHBoxLayout()
        self.btn_undo = MaterialButton(tr("undo_commit"))
        self.btn_undo.clicked.connect(lambda: self.action_requested.emit("undo", {}))
        
        self.btn_push = MaterialButton(tr("push"), is_primary=True)
        self.btn_push.clicked.connect(lambda: self.action_requested.emit("push", {}))
        
        row3.addWidget(self.btn_undo)
        row3.addWidget(self.btn_push)
        pipe_layout.addLayout(row3)
        
        self.layout.addWidget(pipe_widget)
        self.layout.addStretch()

    def _setup_i18n(self):
        lang_manager.language_changed.connect(self._retranslate)

    def _retranslate(self, lang):
        self.lbl_local.setText(tr("local_repo"))
        self.lbl_remote.setText(tr("remote_repo"))
        self.btn_select.setText(tr("select_folder"))
        self.btn_clear_remote.setText(tr("clear_remote"))
        self.btn_save_remote.setText(tr("save_remote"))
        self.lbl_project.setText(tr("project_url"))
        self.btn_preview.setText(tr("preview_project"))
        self.btn_terminal.setText(tr("open_terminal"))
        
        self.btn_sync.setText(tr("sync_latest"))
        self.btn_task.setText(tr("start_task"))
        self.btn_history.setText(tr("branch_history"))
        self.btn_stage.setText(tr("stage_changes"))
        self.btn_unstage.setText(tr("unstage"))
        self.btn_commit.setText(tr("commit"))
        self.btn_undo.setText(tr("undo_commit"))
        self.btn_push.setText(tr("push"))

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("select_folder"), self.config.get("local_path", ""))
        if folder:
            folder = folder.replace('\\', '/')
            self.config["local_path"] = folder
            self.line_local.setText(folder)
            save_config(self.config)
            self.action_requested.emit("change_repo", {"path": folder})

    def _save_remote_url(self):
        url = self.line_remote.text().strip()
        self.config["remote_url"] = url
        save_config(self.config)
        if url:
            self.action_requested.emit("set_remote", {"url": url})
            
    def _save_project_url(self):
        url = self.line_project.text().strip()
        self.config["project_url"] = url
        save_config(self.config)

    def _update_preview_state(self):
        self.btn_preview.setEnabled(bool(self.line_project.text().strip()))

    def _preview_project(self):
        url = self.line_project.text().strip()
        if url:
            webbrowser.open(url)

    def _open_terminal(self):
        path = self.line_local.text()
        if path and os.path.exists(path):
            if os.name == 'nt':
                os.system(f'start cmd /K "cd /d {path}"')
            elif sys.platform == 'darwin':
                subprocess.Popen(["open", "-a", "Terminal", path])
            else:
                subprocess.Popen(["x-terminal-emulator"], cwd=path)

    def _clear_remote_url(self):
        self.line_remote.setText("")
        self.config["remote_url"] = ""
        save_config(self.config)
        self.action_requested.emit("set_remote", {"url": ""})

    def update_state(self, state):
        # State machine
        repo_ok = state.isRepo
        no_changes = not state.hasModified and not state.hasStaged
        is_main = state.currentBranch in ("main", "master")
        
        self.btn_sync.setEnabled(repo_ok and no_changes and is_main)
        self.btn_task.setEnabled(repo_ok)
        self.btn_history.setEnabled(repo_ok and no_changes)
        
        self.btn_stage.setEnabled(repo_ok and state.hasModified)
        self.btn_unstage.setEnabled(repo_ok and state.hasStaged)
        self.btn_commit.setEnabled(repo_ok and state.hasStaged)
        
        self.btn_undo.setEnabled(repo_ok and state.canUndo)
        self.btn_push.setEnabled(bool(repo_ok and (state.commitsAhead > 0 or state.currentBranch)))
        self._update_preview_state()

    def get_repo_path(self):
        return self.line_local.text()
