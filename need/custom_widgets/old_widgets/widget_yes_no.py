#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtCore import Qt, QPropertyAnimation, QSequentialAnimationGroup, QTimer, QPoint, QSize, QLine
from PySide6.QtWidgets import QLabel, QHBoxLayout, QPushButton, QWidget, QDialog
from PySide6.QtGui import QPixmap, QIcon


class ButtonYesNo(QDialog):  # 淡入淡出的窗口不能设parent
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(68, 30)
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.button_yes = QPushButton(QIcon('images/yes_blue.png'), '')
        self.button_no = QPushButton(QIcon('images/no_blue.png'), '')
        self.button_no.setIconSize(QSize(14, 14))

        self.button_yes.setFixedSize(28, 20)
        self.button_yes.setDefault(True)
        self.button_no.setFixedSize(28, 20)
        layout.addWidget(self.button_no)
        layout.addWidget(self.button_yes)

        self.button_no.clicked.connect(self.close)

    def show_at(self, xy: QPoint):
        self.move(xy)
        self.show()
