#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QLabel, QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont


class WaitingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(120, 40)
        self.num = 0
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)
        self.setText(' 等待中')

        self.timer = QTimer()
        self.timer.timeout.connect(self.set_text)
        self.timer.start(1000)

        self.setStyleSheet("background-color: rgb(240, 240, 240); border-color: rgb(80, 80, 80); "
                           "border-width: 2px; border-style: solid;")

    def set_text(self):
        text = ' 等待中.' + '.' * self.num
        self.setText(text)
        self.num += 1
        self.num = self.num % 6

    def stop(self):
        self.timer.stop()


if __name__ == '__main__':
    app = QApplication()
    wl = WaitingLabel()
    wl.show()
    app.exec()
