#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import os
import pdb

from os import path as osp
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtCore import QPoint


class ShapeCombo(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load('ui_files/shape_combo.ui')
        self.setCentralWidget(self.ui)
        self.setWindowTitle(self.tr('组合形状'))

    def closeEvent(self, event):
        self.parent().shape_type_reset()

    def move_to(self, pos: QPoint):
        self.move(pos)

    def show_at(self, pos: QPoint):
        self.move(pos)
        self.show()


if __name__ == '__main__':
    app = QApplication()
    pp = ShapeCombo()
    pp.show()
    app.exec()
