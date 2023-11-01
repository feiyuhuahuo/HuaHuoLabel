#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import os
import pdb

from os import path as osp
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFileDialog, QMainWindow, QApplication, QDialog
from PySide6.QtWidgets import QMessageBox as QMB


class ShapeCombo(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load('ui_files/obj_op.ui')
        self.setCentralWidget(self.ui)
        self.setWindowTitle(self.tr('高级形状'))

    def closeEvent(self, event):
        self.parent().shape_type_reset()

    def show(self):
        x = self.parent().x()
        width = self.parent().width()
        y = self.parent().y()
        self.move(x + width - 370, y + 120)  # 不知为何不能按父控件坐标系调整坐标，只能直接根据HHL_MainWindow的坐标来设置偏移量
        super().show()


if __name__ == '__main__':
    app = QApplication()
    pp = ShapeCombo()
    pp.show()
    app.exec()
