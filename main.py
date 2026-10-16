# -*- coding: utf-8 -*-
"""
Entry point for Al-Bonyan ERP (نظام البنيان للمحاسبة وتجارة الحديد والأسمنت)
Run: python main.py
"""
import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from database import DatabaseManager
from main_window import MainWindow


def global_exception_handler(exctype, value, tb):
    """Catch any unhandled exception and present a friendly Arabic dialog without crashing."""
    tb_str = "".join(traceback.format_exception(exctype, value, tb))
    print(f"Unhandled Error:\n{tb_str}", file=sys.stderr)
    app = QApplication.instance()
    if app:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("تنبيه النظام")
        msg.setText(f"حدث خطأ أثناء تنفيذ العملية:\n{value}")
        msg.setDetailedText(tb_str)
        msg.exec()


sys.excepthook = global_exception_handler


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    db = DatabaseManager()
    window = MainWindow(db)
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
