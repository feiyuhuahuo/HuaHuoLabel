#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QLabel, QApplication, QSizePolicy
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont


class WaitingLabel(QLabel):
    def __init__(self, parent=None, text=None):
        super().__init__(parent)
        self.num = 0
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)
        if text:
            self.text = f' {text} '

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

    def show_at(self, geometry):
        text_width = self.fontMetrics().boundingRect(self.text).width()
        self.setMinimumWidth(text_width + 40)
        x1 = int(geometry.width() / 2)
        y1 = int(geometry.height() / 3)
        self.move(x1, y1)
        self.show()

    # def pp(self):
    #     print(self.fontMetrics().boundingRect('保存土拍中...').width())


if __name__ == '__main__':
    app = QApplication()
    wl = WaitingLabel(text='保存土拍中')
    wl.show()
    wl.pp()
    app.exec()
