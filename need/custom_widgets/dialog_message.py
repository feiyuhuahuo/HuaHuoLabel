#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt
from need.custom_signals import BoolSignal

signal_question_result = BoolSignal()


class CustomMessageBox(QDialog):
    def __init__(self, type, title, hide_dsa=False):
        super().__init__()
        self.ui = QUiLoader().load('ui_files/message.ui')  # 主界面
        hbox_layout = QVBoxLayout()
        hbox_layout.addWidget(self.ui)
        self.setLayout(hbox_layout)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)
        self.__question_result = None

        assert type in ('about', 'information', 'question', 'warning', 'critical')
        self.ui.pushButton_cancel.setVisible(False)
        if type == 'about':
            self.ui.label.setPixmap(QPixmap('images/icon.png'))
        elif type == 'information':
            self.ui.label.setPixmap(QPixmap('images/info_4.png'))
        elif type == 'question':
            self.ui.pushButton_cancel.setVisible(True)
            self.ui.label.setPixmap(QPixmap('images/question_4.png'))
        elif type == 'warning':
            self.ui.label.setPixmap(QPixmap('images/warning_4.png'))
        elif type == 'critical':
            self.ui.label.setPixmap(QPixmap('images/critical_4.png'))

        self.ui.pushButton.clicked.connect(lambda: self.close(True))
        self.ui.pushButton_cancel.clicked.connect(lambda: self.close(False))
        self.ui.checkBox.toggled.connect(self.set_dont_show_again)
        self.ui.textBrowser.append('  ')
        self.DontShowAgain = False

        if not self.has_ch(title):
            self.ui.pushButton.setText('Yes')
            self.ui.checkBox.setText("Don't show again")

        if hide_dsa:
            self.ui.checkBox.setVisible(False)

    def add_text(self, text):
        self.ui.textBrowser.append(text)

    def close(self, result):
        self.__question_result = result
        super().close()

    @staticmethod
    def has_ch(text):
        for one in text:
            if u'\u4e00' <= one <= u'\u9fff':
                return True
        return False

    def result(self):
        return self.__question_result

    def set_dont_show_again(self):
        self.DontShowAgain = self.ui.checkBox.isChecked()

    def show(self, text='', clear_old=True):
        if clear_old:
            self.ui.textBrowser.clear()

        if text:
            self.ui.textBrowser.append(text)

        if not self.DontShowAgain:
            doc = self.ui.textBrowser.document()
            doc.setTextWidth(360)  # 英文需要设置两遍才有效，令人费解 (ˉ▽ˉ；)...
            doc.setTextWidth(360)

            self.ui.textBrowser.setMinimumHeight(doc.size().height())
            self.ui.textBrowser.setMinimumWidth(doc.size().width())
            self.resize(self.ui.textBrowser.size())
            self.exec()


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = CustomMessageBox('question', '关于花火标注')
    ui.show('Version 1.0.0.\n'
            '\n'
            'HuaHuoLabel is a multifunctional label tool developed with PySide6. It can help label data for '
            'five computer vision tasks including single category classification, multiple category '
            'classification, semantic segmentation, object detection and instance segmentation. HuaHuoLabel '
            'also supports auto-labeling, dataset management and pseudo label generation. With the help of '
            'HuaHuoLabel, you can train your AI model more conveniently and efficiently.\n'
            '\n'
            'HuaHuoLabel uses GNU GPL license. You can use this tool at will. However, do not use it for '
            'commercial activities without the permission of the author.\n')
    app.exec()
