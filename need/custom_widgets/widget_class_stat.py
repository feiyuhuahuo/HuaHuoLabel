#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import sys

from PySide6.QtWidgets import QWidget, QTextBrowser, QApplication
from PySide6.QtGui import QFont, QIcon


class ClassStatWidget(QWidget):
    def __init__(self, add_info: list):
        """
        :param add_info: [string1, string2, ...]
        """
        super().__init__()
        self.setWindowTitle('类别统计')
        self.setWindowIcon(QIcon('../../images/icon.png'))
        self.stat_text = QTextBrowser(self)

        font = QFont()
        font.setPointSize(12)
        self.stat_text.setFont(font)

        if sys.platform == 'win32':
            self.stat_text.resize(500, 700)
        else:
            self.stat_text.resize(440, 700)

        if len(add_info):
            for one in add_info:
                self.stat_text.append(one)

        self.setFixedSize(self.stat_text.size())


if __name__ == '__main__':
    app = QApplication()
    info = []
    info.append(f'一二\t3\t30')
    info.append(f'一二三四\t3\t30')
    info.append(f'一二三三三\t3\t30')
    info.append(f'一二三三三三\t3\t30')

    info.append(f'aaaa\t3\t30')
    info.append(f'aaaaaa\t3\t30')
    info.append(f'aaaaaammm\t3\t30')
    info.append(f'aaaaaalll\t3\t30')

    ui = ClassStatWidget(info)
    ui.show()
    app.exec()
