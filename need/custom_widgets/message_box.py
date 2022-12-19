#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt


class CustomMessageBox(QMainWindow):
    def __init__(self, title):
        super().__init__()
        self.ui = QUiLoader().load('ui_files/message.ui')  # 主界面
        self.setCentralWidget(self.ui)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setWindowTitle(title)
        self.ui.pushButton.clicked.connect(self.close)
        self.ui.checkBox.toggled.connect(self.set_dont_show_again)
        self.ui.textBrowser.append('  ')
        self.DontShowAgain = False

    def add_text(self, text):
        self.ui.textBrowser.append(text)

    def set_dont_show_again(self):
        self.DontShowAgain = self.ui.checkBox.isChecked()

    def show(self, type, text):
        self.ui.textBrowser.clear()

        if type == 'information':
            self.ui.label.setPixmap(QPixmap('images/info_4.png'))
        elif type == 'question':
            self.ui.label.setPixmap(QPixmap('images/question_4.png'))
        elif type == 'warning':
            self.ui.label.setPixmap(QPixmap('images/warning_4.png'))
        elif type == 'critical':
            self.ui.label.setPixmap(QPixmap('images/critical_4.png'))
        else:
            print('Incorrect information type!')
            return

        self.ui.textBrowser.append(text)

        if not self.DontShowAgain:
            super().show()
            # 设置窗口随文本多少的变化而变化, 得在调用show()之后设置
            doc = self.ui.textBrowser.document()
            doc.setTextWidth(320)
            self.ui.textBrowser.setMinimumHeight(doc.size().height())
            self.ui.textBrowser.setMinimumWidth(doc.size().width())
            self.resize(self.ui.textBrowser.size())


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = CustomMessageBox('warning')
    ui.show('information', 'sdahhhjjjjjjfjff')
    app.exec()
