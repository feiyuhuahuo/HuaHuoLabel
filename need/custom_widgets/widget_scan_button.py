#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QApplication, QWidget


class ScanButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(65, 25)
        self.pushButton_last = QPushButton(self)
        self.pushButton_last.setFixedSize(32, 24)
        self.pushButton_last.setIcon(QIcon('images/direction/icon_50 - 副本.png'))
        self.pushButton_last.setToolTip(self.tr('浏览上一张图片，快捷键"A"'))
        self.pushButton_last.setStyleSheet(
            """
            QPushButton {
            background-color: rgb(235, 235, 235);
            border: 1px solid gray;
            border-top-left-radius: 4px;
            border-bottom-left-radius: 4px;}

            QPushButton:hover {background-color:rgb(225, 225, 225);}

            QPushButton:pressed {background-color:rgb(215, 215, 215);}
            """
        )
        self.pushButton_next = QPushButton(self)
        self.pushButton_next.setFixedSize(32, 24)
        self.pushButton_next.setIcon(QIcon('images/direction/icon_50.png'))
        self.pushButton_next.setToolTip(self.tr('浏览下一张图片，快捷键"D"'))
        self.pushButton_next.setStyleSheet(
            """
            QPushButton {
            background-color: rgb(235, 235, 235);
            border: 1px solid gray;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;}

            QPushButton:hover {background-color:rgb(225, 225, 225);}

            QPushButton:pressed {background-color:rgb(215, 215, 215);}
            """
        )

        self.pushButton_last.move(0, 0)
        self.pushButton_next.move(31, 0)


if __name__ == '__main__':
    app = QApplication()
    img_edit = ScanButton()
    img_edit.show()
    app.exec()
