from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap


def create_app_icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, 128, 128)
    gradient.setColorAt(0, QColor("#1A1A1A"))
    gradient.setColorAt(1, QColor("#0F5C64"))
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor("#74FBD3"), 4))
    painter.drawRoundedRect(8, 8, 112, 112, 22, 22)

    painter.setPen(QColor("#F8F8F2"))
    font = QFont("Consolas", 34, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A#")

    painter.setPen(QPen(QColor("#74FBD3"), 3))
    painter.drawLine(30, 96, 98, 96)
    painter.end()
    return QIcon(pixmap)
