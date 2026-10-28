from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, Property, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPaintEvent, QPen, QPainterPath, QPixmap
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
        
        if not self.isEnabled():
            painter.setOpacity(0.3)
            
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 12, 12)
        
        if self.is_primary:
            bg_color = QColor(COLORS["primary"])
            text_color = QColor(COLORS["on_primary"])
            ripple_color_base = "#FFFFFF"
        else:
            bg_color = QColor(COLORS["surface_variant"])
            text_color = QColor(COLORS["text"])
            ripple_color_base = COLORS["primary"]

        painter.fillPath(path, QBrush(bg_color))
        
        if self._ripple_opacity > 0:
            painter.setClipPath(path)
            ripple_color = QColor(ripple_color_base)
            ripple_color.setAlphaF(self._ripple_opacity)
            painter.setBrush(QBrush(ripple_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self._ripple_center, self._ripple_radius, self._ripple_radius)
            painter.setClipping(False)

        painter.setPen(QPen(text_color))
        font = self.font()
        font.setWeight(font.Weight.Medium if self.is_primary else font.Weight.Normal)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())
        
        painter.end()

class AnimatedLogo(QPushButton):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 80)
        self.setStyleSheet("background: transparent; border: none;")
        self.setCursor(Qt.PointingHandCursor)
        
        self.pixmap = pixmap
        self._rotation = 0
        self._cached_pixmap = None
        self._cached_size = None
        
        self.anim = QPropertyAnimation(self, b"rotation")
        self.anim.setDuration(1200)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)
        
    @Property(float)
    def rotation(self): return self._rotation
    @rotation.setter
    def rotation(self, val):
        self._rotation = val
        self.update()

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if self.rect().contains(e.position().toPoint()):
            if self.anim.state() == QPropertyAnimation.Stopped:
                self.anim.setStartValue(0)
                self.anim.setEndValue(720) # 2 rotations
                self.anim.start()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        center = self.rect().center()
        painter.translate(center)
        painter.rotate(self._rotation)
        painter.translate(-center)
        
        content_rect = self.rect().adjusted(4, 4, -4, -4)
        if self._cached_size != content_rect.size():
            self._cached_pixmap = self.pixmap.scaled(
                content_rect.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self._cached_size = content_rect.size()
        
        if self._cached_pixmap:
            x = (self.width() - self._cached_pixmap.width()) // 2
            y = (self.height() - self._cached_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._cached_pixmap)
        painter.end()
