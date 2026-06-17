from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ascii_foundry import __app_name__
from ascii_foundry.gui.icon import create_app_icon
from ascii_foundry.gui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setWindowIcon(create_app_icon())
    window = MainWindow()
    window.showMaximized()
    return app.exec()
