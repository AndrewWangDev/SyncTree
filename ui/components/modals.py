from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox
from PySide6.QtGui import QPainter, QColor, QBrush, QPaintEvent, QPen
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal
from ui.theme import COLORS
from ui.components.buttons import MaterialButton
from core.i18n import tr

class ModalOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        # Block inputs from passing to parent
        self.setFocusPolicy(Qt.StrongFocus)
        self.hide()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)
        
        self._bg_opacity = 0
        self.anim = QPropertyAnimation(self, b"bgOpacity")
        
        self.content_widget = None

    @Property(float)
    def bgOpacity(self): return self._bg_opacity
    
    @bgOpacity.setter
    def bgOpacity(self, val):
        self._bg_opacity = val
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        color = QColor(0, 0, 0)
        color.setAlphaF(self._bg_opacity)
        painter.fillRect(self.rect(), color)

    def set_content(self, widget):
        if self.content_widget:
            self.main_layout.removeWidget(self.content_widget)
            self.content_widget.deleteLater()
            
        widget.setParent(self)
        self.main_layout.addWidget(widget)
        self.content_widget = widget

    def show_animated(self):
        self.resize(self.parent().size())
        self.show()
        self.raise_()
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(0.6)
        self.anim.setDuration(250)
        self.anim.start()

    def hide_animated(self):
        self.anim.stop()
        self.anim.setStartValue(self._bg_opacity)
        self.anim.setEndValue(0)
        self.anim.setDuration(250)
        self.anim.finished.connect(lambda: self.hide() if self._bg_opacity==0 else None)
        self.anim.start()

    def resizeEvent(self, e):
        if self.parent():
            self.resize(self.parent().size())

class BaseDialogMsg(QWidget):
    def __init__(self, title, overlay):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("BaseDialog")
        self.setStyleSheet(f"#BaseDialog {{ background: {COLORS['surface']}; border-radius: 12px; border: 1px solid {COLORS['border']}; }}")
        self.setFixedWidth(320)
        
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(20, 20, 20, 20)
        self.vbox.setSpacing(16)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']}; border: none;")
        self.vbox.addWidget(title_lbl)

    def add_buttons(self, on_confirm, on_cancel=None):
        hbs = QHBoxLayout()
        hbs.addStretch()
        
        cancel = MaterialButton(tr("cancel"))
        cancel.clicked.connect(lambda: [self.overlay.hide_animated(), on_cancel() if on_cancel else None])
        
        confirm = MaterialButton(tr("confirm"), is_primary=True)
        confirm.clicked.connect(lambda: [on_confirm(), self.overlay.hide_animated()])
        
        hbs.addWidget(cancel)
        hbs.addWidget(confirm)
        self.vbox.addLayout(hbs)

def show_input_modal(overlay, title, callback):
    dialog = BaseDialogMsg(title, overlay)
    
    line_edit = QLineEdit()
    line_edit.setPlaceholderText("...")
    dialog.vbox.addWidget(line_edit)
    
    dialog.add_buttons(on_confirm=lambda: callback(line_edit.text()))
    overlay.set_content(dialog)
    overlay.show_animated()

def show_history_branch_modal(overlay, title, history_choices, callback):
    dialog = BaseDialogMsg(title, overlay)
    
    combo = QComboBox()
    combo.setStyleSheet(f"background: {COLORS['surface_variant']}; color: {COLORS['text']}; padding: 8px; border-radius: 8px;")
    combo.addItems(history_choices)
    dialog.vbox.addWidget(combo)
    
    line_edit = QLineEdit()
    line_edit.setPlaceholderText(tr("enter_task_name"))
    dialog.vbox.addWidget(line_edit)
    
    def confirm():
        # Extracted choice format is usually: "hash msg"
        choice = combo.currentText()
        if choice:
            hash_val = choice.split(' ', 1)[0].replace('*', '').replace('|', '').replace('\\', '').replace('/', '').strip()
            callback(line_edit.text(), hash_val)
            
    dialog.add_buttons(on_confirm=confirm)
    overlay.set_content(dialog)
    overlay.show_animated()

from PySide6.QtCore import QTimer

class SpinnerDot(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(20, 20)
        self.status = -1 # -1: hidden/waiting, 0: spinning, 1: ok, 2: fail
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        
    def rotate(self):
        if self.status == 0:
            self.angle = (self.angle + 30) % 360
            self.update()
            
    def set_status(self, s):
        self.status = s
        if s == 0:
            self.timer.start(50)
        else:
            self.timer.stop()
        self.update()

    def paintEvent(self, event):
        if self.status == -1: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.status == 0:
            pen = QPen(QColor(COLORS['primary']), 3)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(2, 2, 16, 16, -self.angle * 16, 100 * 16)
        elif self.status == 1:
            pen = QPen(QColor("#4CAF50"), 3)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(4, 11, 8, 15)
            painter.drawLine(8, 15, 15, 5)
        elif self.status == 2:
            pen = QPen(QColor("#F44336"), 3)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(5, 5, 15, 15)
            painter.drawLine(15, 5, 5, 15)
        elif self.status == 3:
            pen = QPen(QColor("#FFC107"), 3)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(10, 4, 10, 12)
            painter.drawPoint(10, 16)

class EnvDiagModalContent(QWidget):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("DiagContainer")
        self.setStyleSheet(f"#DiagContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        self.setFixedWidth(460)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        
        lbl_dev = QLabel(tr("dev_diag"))
        lbl_dev.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['primary']}; margin-top: 8px;")
        layout.addWidget(lbl_dev)
        
        self.rows = []
        
        def add_row(text):
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(16, 4, 16, 4)
            row_l.setSpacing(16)
            
            dot = SpinnerDot()
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
            
            status_lbl = QLabel("")
            status_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
            
            row_l.addWidget(dot)
            row_l.addWidget(lbl)
            row_l.addStretch()
            row_l.addWidget(status_lbl)
            layout.addWidget(row_w)
            
            self.rows.append((dot, lbl, status_lbl, text))
            
        add_row(tr("qq_test"))
        
        lbl_net = QLabel(tr("net_diag"))
        lbl_net.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['primary']}; margin-top: 12px;")
        layout.addWidget(lbl_net)

        add_row(tr("nic_test"))
        add_row(tr("dns_test"))
        add_row(tr("ip_test"))
        add_row(tr("port_test"))
        add_row(tr("gfw_test"))
        
        lbl_basic = QLabel(tr("basic_config"))
        lbl_basic.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLORS['primary']}; margin-top: 12px;")
        layout.addWidget(lbl_basic)
        
        add_row(tr("git_user_test"))
        add_row(tr("ssh_test"))
        
        self.conclusion_lbl = QLabel("")
        self.conclusion_lbl.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 12px; color: #E3E3E3;")
        self.conclusion_lbl.setWordWrap(True)
        self.conclusion_lbl.hide()
        layout.addWidget(self.conclusion_lbl)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_retest = MaterialButton(tr("retest"))
        self.btn_retest.clicked.connect(self.restart_diag)
        self.btn_retest.hide()
        
        self.btn_close = MaterialButton(tr("done"), is_primary=True)
        self.btn_close.clicked.connect(self.close_diag)
        self.btn_close.hide()
        
        btn_layout.addWidget(self.btn_retest)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        from core.network_diag import EnvDiagThread
        self.thread = EnvDiagThread(self)
        self.thread.step_updated.connect(self.update_step)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()
        
    def update_step(self, step, status, text):
        dot, lbl, status_lbl, initial_text = self.rows[step]
        dot.set_status(status)
        if text:
            lbl.setText(text)
        
        if status == 0:
            status_lbl.setText("")
        elif status == 1:
            if step == 0:
                status_lbl.setText(tr("status_not_exist") if "否" in text else tr("status_normal"))
            elif step >= 1 and step <= 5:
                if step == 5:
                    status_lbl.setText(tr("status_not_exist"))
                else:
                    status_lbl.setText(tr("status_normal"))
            else:
                status_lbl.setText("已配置")
            status_lbl.setStyleSheet("color: #4CAF50;")
        elif status == 2:
            if step >= 1 and step <= 5:
                if step == 5:
                    status_lbl.setText(tr("status_exist"))
                else:
                    status_lbl.setText(tr("status_abnormal"))
            else:
                status_lbl.setText("未配置")
            status_lbl.setStyleSheet("color: #F44336;")
        elif status == 3:
            if step == 0:
                status_lbl.setText("是")
                status_lbl.setStyleSheet("color: #FFC107;")
            elif step == 7:
                status_lbl.setText("未检测")
                status_lbl.setStyleSheet("color: #FFC107;")
            else:
                status_lbl.setText(tr("status_abnormal"))
                status_lbl.setStyleSheet("color: #FFC107;")

    def on_thread_finished(self):
        self.btn_retest.show()
        self.btn_close.show()
        
        conclusions = []
        if self.thread.property("err_git_user"):
            conclusions.append("未配置Git用户")
        if self.thread.property("err_ssh"):
            conclusions.append("未配置SSH密钥对")
        if self.thread.property("err_dns"):
            conclusions.append("可能存在运营商干扰")
        if self.thread.property("err_gfw"):
            conclusions.append("可能存在GFW（墙）干扰")
        if self.thread.property("err_qq"):
            conclusions.append("存在不安全的中国软件，建议关闭")
            
        self.conclusion_lbl.show()
        if not conclusions:
            self.conclusion_lbl.setText(tr("conclusion") + " " + "完全正常")
            self.conclusion_lbl.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 12px; color: #4CAF50;")
        else:
            self.conclusion_lbl.setText(tr("conclusion") + " " + "，".join(conclusions))
            self.conclusion_lbl.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 12px; color: #FFC107;")

    def restart_diag(self):
        self.btn_retest.hide()
        self.btn_close.hide()
        self.conclusion_lbl.hide()
        for dot, lbl, status_lbl, initial_text in self.rows:
            dot.set_status(-1)
            lbl.setText(initial_text)
            status_lbl.setText("")
        self.thread.wait()
        self.thread.start()

    def close_diag(self):
        self.thread.wait()
        self.overlay.hide_animated()

def show_diag_modal(overlay):
    content = EnvDiagModalContent(overlay)
    overlay.set_content(content)
    overlay.show_animated()

class EmptyFolderModalContent(QWidget):
    def __init__(self, overlay, on_init, on_clone, on_cancel):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("EmptyFolderContainer")
        self.setStyleSheet(f"#EmptyFolderContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        self.setFixedWidth(420)
        self.setMinimumHeight(280)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        lbl_title = QLabel(tr("empty_folder_title") if tr("empty_folder_title") != "empty_folder_title" else "未检测到Git仓库")
        lbl_title.setStyleSheet(f"color: {COLORS['text']}; font-size: 20px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(lbl_title, alignment=Qt.AlignCenter)
        
        lbl_desc = QLabel(tr("empty_folder_desc") if tr("empty_folder_desc") != "empty_folder_desc" else "您选择的路径为空或尚未初始化为Git仓库。")
        lbl_desc.setStyleSheet(f"color: {COLORS['text_disabled']}; font-size: 14px;")
        lbl_desc.setWordWrap(True)
        lbl_desc.setMinimumHeight(40)
        layout.addWidget(lbl_desc, alignment=Qt.AlignCenter)
        
        layout.addSpacing(16)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(16)
        
        btn_init = MaterialButton(tr("btn_init_local") if tr("btn_init_local") != "btn_init_local" else "我要新建本地仓库", is_primary=True)
        btn_init.clicked.connect(lambda: [self.overlay.hide_animated(), on_init()])
        
        btn_clone = MaterialButton(tr("btn_clone_remote") if tr("btn_clone_remote") != "btn_clone_remote" else "我已有远程仓库", is_primary=True)
        btn_clone.clicked.connect(lambda: [self.overlay.hide_animated(), on_clone()])
        
        btn_cancel = MaterialButton(tr("cancel"))
        btn_cancel.clicked.connect(lambda: [self.overlay.hide_animated(), on_cancel() if on_cancel else None])
        
        btn_layout.addWidget(btn_init)
        btn_layout.addWidget(btn_clone)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)

def show_empty_folder_modal(overlay, on_init, on_clone, on_cancel=None):
    content = EmptyFolderModalContent(overlay, on_init, on_clone, on_cancel)
    overlay.set_content(content)
    overlay.show_animated()

class AboutModalContent(QWidget):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("AboutContainer")
        self.setStyleSheet(f"#AboutContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        self.setFixedWidth(460)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        logo_lbl = QLabel()
        from PySide6.QtGui import QPixmap
        import sys, os
        logo_path = os.path.join(sys._MEIPASS, "logo.png") if hasattr(sys, '_MEIPASS') else "logo.png"
        pix = QPixmap(logo_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_lbl.setPixmap(pix)
        logo_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_lbl)
        
        title = QLabel("SyncTree")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel(tr("app_subtitle"))
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS['text_disabled']};")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(8)
        
        author_lbl = QLabel(f'<a href="https://andrewwangdev.com/about" style="color: {COLORS["primary"]}; text-decoration: none;">{tr("author")}Andrew Wang Dev</a>')
        author_lbl.setAlignment(Qt.AlignCenter)
        author_lbl.setOpenExternalLinks(True)
        author_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(author_lbl)
        
        layout.addSpacing(8)
        
        links_layout = QHBoxLayout()
        links_layout.setAlignment(Qt.AlignCenter)
        links_layout.setSpacing(16)
        
        links = [
            (tr("open_source"), "https://github.com/AndrewWangDev/SyncTree"),
            (tr("terms_of_service"), "https://api.andrewwangdev.com/terms"),
            (tr("privacy_policy"), "https://api.andrewwangdev.com/privacy"),
            (tr("license_agreement"), "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html")
        ]
        
        for text, url in links:
            lbl = QLabel(f'<a href="{url}" style="color: {COLORS["secondary"]}; text-decoration: none;">{text}</a>')
            lbl.setOpenExternalLinks(True)
            lbl.setStyleSheet("font-size: 13px;")
            links_layout.addWidget(lbl)
            
        layout.addLayout(links_layout)
        
        layout.addSpacing(12)
        
        thanks_lbl = QLabel(tr("thanks_msg"))
        thanks_lbl.setStyleSheet(f"font-size: 13px; color: {COLORS['text_disabled']};")
        thanks_lbl.setAlignment(Qt.AlignCenter)
        thanks_lbl.setWordWrap(True)
        layout.addWidget(thanks_lbl)
        
        contact_lbl = QLabel(f'{tr("contact_us")} <a href="mailto:support@andrewwangdev.com" style="color: {COLORS["primary"]}; text-decoration: none;">support@andrewwangdev.com</a>')
        contact_lbl.setStyleSheet("font-size: 13px;")
        contact_lbl.setAlignment(Qt.AlignCenter)
        contact_lbl.setOpenExternalLinks(True)
        layout.addWidget(contact_lbl)
        
        layout.addSpacing(16)
        
        btn_l = QHBoxLayout()
        btn_l.addStretch()
        self.btn_close = MaterialButton(tr("close"), is_primary=True)
        self.btn_close.clicked.connect(self.overlay.hide_animated)
        btn_l.addWidget(self.btn_close)
        btn_l.addStretch()
        
        layout.addLayout(btn_l)

def show_about_modal(overlay):
    content = AboutModalContent(overlay)
    overlay.set_content(content)
    overlay.show_animated()

class SearchResultsModalContent(QWidget):
    def __init__(self, overlay, query, results, repo_path, open_callback):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("SearchContainer")
        self.setStyleSheet(f"#SearchContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        self.setFixedWidth(460)
        
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        
        title = QLabel(f"{tr('search_results')} - '{query}'")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']};")
        layout.addWidget(title)
        
        from PySide6.QtWidgets import QListWidget
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background: {COLORS['surface_variant']}; border: none; border-radius: 8px; outline: none; padding: 4px; }}
            QListWidget::item {{ padding: 8px 12px; border-radius: 6px; color: {COLORS['text']}; margin-bottom: 2px; }}
            QListWidget::item:hover {{ background: {COLORS['surface']}80; }}
            QListWidget::item:selected {{ background: {COLORS['primary']}40; color: {COLORS['primary']}; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['border']}; border-radius: 3px; min-height: 20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
        
        item_height = 34
        padding = 10
        list_height = min(260, max(50, len(results) * item_height + padding)) if results else 50
        self.list_widget.setFixedHeight(list_height)
        
        if not results:
            self.list_widget.addItem(tr("no_files_found"))
            self.list_widget.item(0).setFlags(Qt.NoItemFlags)
            self.list_widget.item(0).setForeground(QColor(COLORS['text_disabled']))
        else:
            for res in results:
                self.list_widget.addItem(res)
                
        self.list_widget.itemDoubleClicked.connect(lambda item: self._on_item_double_clicked(item, open_callback))
        layout.addWidget(self.list_widget)
        
        hint = QLabel(tr("double_click_hint"))
        hint.setStyleSheet(f"color: {COLORS['text_disabled']}; font-size: 12px;")
        layout.addWidget(hint)
        
        btn_l = QHBoxLayout()
        btn_l.addStretch()
        btn_close = MaterialButton(tr("close"), is_primary=True)
        btn_close.clicked.connect(self.overlay.hide_animated)
        btn_l.addWidget(btn_close)
        
        layout.addLayout(btn_l)

    def _on_item_double_clicked(self, item, open_callback):
        if item.flags() & Qt.ItemIsEnabled:
            open_callback(item.text())
            self.overlay.hide_animated()

def show_search_results_modal(overlay, query, results, repo_path, open_callback):
    content = SearchResultsModalContent(overlay, query, results, repo_path, open_callback)
    overlay.set_content(content)
    overlay.show_animated()

class ResultModalContent(QWidget):
    def __init__(self, overlay, is_success, message, diag_callback=None):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("ResultContainer")
        self.setStyleSheet(f"#ResultContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        self.setFixedWidth(380)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        if is_success:
            icon_lbl.setText("✅")
            icon_lbl.setStyleSheet("font-size: 48px;")
        else:
            icon_lbl.setText("❌")
            icon_lbl.setStyleSheet("font-size: 48px; color: #F44336;")
            
        layout.addWidget(icon_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"font-size: 15px; color: {COLORS['text']};")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)
        
        layout.addSpacing(8)
        
        btn_l = QHBoxLayout()
        btn_l.addStretch()
        
        from PySide6.QtCore import QTimer
        if not is_success and diag_callback:
            btn_diag = MaterialButton(tr("network_diag"))
            btn_diag.clicked.connect(lambda: [self.overlay.hide_animated(), QTimer.singleShot(260, diag_callback)])
            btn_l.addWidget(btn_diag)
            
        btn_close = MaterialButton(tr("close"), is_primary=is_success)
        btn_close.clicked.connect(self.overlay.hide_animated)
        btn_l.addWidget(btn_close)
        btn_l.addStretch()
        
        layout.addLayout(btn_l)
        
def show_result_modal(overlay, is_success, message, diag_callback=None):
    content = ResultModalContent(overlay, is_success, message, diag_callback)
    overlay.set_content(content)
    overlay.show_animated()

class DiffModalContent(QWidget):
    def __init__(self, overlay, filename, diff_text):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("DiffContainer")
        self.setStyleSheet(f"#DiffContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = QLabel(f"{tr('diff_view')}: {filename}")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text']};")
        layout.addWidget(title)
        
        from PySide6.QtWidgets import QTextEdit
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{ 
                background: {COLORS['surface_variant']}; 
                color: {COLORS['text']}; 
                border: none; 
                border-radius: 8px; 
                font-family: Consolas, monospace; 
                font-size: 13px; 
                padding: 12px; 
            }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: {COLORS['border']}; border-radius: 4px; min-height: 20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)
        
        html = []
        html.append("<pre style='margin:0; white-space:pre-wrap;'>")
        for line in diff_text.split('\\n'):
            escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if escaped.startswith('+'):
                html.append(f"<span style='color: #4CAF50;'>{escaped}</span>")
            elif escaped.startswith('-'):
                html.append(f"<span style='color: #F44336;'>{escaped}</span>")
            elif escaped.startswith('@@'):
                html.append(f"<span style='color: {COLORS['primary']};'>{escaped}</span>")
            else:
                html.append(f"<span style='color: {COLORS['text']};'>{escaped}</span>")
        html.append("</pre>")
        self.text_edit.setHtml("<br>".join(html))
        
        layout.addWidget(self.text_edit, stretch=1)
        
        btn_l = QHBoxLayout()
        btn_l.addStretch()
        btn_close = MaterialButton(tr("close"), is_primary=True)
        btn_close.clicked.connect(self.overlay.hide_animated)
        btn_l.addWidget(btn_close)
        
        layout.addLayout(btn_l)
        
def show_diff_modal(overlay, filename, diff_text):
    content = DiffModalContent(overlay, filename, diff_text)
    overlay.set_content(content)
    overlay.show_animated()
