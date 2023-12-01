#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtCore import Qt, QPropertyAnimation, QSequentialAnimationGroup, QTimer, QPoint
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap


class ReadEditInfo(QLabel):  # 淡入淡出的窗口不能设parent
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowOpacity(0)
        self.setWindowFlag(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setPixmap(QPixmap('images/switch_to_read.png'))
        self.setScaledContents(True)
        self.resize(350, 81)

        start_opa = 0.7
        self.ani1 = QPropertyAnimation(self, b'windowOpacity')
        self.ani1.setDuration(300)
        self.ani1.setStartValue(start_opa)
        self.ani1.setEndValue(start_opa)

        self.ani2 = QPropertyAnimation(self, b'windowOpacity')
        self.ani2.setDuration(500)
        self.ani2.setStartValue(start_opa)
        self.ani2.setEndValue(0)

        self.ani_group = QSequentialAnimationGroup(self)
        self.ani_group.addAnimation(self.ani1)
        self.ani_group.addPause(300)
        self.ani_group.addAnimation(self.ani2)
        self.ani_group.finished.connect(self.close)

    def set_pixmap_pos(self, img_path: str, pos: QPoint):
        self.setPixmap(QPixmap(img_path))
        self.move(pos)

    def show(self):
        # 加个singleShot(), 不然不透明的窗口会先一闪而过，恶心心，或者动画的透明度从0开始也可以
        timer = QTimer()
        timer.singleShot(200, self.ani_group.start)
        super().show()

