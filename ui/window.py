from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSplitter, QTreeView, QFileSystemModel, QMenu, QLineEdit
from PySide6.QtGui import QIcon, QCursor, QPainter, QPixmap, QColor, QPen, QDesktopServices
from PySide6.QtCore import Qt, QTimer, QEvent, QUrl
import os
import sys
import ctypes
import re

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if os.name == 'nt':
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("andrewwang.synctree.beta.1")
    except Exception:
        pass

from core.git_utils import GitPoller
from core.git_actions import GitActions, CleanupThread
from core.i18n import lang_manager, tr
from ui.theme import QSS, COLORS
from ui.graph_view import GraphView
from ui.panel_view import PanelView
from ui.components.buttons import MaterialButton, AnimatedLogo
from ui.components.toast import ToastLabel
from ui.components.modals import ModalOverlay, show_input_modal, show_history_branch_modal, show_diag_modal, show_about_modal, show_search_results_modal, show_result_modal, BaseDialogMsg

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
                'staged': "#FFEB3B",     # Bright Yellow
                'conflicted': "#FF5722", # Deep Orange / Conflict
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
        if not state or not state.isRepo or not self.main_window.poller.repo_path:
            return None
        
        file_real = os.path.realpath(file_path).replace('\\', '/').lower()
        repo_real = os.path.realpath(self.main_window.poller.repo_path).replace('\\', '/').lower()
        
        # 1. 直接绝对路径匹配
        if file_real in state.fileStatuses:
            return state.fileStatuses[file_real]
            
        # 2. 相对路径匹配
        rel = ""
        try:
            rel = os.path.relpath(file_real, repo_real).replace('\\', '/').lower().strip('/')
            if rel == '.' or rel == '':
                rel = ""
            if rel and rel in state.fileStatuses:
                return state.fileStatuses[rel]
        except Exception:
            rel = ""
            
        # 3. 针对 README 的兼容匹配
        name = os.path.basename(file_path).lower()
        if name == "readme.md":
            for k, v in state.fileStatuses.items():
                if k.endswith("readme.md"):
                    return v

        # 4. 目录状态冒泡：利用 state.dirStatuses 进行 O(1) 检索，兼顾测试/mock对象的全量冒泡
        if os.path.isdir(file_path):
            if state.dirStatuses:
                if file_real in state.dirStatuses:
                    return state.dirStatuses[file_real]
                if rel and rel in state.dirStatuses:
                    return state.dirStatuses[rel]
                # 不在变动目录集合中，继续向下判断父级继承，最终返回 'clean'，避免绿点异常消失
            else:
                priority = {'conflicted': 4, 'unstaged': 3, 'staged': 2, 'untracked': 1}
                best_status = None
                best_priority = 0
                prefix_abs = file_real.rstrip('/') + '/'
                prefix_rel = (rel.rstrip('/') + '/') if rel else ""
                for path_key, status in state.fileStatuses.items():
                    norm = path_key.replace('\\', '/').lower()
                    if norm.startswith(prefix_abs) or (prefix_rel and norm.startswith(prefix_rel)):
                        p = priority.get(status, 0)
                        if p > best_priority:
                            best_priority = p
                            best_status = status
                if best_status:
                    return best_status
            
        # 5. 父级状态继承（未跟踪或忽略目录向下传播）
        curr = file_real
        while len(curr) > len(repo_real):
            curr = os.path.dirname(curr).replace('\\', '/').lower()
            if curr in state.fileStatuses:
                p_st = state.fileStatuses[curr]
                if p_st in ('untracked', 'ignored'):
                    return p_st
        return 'clean'

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SyncTree (Beta)")
        self.setWindowIcon(QIcon(get_resource_path("logo.png")))
        self.resize(800, 820)
        self.setStyleSheet(QSS)
        
        self.poller = GitPoller()
        self.actions = GitActions(self.poller)
        self.current_state = None
        
        self._setup_ui()
        self._bind_signals()
        
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
        
        self.btn_switch = QPushButton("⇄")
        self.btn_switch.setFixedSize(24, 24)
        self.btn_switch.setToolTip(tr("switch_branch"))
        self.btn_switch.setStyleSheet(f"QPushButton {{ border: none; background: transparent; color: {COLORS['primary']}; font-size: 16px; font-weight: bold; padding: 0; }} QPushButton:hover {{ color: {COLORS['text']}; }}")
        self.btn_switch.clicked.connect(self._switch_branch)
        header_layout.addWidget(self.btn_switch)
        
        header_layout.addSpacing(16)
        header_layout.addLayout(right_layout)
        main_layout.addLayout(header_layout)
        
        # Splitter (Graph View + File Tree View)
        top_splitter = QSplitter(Qt.Horizontal)
        self.graph = GraphView()
        
        right_panel = QWidget()
        right_tree_layout = QHBoxLayout(right_panel)
        right_tree_layout.setContentsMargins(0, 0, 0, 0)
        right_tree_layout.setSpacing(8)
        
        self.file_model = GitFileModel(self)
        self.file_model.setRootPath("")
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setStyleSheet(f"background-color: {COLORS['surface']}; color: {COLORS['text']}; border: none; border-radius: 8px; padding: 4px;")
        self.file_tree.setHeaderHidden(True)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        for i in range(1, 4):
            self.file_tree.hideColumn(i)
        self.file_tree.doubleClicked.connect(self._open_file)
        self.file_tree.clicked.connect(self._on_file_clicked)
        self.file_tree.customContextMenuRequested.connect(self._show_context_menu)
            
        right_tree_layout.addWidget(self.file_tree, stretch=1)
        
        legend_layout = QVBoxLayout()
        legend_layout.setContentsMargins(4, 4, 4, 4)
        self.legend_labels = []
        
        # 统一图例与文件树圆点完全对应
        legend_items = [
            ("#4CAF50", "file_clean"),      # 绿：未修改
            ("#F44336", "file_unstaged"),   # 红：未暂存
            ("#FFEB3B", "file_staged"),     # 黄：已暂存
            ("#9E9E9E", "file_untracked"),  # 灰：未跟踪
            ("#FF5722", "file_conflicted")  # 橙：冲突未解决
        ]
        
        for color, key in legend_items:
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            
            dot = QLabel(f'<span style="color:{color}; font-size:16px;">●</span>')
            lbl = QLabel(tr(key))
            lbl.setStyleSheet(f"font-size:12px; color:{COLORS['text']};")
            
            h.addWidget(dot)
            h.addWidget(lbl)
            h.addStretch()
            
            legend_layout.addWidget(container)
            self.legend_labels.append((lbl, key))
        
        legend_layout.addStretch()
        
        logo_pixmap = QPixmap(get_resource_path("logo.png")).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_btn = AnimatedLogo(logo_pixmap)
        # 解除 Logo 上的直接破坏性操作绑定，仅保留点击动画彩蛋
        legend_layout.addWidget(self.logo_btn, alignment=Qt.AlignLeft)
        
        right_tree_layout.addLayout(legend_layout)
        
        top_splitter.addWidget(self.graph)
        top_splitter.addWidget(right_panel)
        top_splitter.setStretchFactor(0, 6)
        top_splitter.setStretchFactor(1, 4)
        
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
            
        for lbl, key in self.legend_labels:
            lbl.setText(tr(key))

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
            
        if self.poller.repo_path:
            root_idx = self.file_model.index(self.poller.repo_path)
            rows = self.file_model.rowCount(root_idx)
            if rows > 0:
                top_left = self.file_model.index(0, 0, root_idx)
                bottom_right = self.file_model.index(rows - 1, 0, root_idx)
                self.file_model.dataChanged.emit(top_left, bottom_right, [Qt.DecorationRole])
            self.file_tree.viewport().update()

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow():
                self.poller.trigger_update()
        super().changeEvent(event)

    def _switch_branch(self):
        if not self.current_state or not self.current_state.isRepo:
            return
            
        if self.current_state.hasModified or self.current_state.hasStaged:
            show_result_modal(self.overlay, False, tr("err_uncommitted_changes"))
            return
            
        choices = self.current_state.branches
        def do_switch(branch_name):
            out, err = self.actions.switch_branch(branch_name)
            if err:
                show_result_modal(self.overlay, False, f"{tr('switch_blocked')}:\n\n{err}")
                return False
            else:
                self.poller.trigger_update()
                self.toast.show_message(f"{tr('switched_to')}: {branch_name}")
                return True
                
        from ui.components.modals import show_branch_selection_modal
        show_branch_selection_modal(self.overlay, tr("switch_branch"), choices, do_switch)

    BLOCKED_EXTS = {'.exe', '.bat', '.cmd', '.ps1', '.vbs', '.vbe', '.jse', '.wsf', '.wsh', '.msc', '.com', '.scr', '.pif'}

    def _safe_open_file(self, full_path):
        if not full_path or not os.path.isfile(full_path):
            return
        ext = os.path.splitext(full_path)[1].lower()
        if ext in self.BLOCKED_EXTS:
            show_result_modal(self.overlay, False, tr("executable_blocked_warning"))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))

    def _open_file(self, index):
        path = self.file_model.filePath(index)
        self._safe_open_file(path)

    def _on_file_clicked(self, index):
        pass

    def _perform_search(self):
        query = self.search_input.text().strip().lower()
        if not query or not self.poller.repo_path:
            return
            
        out, err = self.actions.run_cmd(["ls-files", "--cached", "--others", "--exclude-standard"])
        if not out:
            return
            
        results = []
        for line in out.splitlines():
            line = line.strip()
            if line and query in os.path.basename(line).lower():
                results.append(line)
        
        show_search_results_modal(self.overlay, query, results, self.poller.repo_path, self._open_search_file)
        self.search_input.clear()

    def _show_context_menu(self, pos):
        index = self.file_tree.indexAt(pos)
        if not index.isValid():
            return
            
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {COLORS['surface']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 4px; }}
            QMenu::item {{ padding: 6px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {COLORS['primary']}40; color: {COLORS['primary']}; }}
        """)
        
        rename_act = menu.addAction(tr("rename"))
        delete_act = menu.addAction(tr("delete"))
        
        action = menu.exec(self.file_tree.mapToGlobal(pos))
        if action == rename_act:
            self._rename_item(index)
        elif action == delete_act:
            self._delete_item(index)

    def _rename_item(self, index):
        old_path = self.file_model.filePath(index)
        old_name = os.path.basename(old_path)
        
        def do_rename(new_name):
            new_name = new_name.strip() if new_name else ""
            if not new_name or new_name == old_name:
                return False
            
            # 路径穿越与合法性校验
            if new_name != os.path.basename(new_name) or any(c in '<>:"/\\|?*' for c in new_name):
                show_result_modal(self.overlay, False, tr("invalid_filename"))
                return False
                
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if os.path.exists(new_path):
                show_result_modal(self.overlay, False, tr("file_exists"))
                return False
                
            try:
                rel_old = os.path.relpath(old_path, self.poller.repo_path).replace('\\', '/')
                rel_new = os.path.relpath(new_path, self.poller.repo_path).replace('\\', '/')
                out, err = self.actions.run_cmd(["mv", rel_old, rel_new])
                if err:
                    os.rename(old_path, new_path)
                self.poller.trigger_update()
                self.toast.show_message(f"Renamed: {new_name}")
                return True
            except Exception as e:
                show_result_modal(self.overlay, False, f"Rename failed: {e}")
                return False
                
        show_input_modal(self.overlay, tr("rename"), do_rename)

    def _delete_item(self, index):
        path = self.file_model.filePath(index)
        if not path or not self.poller.repo_path:
            return
            
        repo_real = os.path.normcase(os.path.realpath(self.poller.repo_path))
        path_real = os.path.normcase(os.path.realpath(path))
        
        # 禁止删除仓库根目录
        if path_real == repo_real:
            show_result_modal(self.overlay, False, tr("cannot_delete_root"))
            return
            
        # 禁止删除非仓库内部文件 (防范符号链接与大小写逃逸)
        try:
            common = os.path.normcase(os.path.commonpath([repo_real, path_real]))
            if common != repo_real:
                show_result_modal(self.overlay, False, tr("cannot_delete_outside"))
                return
        except ValueError:
            show_result_modal(self.overlay, False, tr("cannot_delete_outside"))
            return
            
        name = os.path.basename(path)
        
        def do_delete():
            rel_path = os.path.relpath(path, self.poller.repo_path).replace('\\', '/')
            args = ["rm", "-r", "--force", "--", rel_path] if os.path.isdir(path) else ["rm", "--force", "--", rel_path]
            out, err = self.actions.run_cmd(args)
            
            if err:
                try:
                    import shutil
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    self.poller.trigger_update()
                    self.toast.show_message(f"Deleted: {name}")
                except Exception as e:
                    show_result_modal(self.overlay, False, f"Delete failed: {e}")
            else:
                self.toast.show_message(f"Git Deleted: {name}")
                
        msg = tr("delete_warning").format(name)
        dialog = BaseDialogMsg(tr("confirm_delete"), self.overlay)
        lbl = QLabel(msg)
        lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        lbl.setWordWrap(True)
        dialog.vbox.addWidget(lbl)
        dialog.add_buttons(on_confirm=do_delete)
        self.overlay.set_content(dialog)
        self.overlay.show_animated()

    def _open_search_file(self, rel_path):
        full_path = os.path.join(self.poller.repo_path, rel_path)
        self._safe_open_file(full_path)

    def _handle_panel_action(self, action, payload):
        if action == "change_repo":
            self.change_repo(payload["path"])
        elif action == "set_remote":
            out, err = self.actions.set_remote(payload["url"])
            if err:
                show_result_modal(self.overlay, False, f"{tr('config_remote_failed')}:\n\n{err}")
        elif action == "sync":
            out, err = self.actions.sync_latest()
            if err:
                show_result_modal(self.overlay, False, f"{tr('sync_failed')}\n\n{err}", lambda: show_diag_modal(self.overlay))
            else:
                show_result_modal(self.overlay, True, tr("sync_success"))
        elif action == "terminal_error":
            show_result_modal(self.overlay, False, payload.get("msg", "Terminal launch failed."))
        elif action == "branch":
            def do_branch(name):
                name = name.strip()
                is_valid, err_msg = self.actions.is_valid_branch_name(name)
                if not is_valid:
                    show_result_modal(self.overlay, False, err_msg)
                    return False
                out, err = self.actions.create_branch(name)
                if err:
                    show_result_modal(self.overlay, False, f"Failed: {err}")
                else:
                    show_result_modal(self.overlay, True, tr("branch_success") + f": {name}")
                return False
            show_input_modal(self.overlay, tr("enter_task_name"), do_branch)
        elif action == "branch_history":
            if self.current_state:
                out, err = self.actions.run_cmd(["log", "--all", "--oneline", "--no-color", "-n", "50"])
                choices = out.splitlines() if out else []
                def do_branch_hist(name, hash_val):
                    o, e = self.actions.create_branch(name, hash_val)
                    if e:
                        show_result_modal(self.overlay, False, f"{tr('branch_failed')}\n\n{e}")
                    else:
                        show_result_modal(self.overlay, True, tr("branch_success") + f": {name}")
                    return False
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
                if not msg.strip():
                    show_result_modal(self.overlay, False, tr("commit_msg_empty"))
                    return False
                out, err = self.actions.commit(msg)
                if err:
                    show_result_modal(self.overlay, False, f"{tr('commit_failed')}\n\n{err}")
                else:
                    show_result_modal(self.overlay, True, tr("commit_success"))
                return False
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

    def _handle_cleanup_safe(self):
        """显式安全清理入口（支持 dry-run 预览与二次确认）"""
        out, err = self.actions.preview_cleanup()
        if not out or not out.strip():
            self.toast.show_message(tr("no_garbage"))
            return
            
        dialog = BaseDialogMsg(tr("cleanup_title"), self.overlay)
        warning_lbl = QLabel(tr("cleanup_warning"))
        warning_lbl.setStyleSheet(f"color: {COLORS['error']}; font-weight: bold;")
        warning_lbl.setWordWrap(True)
        dialog.vbox.addWidget(warning_lbl)
        
        preview_lbl = QLabel(out[:400] + ("..." if len(out) > 400 else ""))
        preview_lbl.setStyleSheet(f"color: {COLORS['text_disabled']}; font-size: 12px; font-family: Consolas;")
        preview_lbl.setWordWrap(True)
        dialog.vbox.addWidget(preview_lbl)
        
        def confirm_cleanup():
            self.cleanup_thread = CleanupThread(self.actions, self)
            self.cleanup_thread.finished.connect(lambda o, e: self.toast.show_message(tr("cleanup_done")))
            self.cleanup_thread.start()
            
        dialog.add_buttons(on_confirm=confirm_cleanup)
        self.overlay.set_content(dialog)
        self.overlay.show_animated()

    def _set_new_cloned_repo(self, new_dir):
        new_dir = new_dir.replace('\\', '/')
        self.panel.line_local.setText(new_dir)
        self.panel.config["local_path"] = new_dir
        from core.config import save_config
        save_config(self.panel.config)
        self.change_repo(new_dir)

    def change_repo(self, path):
        path = os.path.realpath(path).replace('\\', '/') if path else path
        if path and os.path.exists(path):
            if not os.path.exists(os.path.join(path, ".git")):
                def do_init():
                    self._setup_repo_path(path)
                    self.actions.init_repo()
                    self.toast.show_message(tr("auto_init"))
                    
                def do_clone():
                    def perform_clone(url):
                        url = url.strip()
                        self.panel.line_remote.setText(url)
                        self.panel.config["remote_url"] = url
                        self.toast.show_message(tr("cloning_wait"))
                        
                        # 记录克隆前的已有子文件夹与预期的仓库名
                        match = re.search(r'/([^/]+?)(?:\.git)?$', url.rstrip('/'))
                        expected_repo_name = match.group(1) if match else None
                        existing_subdirs = set(
                            d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))
                        )
                        
                        from PySide6.QtCore import QThread, Signal
                        class CloneThread(QThread):
                            res_ready = Signal(object)
                            def __init__(self, c_url, c_cwd, parent=None):
                                super().__init__(parent)
                                self.url = c_url
                                self.cwd = c_cwd
                                self.proc = None

                            def run(self):
                                import subprocess, os
                                cr = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                                try:
                                    self.proc = subprocess.Popen(
                                        ["git", "clone", self.url],
                                        cwd=self.cwd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True,
                                        creationflags=cr,
                                        encoding='utf-8',
                                        errors='replace'
                                    )
                                    out, err = self.proc.communicate()
                                    from collections import namedtuple
                                    Result = namedtuple("Result", ["returncode", "stdout", "stderr"])
                                    self.res_ready.emit(Result(self.proc.returncode, out, err))
                                except Exception as e:
                                    from collections import namedtuple
                                    Result = namedtuple("Result", ["returncode", "stdout", "stderr"])
                                    self.res_ready.emit(Result(1, "", str(e)))

                            def cancel(self):
                                if self.proc and self.proc.poll() is None:
                                    try:
                                        self.proc.terminate()
                                    except Exception:
                                        try:
                                            self.proc.kill()
                                        except Exception:
                                            pass
                                
                        def on_clone_done(res):
                            if res.returncode == 0:
                                current_subdirs = set(
                                    d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))
                                )
                                new_dirs = current_subdirs - existing_subdirs
                                
                                # 优先尝试新生成的目录
                                if len(new_dirs) == 1:
                                    target_dir = os.path.join(path, list(new_dirs)[0])
                                    self._set_new_cloned_repo(target_dir)
                                    self.toast.show_message(tr("clone_success"))
                                    return
                                    
                                # 其次尝试从 URL 提取的预期项目名
                                if expected_repo_name:
                                    expected_full = os.path.join(path, expected_repo_name)
                                    if os.path.isdir(expected_full):
                                        self._set_new_cloned_repo(expected_full)
                                        self.toast.show_message(tr("clone_success"))
                                        return
                                        
                                # 目录判断不确定
                                if len(current_subdirs) >= 1:
                                    self.toast.show_message(tr("clone_dir_ambiguous"))
                                else:
                                    self.toast.show_message(tr("clone_subfolder_not_found"))
                            else:
                                show_result_modal(self.overlay, False, f"{tr('clone_failed')}:\n{res.stderr}")
                                
                        self._clone_thread = CloneThread(url, path, self)
                        self._clone_thread.res_ready.connect(on_clone_done)
                        self._clone_thread.start()
                        
                    show_input_modal(self.overlay, tr("enter_remote_url"), perform_clone)
                    
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
        path = os.path.normpath(path)
        self.poller.reset_watcher()
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
        if hasattr(self, '_clone_thread') and self._clone_thread and self._clone_thread.isRunning():
            if hasattr(self._clone_thread, 'cancel'):
                self._clone_thread.cancel()
            self._clone_thread.quit()
            self._clone_thread.wait(1000)
        if hasattr(self, 'cleanup_thread') and self.cleanup_thread and self.cleanup_thread.isRunning():
            self.cleanup_thread.quit()
            self.cleanup_thread.wait(1000)
        super().closeEvent(event)
