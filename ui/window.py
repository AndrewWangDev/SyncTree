from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSplitter, QTreeView, QFileSystemModel
from PySide6.QtGui import QIcon, QCursor, QPainter, QPixmap, QColor, QPen
from PySide6.QtCore import Qt, QTimer
import os
import sys
import ctypes
import webbrowser

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if os.name == 'nt':
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("andrewwang.synctree.beta.1")

from core.git_utils import GitPoller
from core.git_actions import GitActions
from core.i18n import lang_manager, tr
from ui.theme import QSS, COLORS
from ui.graph_view import GraphView
from ui.panel_view import PanelView
from ui.components.toast import ToastLabel
from ui.components.modals import ModalOverlay, show_input_modal, show_history_branch_modal, show_diag_modal, show_about_modal, show_search_results_modal, show_result_modal
from PySide6.QtWidgets import QLineEdit

class GitFileModel(QFileSystemModel):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DecorationRole and index.column() == 0:
            original_icon = super().data(index, role)
            file_path = self.filePath(index)
            
            status = self.get_status(file_path)
            if not status or status == 'ignored': 
                return original_icon
                
            color_map = {
                'clean': "#4CAF50",      # Bright Green
                'untracked': "#9E9E9E",  # Brighter Grey
                'unstaged': "#F44336",   # Bright Red
                'staged': "#FFEB3B"      # Bright Yellow
            }
            color_hex = color_map.get(status, "#9E9E9E")
            
            pixmap = QPixmap(32, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            painter.setBrush(QColor(color_hex))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 3, 10, 10)
            
            if original_icon:
                if isinstance(original_icon, QIcon):
                    original_icon.paint(painter, 16, 0, 16, 16)
                
            painter.end()
            
            return QIcon(pixmap)
            
        return super().data(index, role)

    def get_status(self, file_path):
        state = self.main_window.current_state
        if not state or not state.isRepo: return None
        
        # Build normalized dictionary specifically for case-insensitive Windows match
        fileStatuses_nc = {os.path.normcase(k): v for k, v in state.fileStatuses.items()}
        
        file_path_nc = os.path.normcase(os.path.normpath(file_path))
        
        if file_path_nc in fileStatuses_nc:
            return fileStatuses_nc[file_path_nc]
            
        curr = file_path_nc
        repo_path_nc = os.path.normcase(os.path.normpath(self.main_window.poller.repo_path))
        while curr and len(curr) > 3 and curr != repo_path_nc:
            curr = os.path.dirname(curr)
            if curr in fileStatuses_nc:
                parent_status = fileStatuses_nc[curr]
                if parent_status in ('untracked', 'ignored'):
                    return parent_status
        return 'clean'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SyncTree (Beta)")
        self.setWindowIcon(QIcon(get_resource_path("logo.png")))
        self.resize(800, 700)
        self.setStyleSheet(QSS)
        
        self.poller = GitPoller()
        self.actions = GitActions(self.poller)
        self.current_state = None
        
        self._setup_ui()
        self._bind_signals()
        
        # Initialization logic from config
        initial_path = self.panel.get_repo_path()
        if initial_path:
            self.change_repo(initial_path)
            if self.panel.config.get("remote_url"):
                self.actions.set_remote(self.panel.config["remote_url"])

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Header with Language Toggle
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignVCenter)
        
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        title_lbl = QLabel("SyncTree")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        beta_lbl = QLabel("Beta")
        beta_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLORS['on_primary']}; background-color: {COLORS['primary']}; border-radius: 4px; padding: 2px 6px;")
        beta_lbl.setFixedHeight(20)
        
        title_layout.addWidget(title_lbl)
        title_layout.addWidget(beta_lbl, 0, Qt.AlignVCenter)
        
        self.btn_lang = QPushButton("中 / EN")
        self.btn_lang.setFixedSize(80, 40)
        self.btn_lang.setStyleSheet(f"font-size: 14px; font-weight: bold; background: {COLORS['surface_variant']}; border-radius: 8px;")
        self.btn_lang.setCursor(Qt.PointingHandCursor)
        self.btn_lang.clicked.connect(lang_manager.toggle)
        
        self.btn_diag = QPushButton(tr("network_diag"))
        self.btn_diag.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['primary']}; background: transparent; border: none; padding: 0 8px;")
        self.btn_diag.setCursor(Qt.PointingHandCursor)
        self.btn_diag.clicked.connect(lambda: show_diag_modal(self.overlay))
        
        self.btn_about_us = QPushButton(tr("about_us"))
        self.btn_about_us.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['secondary']}; background: transparent; border: none; padding: 0 8px;")
        self.btn_about_us.setCursor(Qt.PointingHandCursor)
        self.btn_about_us.clicked.connect(lambda: show_about_modal(self.overlay))
        
        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)
        right_layout.addWidget(self.btn_diag)
        right_layout.addWidget(self.btn_about_us)
        right_layout.addSpacing(8)
        right_layout.addWidget(self.btn_lang)
        
        header_layout.addLayout(title_layout)
        
        def create_search_icon():
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(COLORS['text_disabled']))
            pen.setWidth(2)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawEllipse(2, 2, 6, 6)
            painter.drawLine(7, 7, 12, 12)
            painter.end()
            return QIcon(pixmap)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("search_files") + "...")
        from PySide6.QtWidgets import QSizePolicy
        self.search_input.setMinimumWidth(200)
        self.search_input.setMaximumWidth(500)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet(f"background-color: {COLORS['surface_variant']}; border: none; border-radius: 16px; padding: 0 12px 0 4px; color: {COLORS['text']};")
        self.search_input.addAction(create_search_icon(), QLineEdit.LeadingPosition)
        self.search_input.returnPressed.connect(self._perform_search)
        
        header_layout.addSpacing(24)
        header_layout.addWidget(self.search_input)
        header_layout.addStretch()
        
        self.lbl_branch = QLabel(f"{tr('current_branch')}: -")
        self.lbl_branch.setFixedHeight(32)
        self.lbl_branch.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['primary']}; background: {COLORS['surface_variant']}; padding: 0 12px; border-radius: 8px;")
        header_layout.addWidget(self.lbl_branch)
        header_layout.addSpacing(16)
        
        header_layout.addLayout(right_layout)
        
        main_layout.addLayout(header_layout)
        
        # Top 40% area with Splitter (Graph View + File Tree View)
        top_splitter = QSplitter(Qt.Horizontal)
        self.graph = GraphView()
        
        right_panel = QWidget()
        right_layout = QHBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        self.file_model = GitFileModel(self)
        self.file_model.setRootPath("")
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text']}; border: none; border-radius: 8px; padding: 4px;")
        self.file_tree.setHeaderHidden(True)
        for i in range(1, 4):
            self.file_tree.hideColumn(i)
        self.file_tree.doubleClicked.connect(self._open_file)
        self.file_tree.clicked.connect(self._on_file_clicked)
            
        right_layout.addWidget(self.file_tree, stretch=1)
        
        from PySide6.QtWidgets import QListWidget, QListWidgetItem, QSizePolicy
        legend_layout = QVBoxLayout()
        legend_layout.setContentsMargins(4, 4, 4, 4)
        def make_legend(color, text):
            return QLabel(f'<span style="color:{color}; font-size:16px;">●</span> <span style="font-size:12px; color:{COLORS["text"]};">{text}</span>')
        legend_layout.addWidget(make_legend("#9E9E9E", "未修改"))
        legend_layout.addWidget(make_legend("#F44336", "未暂存"))
        legend_layout.addWidget(make_legend("#FFEB3B", "未提交"))
        legend_layout.addWidget(make_legend("#4CAF50", "已提交"))
        
        legend_layout.addStretch()
        
        logo_lbl = QLabel()
        logo_pixmap = QPixmap(get_resource_path("logo.png")).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_lbl.setPixmap(logo_pixmap)
        logo_lbl.setAlignment(Qt.AlignCenter)
        legend_layout.addWidget(logo_lbl)
        
        right_layout.addLayout(legend_layout)
        
        top_splitter.addWidget(self.graph)
        top_splitter.addWidget(right_panel)
        top_splitter.setStretchFactor(0, 6)
        top_splitter.setStretchFactor(1, 4) # adjustable File Tree width
        
        main_layout.addWidget(top_splitter, stretch=4)
        
        # Panel View (60%)
        self.panel = PanelView()
        main_layout.addWidget(self.panel, stretch=6)
        
        # Overlays
        self.overlay = ModalOverlay(self)
        self.toast = ToastLabel(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())
        
    def _retranslate_local(self, lang):
        self.btn_about_us.setText(tr("about_us"))
        self.btn_diag.setText(tr("network_diag"))
        self.search_input.setPlaceholderText(tr("search_files") + "...")
        if self.current_state and self.current_state.currentBranch:
            self.lbl_branch.setText(f"{tr('current_branch')}: {self.current_state.currentBranch}")
        else:
            self.lbl_branch.setText(f"{tr('current_branch')}: -")

    def _bind_signals(self):
        self.poller.state_updated.connect(self._on_state_updated)
        self.panel.action_requested.connect(self._handle_panel_action)
        lang_manager.language_changed.connect(self._retranslate_local)

    def _on_state_updated(self, state):
        self.current_state = state
        self.graph.update_graph(state)
        self.panel.update_state(state)
        
        if state.currentBranch:
            self.lbl_branch.setText(f"{tr('current_branch')}: {state.currentBranch}")
        else:
            self.lbl_branch.setText(f"{tr('current_branch')}: -")
            
        self.file_model.layoutChanged.emit()

    def _open_file(self, index):
        path = self.file_model.filePath(index)
        if os.path.isfile(path):
            if os.name == 'nt':
                os.startfile(path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.Popen(['open', path])

    def _on_file_clicked(self, index):
        path = self.file_model.filePath(index)
        if not os.path.isfile(path) or not self.current_state:
            return
            
        status = self.file_model.get_status(path)
        if status in ['unstaged', 'staged']:
            rel_path = os.path.relpath(path, self.poller.repo_path)
            out, err = self.actions.diff_file(rel_path, staged=(status == 'staged'))
            if out:
                from ui.components.modals import show_diff_modal
                show_diff_modal(self.overlay, rel_path, out)

    def _perform_search(self):
        query = self.search_input.text().strip().lower()
        if not query or not self.poller.repo_path:
            return
            
        out, err = self.actions.run_cmd(["ls-files", "--cached", "--others", "--exclude-standard"])
        if not out:
            return
            
        results = []
        for line in out.split('\n'):
            line = line.strip()
            if line and query in os.path.basename(line).lower():
                results.append(line)
        
        show_search_results_modal(self.overlay, query, results, self.poller.repo_path, self._open_search_file)
        self.search_input.clear()

    def _open_search_file(self, rel_path):
        import os, sys
        full_path = os.path.join(self.poller.repo_path, rel_path)
        if os.path.isfile(full_path):
            if os.name == 'nt':
                os.startfile(full_path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.Popen(['open', full_path])

    def _handle_panel_action(self, action, payload):
        if action == "change_repo":
            self.change_repo(payload["path"])
        elif action == "set_remote":
            out, err = self.actions.set_remote(payload["url"])
            if err:
                show_result_modal(self.overlay, False, f"配置远端失败:\n\n{err}")
        elif action == "sync":
            out, err = self.actions.sync_latest()
            if err:
                show_result_modal(self.overlay, False, f"{tr('sync_failed')}\n\n{err}", lambda: show_diag_modal(self.overlay))
            else:
                show_result_modal(self.overlay, True, tr("sync_success"))
        elif action == "branch":
            def do_branch(name):
                out, err = self.actions.create_branch(name)
                if err:
                    show_result_modal(self.overlay, False, f"{tr('branch_failed')}\n\n{err}")
                else:
                    show_result_modal(self.overlay, True, tr("branch_success") + f": {name}")
            show_input_modal(self.overlay, tr("enter_task_name"), do_branch)
        elif action == "branch_history":
            if self.current_state:
                out, err = self.actions.run_cmd(["log", "--all", "--oneline", "-n", "50"])
                choices = out.split('\n') if out else []
                def do_branch_hist(name, hash_val):
                    o, e = self.actions.create_branch(name, hash_val)
                    if e:
                        show_result_modal(self.overlay, False, f"{tr('branch_failed')}\n\n{e}")
                    else:
                        show_result_modal(self.overlay, True, tr("branch_success") + f": {name}")
                show_history_branch_modal(self.overlay, tr("branch_history"), choices, do_branch_hist)
        elif action == "stage":
            out, err = self.actions.stage_all()
            if err:
                show_result_modal(self.overlay, False, f"{tr('stage_failed')}\n\n{err}")
            else:
                show_result_modal(self.overlay, True, tr("stage_success"))
        elif action == "unstage":
            out, err = self.actions.unstage_all()
            if err:
                show_result_modal(self.overlay, False, f"{tr('unstage_failed')}\n\n{err}")
            else:
                show_result_modal(self.overlay, True, tr("unstage_success"))
        elif action == "commit":
            def do_commit(msg):
                out, err = self.actions.commit(msg)
                if err:
                    show_result_modal(self.overlay, False, f"{tr('commit_failed')}\n\n{err}")
                else:
                    show_result_modal(self.overlay, True, tr("commit_success"))
            show_input_modal(self.overlay, tr("describe_work"), do_commit)
        elif action == "undo":
            out, err = self.actions.undo_commit()
            if err:
                show_result_modal(self.overlay, False, f"{tr('undo_commit_failed')}\n\n{err}")
            else:
                show_result_modal(self.overlay, True, tr("undo_commit_success"))
        elif action == "push":
            if self.current_state:
                out, err = self.actions.push(self.current_state.currentBranch)
                if err is not None:
                    show_result_modal(self.overlay, False, f"{tr('push_failed')}\n\n{err}", lambda: show_diag_modal(self.overlay))
                else:
                    show_result_modal(self.overlay, True, tr("push_success"))

    def _set_new_cloned_repo(self, new_dir):
        new_dir = new_dir.replace('\\', '/')
        self.panel.line_local.setText(new_dir)
        self.panel.config["local_path"] = new_dir
        from core.config import save_config
        save_config(self.panel.config)
        self.change_repo(new_dir)

    def change_repo(self, path):
        path = path.replace('\\', '/') if path else path
        if path and os.path.exists(path):
            if not os.path.exists(os.path.join(path, ".git")):
                # Show empty folder interaction interceptor
                def do_init():
                    self._setup_repo_path(path)
                    self.actions.init_repo()
                    self.toast.show_message(tr("auto_init"))
                    
                def do_clone():
                    def perform_clone(url):
                        self.panel.line_remote.setText(url)
                        self.panel.config["remote_url"] = url
                        self.toast.show_message("正在克隆，请耐心等待...")
                        
                        from PySide6.QtCore import QThread, Signal
                        class CloneThread(QThread):
                            res_ready = Signal(object)
                            def __init__(self, c_url, c_cwd, parent=None):
                                super().__init__(parent)
                                self.url = c_url
                                self.cwd = c_cwd
                            def run(self):
                                import subprocess, os
                                cr = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                                res = subprocess.run(["git", "clone", self.url], cwd=self.cwd, capture_output=True, text=True, creationflags=cr, encoding='utf-8', errors='replace')
                                self.res_ready.emit(res)
                                
                        def on_clone_done(res):
                            if res.returncode == 0:
                                dirs = [os.path.join(path, d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                                if len(dirs) >= 1:
                                    # Choose the most recently created or the only dir
                                    self._set_new_cloned_repo(dirs[-1])
                                    self.toast.show_message("克隆成功")
                                else:
                                    self.toast.show_message("克隆完成但找不到子文件夹")
                            else:
                                show_result_modal(self.overlay, False, f"克隆失败:\n{res.stderr}")
                                
                        self._clone_thread = CloneThread(url, path, self)
                        self._clone_thread.res_ready.connect(on_clone_done)
                        self._clone_thread.start()
                        
                    from ui.components.modals import show_input_modal
                    show_input_modal(self.overlay, "请输入远程仓库URL", perform_clone)
                    
                from ui.components.modals import show_empty_folder_modal
                show_empty_folder_modal(self.overlay, do_init, do_clone)
                return
                
            self._setup_repo_path(path)
        else:
            self.poller.stop()
            self.poller.wait()
            from core.state import GitState
            self._on_state_updated(GitState())
            
    def _setup_repo_path(self, path):
        self.poller.repo_path = path
        self.file_model.setRootPath(path)
        self.file_tree.setRootIndex(self.file_model.index(path))
        
        if not self.poller.isRunning():
            self.poller.start()
        else:
            self.poller.trigger_update()

    def closeEvent(self, event):
        self.poller.stop()
        self.poller.wait()
        super().closeEvent(event)
