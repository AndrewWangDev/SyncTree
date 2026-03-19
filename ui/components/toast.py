from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from ui.theme import COLORS

class ToastLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.label = QLabel()
        self.label.setStyleSheet(f"""
            background-color: {COLORS['text']};
            color: {COLORS['background']};
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
        """)
        self.label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)
        
        self.hide()

    def show_message(self, text, duration=2000):
        self.label.setText(text)
        self.adjustSize()
        
        # Center at the bottom of the parent if exists
        if self.parent():
            parent_rect = self.parent().rect()
            pos_x = parent_rect.center().x() - self.width() // 2
            pos_y = parent_rect.bottom() - self.height() - 40
            self.move(self.parent().mapToGlobal(self.parent().rect().topLeft()) + QPoint(pos_x, pos_y))
            
        self.show()
        
        self.anim.stop()
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(1)
        self.anim.start()
        
        self.timer.start(duration)
        
    def hide_toast(self):
        self.anim.stop()
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(0)
        self.anim.finished.connect(self.hide)
        self.anim.start()
