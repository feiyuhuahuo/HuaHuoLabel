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
            # 如果这里getText()和warning()的parent为self，则会继承这个类的styleSheet
            text, is_ok = QInputDialog().getText(None, self.tr('类别名称'), self.tr('请输入类别名称，输入"-"删除当前类别。'),
                                                 QLineEdit.Normal)

            if is_ok and text:
                if text in ClsClasses.classes():
                    QMessageBox.warning(None, self.tr('类别重复'), self.tr('类别"{}"已存在。').format(text))

                else:
                    if ori_text == '-':
                        if text != '-':
                            self.setText(text)
                    else:
                        ClsClasses.delete(ori_text)
                        self.setText(text)

    def setText(self, text: str):
        super().setText(text)
        if text != '-':
            ClsClasses.add(text)
