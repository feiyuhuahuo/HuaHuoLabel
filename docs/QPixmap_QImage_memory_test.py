#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


class ImageDisplay(QMainWindow):
    def __init__(self):
        super().__init__()

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # 创建一个QLabel
        lay = QVBoxLayout(self)
        self.button = QPushButton(self)
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.button)
        lay.addWidget(self.label)

        self.central_widget.setLayout(lay)

        self.button.clicked.connect(self.add)
        self.setWindowTitle('Image Display')

        self.aa =[]

    def add(self):
        self.aa.append(QImage('D:\Data\SIC_E\样片边缘测试/1、同光\Images_20231012173825-同光-1654-崩边\EdgeSurface_UP/1_0.jpg'))


if __name__ == '__main__':
    app = QApplication()
    window = ImageDisplay()
    window.show()
    app.exec()


# 对于创建一个QPixmap和QImage对象, 4000*5000的jpg图，需要~75M内存
# 对于4000*5000的jpg图, setPixmap仅感受到略微延迟
