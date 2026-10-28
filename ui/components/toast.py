from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from ui.theme import COLORS

class ToastLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        if not parent:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
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
        self.anim.finished.connect(self._on_anim_finished)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)
        
        self.hide()

    def _on_anim_finished(self):
        if self.opacity_effect.opacity() <= 0.01:
            self.hide()

    def show_message(self, text, duration=2000):
        self.label.setText(text)
        self.adjustSize()
        
        if self.parent():
            pos_x = (self.parent().width() - self.width()) // 2
            pos_y = self.parent().height() - self.height() - 40
            self.move(pos_x, pos_y)
            self.raise_()
            
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
        self.anim.start()
