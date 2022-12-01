#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QLineEdit
from PySide6.QtCore import Qt
from need.utils import ClsClasses


class ClassButton(QPushButton):
    def __init__(self, parent=None):  # parent=None 必须要实现
        super().__init__(parent)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() == Qt.RightButton:
            ori_text = self.text()
            text, is_ok = QInputDialog().getText(self, '类别名称', '请输入类别名称，输入"-"删除当前类别', QLineEdit.Normal)
            if is_ok and text:
                if text in ClsClasses.classes():
                    QMessageBox.warning(self, '类别重复', f'类别"{text}"已存在。')
                else:
                    if ori_text == '-':
                        if text != '-':
                            self.setText(text)
                            ClsClasses.add(text)
                    else:
                        ClsClasses.delete(ori_text)
                        self.setText(text)
                        if text != '-':
                            ClsClasses.add(text)
