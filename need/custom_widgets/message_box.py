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

        # self.message_box = QMessageBox(self, icon, title=title, text=message)

        self.message_box = QMessageBox(QMessageBox.Information, title='SS', text='ASDSD')


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = MessageBoxWithTips('warning', 'asd', 'sadaf')
    ui.show()
    app.exec()
