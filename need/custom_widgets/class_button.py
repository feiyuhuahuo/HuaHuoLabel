#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QLineEdit
from PySide6.QtCore import Qt
from need.utils import ClassStatDict


class ClassButton(QPushButton):
    def __init__(self, parent=None):  # parent=None 必须要实现
        super().__init__(parent)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if e.button() == Qt.RightButton:
            ori_text = self.text()
            text, is_ok = QInputDialog().getText(self, '类别名称', '请输入类别名称，输入"-"删除当前类别', QLineEdit.Normal)
            if is_ok and text:
                if text in ClassStatDict.keys():
                    QMessageBox.warning(self, '类别重复', f'类别\'{text}\'已存在。')
                else:
                    if ori_text == '-':
                        if text != '-':
                            self.setText(text)
                            ClassStatDict.setdefault(text, 0)
                    else:
                        self.setText(text)
                        if ori_text in ClassStatDict.keys():
                            ClassStatDict.pop(ori_text)
                        if text != '-':
                            ClassStatDict.setdefault(text, 0)

                with open(f'log_files/buttons.txt', 'w', encoding='utf-8') as f:
                    for one_c in ClassStatDict.keys():
                        f.writelines(f'{one_c}\n')
