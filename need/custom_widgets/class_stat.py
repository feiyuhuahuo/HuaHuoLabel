#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QListWidget, QWidget
from PySide6.QtGui import QFont
from need.utils import ClassStatDict


class ClassStat(QWidget):
    def __init__(self, add_info=[]):
        """
        :param add_info: [string1, string2, ...]
        """
        super().__init__()
        self.setWindowTitle('类别统计')
        self.class_list = QListWidget(self)

        font = QFont()
        font.setPointSize(12)
        self.class_list.setFont(font)
        self.class_list.resize(200, 500)

        for k, v in ClassStatDict.items():
            self.class_list.addItem(f'{k}: {v}')

        if len(add_info):
            for one in add_info:
                self.class_list.addItem(one)

