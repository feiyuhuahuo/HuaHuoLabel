#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QListWidget, QWidget
from PySide6.QtGui import QFont, QIcon


class ClassStatWidget(QWidget):
    def __init__(self, add_info: list):
        """
        :param add_info: [string1, string2, ...]
        """
        super().__init__()
        self.setWindowTitle('类别统计')
        self.setWindowIcon(QIcon('images/icon.png'))
        self.class_list = QListWidget(self)

        font = QFont()
        font.setPointSize(12)
        self.class_list.setFont(font)
        self.class_list.resize(385, 700)

        if len(add_info):
            for one in add_info:
                self.class_list.addItem(one)
