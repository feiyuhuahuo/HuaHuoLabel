#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtCore import QPoint

from need.SharedWidgetStatFlags import stat_flags


class ShapeCombo(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load('ui_files/shape_combo.ui')
        self.setCentralWidget(self.ui)
        self.setWindowTitle(self.tr('组合形状'))
        self.resize(220, 400)

    def closeEvent(self, event):
        stat_flags.ShapeCombo_IsOpened = False
        self.parent().shape_type_reset()

    def move_to(self, pos: QPoint):
        self.move(pos)

    def show_at(self, pos: QPoint):
        self.move(pos)
        stat_flags.ShapeCombo_IsOpened = True
        self.show()


if __name__ == '__main__':
    app = QApplication()
    pp = ShapeCombo()
    pp.show()
    app.exec()
