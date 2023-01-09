#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QLabel, QApplication, QSizePolicy
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont


class WaitingLabel(QLabel):
    def __init__(self, parent=None, text=None, language='CN'):
        super().__init__(parent)
        self.num = 0
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)
        if text:
            self.text = f' {text} '
        else:
            if language == 'CN':
                self.text = ' 等待中 '
            elif language == 'EN':
                self.text = ' Waiting '

        self.setText(self.text + '...')
        self.setStyleSheet("background-color: rgb(220, 220, 220); border-color: rgb(80, 80, 80); "
                           "border-width: 2px; border-style: solid;")

        self.setMinimumHeight(40)
        policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setSizePolicy(policy)

        self.timer = QTimer()
        self.timer.timeout.connect(self.set_text)
        self.timer.start(1000)

    def set_text(self):
        self.setText(self.text + '.' * (self.num + 1))
        self.num += 1
        self.num = self.num % 3

    def stop(self):
        self.timer.stop()


if __name__ == '__main__':
    app = QApplication()
    wl = WaitingLabel('保中')
    wl.show()
    app.exec()
