#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox, QCheckBox, QVBoxLayout, QMainWindow
from PySide6.QtGui import QIcon, QPixmap


class CustomMessageBox(QMainWindow):
    def __init__(self, type, title, message):
        super().__init__()
        self.ui = QUiLoader().load('../../ui_files/message.ui')  # 主界面
        self.setCentralWidget(self.ui)
        self.setWindowIcon(QIcon('../../images/info.png'))
        self.setWindowTitle(title)
        self.ui.textBrowser.append(message)

        if type == 'information':
            self.ui.label.setPixmap(QPixmap('../../images/info.png'))
        elif type == 'question':
            self.ui.label.setPixmap(QPixmap('../../images/question.png'))
        elif type == 'warning':
            self.ui.label.setPixmap(QPixmap('../../images/warning.png'))


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = CustomMessageBox('information', 'asd', 'sadfghbfhshtths')

    ui.show()
    app.exec()
