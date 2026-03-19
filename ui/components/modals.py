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

class DiagModalContent(QWidget):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        self.setAttribute(Qt.WA_StyledBackground)
        self.setObjectName("DiagContainer")
        self.setStyleSheet(f"#DiagContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        self.setFixedWidth(420)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title = QLabel(tr("diag_title"))
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        self.rows = []
        labels = [
            tr("nic_test"),
            tr("dns_test"),
            tr("ip_test"),
            tr("port_test"),
            tr("gfw_test")
        ]
        
        for text in labels:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(16, 12, 16, 12)
            row_l.setSpacing(16)
            
            dot = SpinnerDot()
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: 500;")
            
            status_lbl = QLabel("")
            status_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
            
            row_l.addWidget(dot)
            row_l.addWidget(lbl)
            row_l.addStretch()
            row_l.addWidget(status_lbl)
            layout.addWidget(row_w)
            
            self.rows.append((dot, status_lbl))
            
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
        
        from core.network_diag import NetworkDiagThread
        self.thread = NetworkDiagThread(self)
        self.thread.step_updated.connect(self.update_step)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()
        
    def update_step(self, step, status):
        dot, status_lbl = self.rows[step]
        dot.set_status(status)
        if status == 0:
            status_lbl.setText("")
        elif status == 1:
            if step == len(self.rows) - 1:
                status_lbl.setText(tr("status_not_exist"))
            else:
                status_lbl.setText(tr("status_normal"))
            status_lbl.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        elif status == 2:
            if step == len(self.rows) - 1:
                status_lbl.setText(tr("status_exist"))
            else:
                status_lbl.setText(tr("status_abnormal"))
            status_lbl.setStyleSheet("color: #F44336; font-size: 14px; font-weight: bold;")

    def on_thread_finished(self):
        self.btn_retest.show()
        self.btn_close.show()

    def restart_diag(self):
        self.btn_retest.hide()
        self.btn_close.hide()
        for dot, status_lbl in self.rows:
            dot.set_status(-1)
            status_lbl.setText("")
        self.thread.wait()
        self.thread.start()

    def close_diag(self):
        self.thread.wait()
        self.overlay.hide_animated()

def show_diag_modal(overlay):
    content = DiagModalContent(overlay)
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

