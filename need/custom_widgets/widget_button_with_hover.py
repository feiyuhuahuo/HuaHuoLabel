#!/usr/bin/env python
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QApplication


class ButtonWithHoverWindow(QPushButton):
    def __init__(self, parent=None):  # parent=None 必须要实现
        super().__init__(parent)


    def enterEvent(self, event):
        print('in')

    def leaveEvent(self, event):
        print('out')


if __name__ == '__main__':
    app = QApplication()
    ui = ButtonWithHoverWindow()
    ui.show()
    app.exec()
