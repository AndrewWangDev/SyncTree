from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, Property, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPaintEvent, QPen, QPainterPath, QPixmap, QTransform
from ui.theme import COLORS

class MaterialButton(QPushButton):
    def __init__(self, text="", parent=None, is_primary=False):
        super().__init__(text, parent)
        self.is_primary = is_primary
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        
        # Ripple animation
        self._ripple_radius = 0
        self._ripple_opacity = 0
        self._ripple_center = QPoint()
        
        self.anim_radius = QPropertyAnimation(self, b"rippleRadius")
        self.anim_opacity = QPropertyAnimation(self, b"rippleOpacity")
        
    @Property(float)
    def rippleRadius(self): return self._ripple_radius
    @rippleRadius.setter
    def rippleRadius(self, val):
        self._ripple_radius = val
        self.update()

    @Property(float)
    def rippleOpacity(self): return self._ripple_opacity
    @rippleOpacity.setter
    def rippleOpacity(self, val):
        self._ripple_opacity = val
        self.update()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self._ripple_center = e.position().toPoint()
        self._ripple_opacity = 0.4
        
        self.anim_radius.setStartValue(0)
        self.anim_radius.setEndValue(max(self.width(), self.height()) * 1.5)
        self.anim_radius.setDuration(400)
        self.anim_radius.setEasingCurve(QEasingCurve.OutQuad)
        
        self.anim_opacity.setStartValue(0.4)
        self.anim_opacity.setEndValue(0)
        self.anim_opacity.setDuration(400)
        
        self.anim_radius.start()
        self.anim_opacity.start()

    def paintEvent(self, e: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Handle disabled opacity explicitly
        if not self.isEnabled():
            painter.setOpacity(0.3)
            
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)
        
        # Fill Background - Unify all to dark surface variant
        bg_color = QColor(COLORS["surface_variant"])
        painter.fillPath(path, QBrush(bg_color))
        
        # Draw Ripple
        if self._ripple_opacity > 0:
            painter.setClipPath(path)
            ripple_color = QColor(COLORS["primary"])
            ripple_color.setAlphaF(self._ripple_opacity)
            painter.setBrush(QBrush(ripple_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self._ripple_center, self._ripple_radius, self._ripple_radius)
            painter.setClipping(False)

        # Draw Text
        text_color = QColor(COLORS["text"])
        painter.setPen(QPen(text_color))
        font = self.font()
        font.setWeight(font.Weight.Medium if self.is_primary else font.Weight.Normal)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())
        
        painter.end()

class AnimatedLogo(QPushButton):
    clicked = Signal()

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 80)
        self.setStyleSheet("background: transparent; border: none;")
        self.setCursor(Qt.PointingHandCursor)
        
        self.pixmap = pixmap
        self._rotation = 0
        
        self.anim = QPropertyAnimation(self, b"rotation")
        self.anim.setDuration(1200)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        
    @Property(float)
    def rotation(self): return self._rotation
    @rotation.setter
    def rotation(self, val):
        self._rotation = val
        self.update()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if self.anim.state() == QPropertyAnimation.Stopped:
            self.anim.setStartValue(0)
            self.anim.setEndValue(720) # 2 rotations
            self.anim.start()
            self.clicked.emit()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        center = self.rect().center()
        painter.translate(center)
        painter.rotate(self._rotation)
        painter.translate(-center)
        
        # Calculate aspect ratio preserving rect
        content_rect = self.rect().adjusted(4, 4, -4, -4)
        scaled_pixmap = self.pixmap.scaled(content_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Center the scaled pixmap
        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2
        
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()
