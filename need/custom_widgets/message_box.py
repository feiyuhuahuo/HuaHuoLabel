#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt


class CustomMessageBox(QMainWindow):
    def __init__(self, type, title):
        super().__init__()
        self.ui = QUiLoader().load('ui_files/message.ui')  # 主界面
        self.setCentralWidget(self.ui)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setWindowTitle(title)
        self.type = type
        self.ui.pushButton.clicked.connect(self.close)
        self.ui.checkBox.toggled.connect(self.set_dont_show_again)
        self.ui.textBrowser.append('  ')
        self.DontShowAgain = False

    def add_text(self, text):
        self.ui.textBrowser.append(text)

    def hide_dont_show_again(self):
        self.ui.checkBox.setVisible(False)

    def set_dont_show_again(self):
        self.DontShowAgain = self.ui.checkBox.isChecked()

    def show(self, text='', clear_old=True):
        if clear_old:
            self.ui.textBrowser.clear()

        if self.type == 'about':
            self.ui.label.setPixmap(QPixmap('images/icon.png'))
        elif self.type == 'information':
            self.ui.label.setPixmap(QPixmap('images/info_4.png'))
        elif self.type == 'question':
            self.ui.label.setPixmap(QPixmap('images/question_4.png'))
        elif self.type == 'warning':
            self.ui.label.setPixmap(QPixmap('images/warning_4.png'))
        elif self.type == 'critical':
            self.ui.label.setPixmap(QPixmap('images/critical_4.png'))
        else:
            print('Incorrect information type!')
            return

        if text:
            self.ui.textBrowser.append(text)

        if not self.DontShowAgain:
            super().show()
            # 设置窗口随文本多少的变化而变化, 得在调用show()之后设置
            doc = self.ui.textBrowser.document()
            doc.setTextWidth(360)
            self.ui.textBrowser.setMinimumHeight(doc.size().height())
            self.ui.textBrowser.setMinimumWidth(doc.size().width())
            self.resize(self.ui.textBrowser.size())


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = CustomMessageBox('about', '关于花火标注')
    ui.add_text('花火标注是一款多功能的标注工具，具有单类别分类，多类别分类，目标检测，语义分割，slfg等多种更，采用GNU License\n'
                '具有多发发我算法的撒旦撒反对十大单曲我觉得是积分圣诞节哈和我覅收电费水费年开始\n'
                '二是发挥示范色分红二手房建瓯市佛安抚水电费crew如厕微软范围广而非和我发表是的反思反思v三年覅就是南非无法收费是否能四分'
                '十分十分难受散发弄的设计费\n'
                '\n'
                'sfdkj ad欸u和覅发货金额是否就额外ripe王夫人上的飞机欧杰佛')
    ui.show()
    # ui.hide_dont_show_again()
    app.exec()
