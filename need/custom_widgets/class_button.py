#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QLineEdit
from PySide6.QtCore import Qt
from need.utils import ClsClasses


class ClassButton(QPushButton):
    def __init__(self, parent=None, language='CN'):  # parent=None 必须要实现
        super().__init__(parent)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)
        self.language = language

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() == Qt.RightButton:
            ori_text = self.text()

            if self.language == 'CN':
                text, is_ok = QInputDialog().getText(self, '类别名称', '请输入类别名称，输入"-"删除当前类别。', QLineEdit.Normal)
            elif self.language == 'EN':
                text, is_ok = QInputDialog().getText(self, 'Class Name',
                                                     'Please input class name, input "-" to delete.', QLineEdit.Normal)

            if is_ok and text:
                if text in ClsClasses.classes():
                    if self.language == 'CN':
                        QMessageBox.warning(self, '类别重复', f'类别"{text}"已存在。')
                    elif self.language == 'EN':
                        QMessageBox.warning(self, 'Duplicate Class', f'Class "{text}" already exists.')
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
