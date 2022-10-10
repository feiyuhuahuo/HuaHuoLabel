#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QListWidget, QWidget
from PySide6.QtGui import QFont
from need.utils import ClassStatDict


class ClassStat(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('类别统计')
        self.class_list = QListWidget(self)

        font = QFont()
        font.setPointSize(12)
        self.class_list.setFont(font)
        self.class_list.resize(200, 500)

        for i, (k, v) in enumerate(ClassStatDict.items()):
            self.class_list.insertItem(i, f'{k}: {v}')
