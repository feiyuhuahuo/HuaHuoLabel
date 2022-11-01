#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QMessageBox, QWidget, QCheckBox, QVBoxLayout


class MessageBoxWithTips(QWidget):
    def __init__(self, type, title, message):
        super().__init__()
        if type == 'information':
            icon = QMessageBox.Information
        elif type == 'question':
            icon = QMessageBox.Question
        elif type == 'warning':
            icon = QMessageBox.Warning
        elif type == 'critical':
            icon = QMessageBox.Critical

        self.message_box = QMessageBox(self)
        self.message_box.setWindowTitle(title)
        self.message_box.setText(message)
        self.message_box.setIcon(icon)
        self.message_box.show()


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = MessageBoxWithTips('critical', 'asd', 'sadfghbfhshtthsdsththseesbegesaf')
    ui.show()
    app.exec()
