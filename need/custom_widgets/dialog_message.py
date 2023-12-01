#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt


class CustomMessageBox(QDialog):
    # 不同功能的实例不能取相同的title!!
    # 如果是临时窗口，则实例属性将不起作用，因此用类属性来实现，同时记录窗口的title，防止不同窗口共用一个属性
    class_dsa, close_by_ok = {}, {}

    def __init__(self, type, title, hide_dsa=False):
        super().__init__()
        self.ui = QUiLoader().load('ui_files/message.ui')  # 主界面
        hbox_layout = QVBoxLayout()
        hbox_layout.addWidget(self.ui)
        self.setLayout(hbox_layout)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)

        assert type in ('about', 'information', 'question', 'warning', 'critical')
        self.type = type
        self.title = title
        self.ui.pushButton_cancel.setVisible(False)
        if type == 'about':
            self.ui.label.setPixmap(QPixmap('images/icon.png'))
        elif type == 'information':
            self.ui.label.setPixmap(QPixmap('images/iqwc/info_4.png'))
        elif type == 'question':
            self.ui.pushButton_cancel.setVisible(True)
            self.ui.label.setPixmap(QPixmap('images/iqwc/question_4.png'))
        elif type == 'warning':
            self.ui.label.setPixmap(QPixmap('images/iqwc/warning_4.png'))
        elif type == 'critical':
            self.ui.label.setPixmap(QPixmap('images/iqwc/critical_4.png'))

        self.ui.pushButton.clicked.connect(self.close)
        self.ui.pushButton_cancel.clicked.connect(self.close)
        self.ui.checkBox.toggled.connect(self.set_dont_show_again)
        self.ui.textBrowser.append('  ')

        self.class_dsa.setdefault(title, False)
        self.close_by_ok.setdefault(title, False)

        if hide_dsa:
            self.ui.checkBox.setVisible(False)

    def closeEvent(self, event):
        if self.sender() is self.ui.pushButton:
            self.close_by_ok[self.title] = True
        else:
            self.close_by_ok[self.title] = False

    def add_text(self, text):
        self.ui.textBrowser.append(text)

    @property
    def question_result(self):
        assert self.type == 'question', 'Error, self.type != "question".'
        return self.close_by_ok[self.title]

    def set_dont_show_again(self):
        self.class_dsa[self.title] = self.ui.checkBox.isChecked()

    def show(self, text='', clear_old=True):
        if self.class_dsa[self.title]:
            return

        if clear_old:
            self.ui.textBrowser.clear()

        if text:
            self.ui.textBrowser.append(text)

        doc = self.ui.textBrowser.document()
        doc.setTextWidth(360)  # 英文需要设置两遍才有效，令人费解 (ˉ▽ˉ；)...
        doc.setTextWidth(360)

        self.ui.textBrowser.setMinimumHeight(doc.size().height())
        self.ui.textBrowser.setMinimumWidth(doc.size().width())
        self.resize(self.ui.textBrowser.size())
        self.exec()


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTranslator, QObject

    app = QApplication()

    trans_main_window = QTranslator()
    trans_main_window.load('../../ts_files/dialog_message.qm')
    app.installTranslator(trans_main_window)

    ui = CustomMessageBox('question', QObject.tr('关于花火标注'))
    ui.show(QObject.tr('你好野'))
    app.exec()
