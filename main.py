import sys
import os
import time
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPixmap, QPainter

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class RotatingLogo(QWidget):
    def __init__(self, pix_path, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.pixmap = QPixmap(pix_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._rotation = 0
        
        self.anim = QPropertyAnimation(self, b"rotation")
        self.anim.setDuration(1500)
        self.anim.setStartValue(0)
        self.anim.setEndValue(360)
        self.anim.setLoopCount(-1) # Continuous
        self.anim.setEasingCurve(QEasingCurve.Linear)
        self.anim.start()

    @Property(float)
    def rotation(self): return self._rotation
    @rotation.setter
    def rotation(self, val):
        self._rotation = val
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        center = self.rect().center()
        painter.translate(center)
        painter.rotate(self._rotation)
        painter.translate(-center)
        
        # Draw pixmap centered
        x = (self.width() - self.pixmap.width()) // 2
        y = (self.height() - self.pixmap.height()) // 2
        painter.drawPixmap(x, y, self.pixmap)
        painter.end()

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(460, 280)
        
        from ui.theme import COLORS
        from core.i18n import tr

        container = QWidget(self)
        container.setFixedSize(self.size())
        container.setObjectName("SplashContainer")
        container.setStyleSheet(f"#SplashContainer {{ background-color: {COLORS['surface']}; border-radius: 16px; border: 1px solid {COLORS['border']}; }}")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        self.logo = RotatingLogo(get_resource_path("logo.png"))
        layout.addWidget(self.logo)
        
        title = QLabel("SyncTree")
        title.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {COLORS['text']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel(tr("app_subtitle"))
        subtitle.setStyleSheet(f"font-size: 15px; color: {COLORS['text_disabled']};")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
        author_lbl = QLabel(f'<span style="color: {COLORS["text"]}; font-size: 15px; font-weight: bold;">{tr("author")} </span><span style="color: {COLORS["primary"]}; font-size: 15px; font-weight: bold;">Andrew Wang Dev</span>')
        author_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_lbl)


def main():
    # Make sure we run from the script directory for config.json to behave well
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Optional styling or High DPI scaling - MUST be before QApplication
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    start_time = time.time()
    
    from ui.window import MainWindow
    window = MainWindow()
    
    elapsed = time.time() - start_time
    delay = max(0, 1200 - int(elapsed * 1000))
    
    QTimer.singleShot(delay, lambda: [splash.close(), window.show()])
    
    sys.exit(app.exec())

if __name__ == "__main__":
    # Qt is needed for the high-dpi check, but we import it lazily or globally
    main()
