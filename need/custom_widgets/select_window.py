#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from need.custom_signals import BoolSignal
from need.utils import has_ch

signal_select_window_close = BoolSignal()


class SelectWindow(QMainWindow):
    def __init__(self, title='窗口', button_signal=None):
        super().__init__()
        loader = QUiLoader()
        self.ui = loader.load('ui_files/label_window.ui')
        self.setCentralWidget(self.ui)
        self.resize(150, 320)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setWindowModality(Qt.ApplicationModal)
        self.button_signal = button_signal
        if has_ch(title):
            placeholder_text = f'请输入{title}名称'
        else:
            placeholder_text = f'Please input {title} name.'
        self.ui.lineEdit.setPlaceholderText(placeholder_text)
        self.ui.listWidget.itemClicked.connect(self.select_seg_label)
        self.ui.pushButton.clicked.connect(self.emit_text)

    def closeEvent(self, event):
        signal_select_window_close.send(True)
        self.close()

    def select_seg_label(self):
        self.ui.lineEdit.setText(self.ui.listWidget.currentItem().text())

    def emit_text(self):
        text = self.ui.lineEdit.text().strip()
        if self.button_signal is not None:
            self.button_signal.send(text)

# if __name__ == '__main__':
#     from PySide6.QtWidgets import QApplication
#     app = QApplication()
#     ui = SelectWindow(title='你好')
#     ui.show()
#     app.exec()
