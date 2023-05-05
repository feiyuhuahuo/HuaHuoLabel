#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtCore import Qt, QPropertyAnimation, QSequentialAnimationGroup, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtGui import QPixmap


class ReadEditInfo(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowOpacity(0)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setPixmap(QPixmap('images/switch_to_read.png'))
        self.setScaledContents(True)
        self.resize(450, 105)

        start_opa = 0.7
        self.ani1 = QPropertyAnimation(self, b'windowOpacity')
        self.ani1.setDuration(1000)
        self.ani1.setStartValue(start_opa)
        self.ani1.setEndValue(start_opa)

        self.ani2 = QPropertyAnimation(self, b'windowOpacity')
        self.ani2.setDuration(1000)
        self.ani2.setStartValue(start_opa)
        self.ani2.setEndValue(0)

        self.ani_group = QSequentialAnimationGroup(self)
        self.ani_group.addAnimation(self.ani1)
        self.ani_group.addPause(500)
        # self.ani_group.addAnimation(self.ani2)
        # self.ani_group.finished.connect(self.close)

    def show(self):
        # 加个singleShot(), 不然不透明的窗口会先一闪而过，恶心心，或者动画的透明度从0开始也可以
        timer = QTimer()
        timer.singleShot(200, self.ani_group.start)
        super().show()
