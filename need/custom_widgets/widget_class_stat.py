#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import sys

from PySide6.QtWidgets import QWidget, QTextBrowser, QApplication, QMenu, QInputDialog, QMessageBox
from PySide6.QtGui import QFont, QIcon, QCursor
from PySide6.QtCore import Qt


class ClassStatWidget(QWidget):
    def __init__(self, parent=None, add_info: list = [], version_path=''):
        """
        :param add_info: [string1, string2, ...]
        """
        super().__init__(parent)
        self.setWindowTitle(self.tr('类别统计'))
        self.setWindowIcon(QIcon('images/icon.png'))
        self.add_info = add_info
        self.version_path = version_path
        self.input_dlg = QInputDialog(self)

        self.stat_text = QTextBrowser(self)
        self.stat_text.setContextMenuPolicy(Qt.CustomContextMenu)
        font = QFont('新宋体')  # 这个字体，中文固定占两个宽度，英文固定占一个宽度
        font.setPointSize(12)
        self.stat_text.setFont(font)

        if sys.platform == 'win32':
            self.stat_text.resize(450, 700)
        else:
            self.stat_text.resize(400, 700)

        self.setFixedSize(self.stat_text.size())

        if len(add_info):
            for one in add_info:
                self.stat_text.append(one)

        self.menu = QMenu(self.stat_text)
        self.menu.addAction(self.tr('导出统计信息')).triggered.connect(self.export_txt)
        self.stat_text.customContextMenuRequested.connect(self.show_menu)

    def export_txt(self):
        name, ok = self.input_dlg.getText(self, self.tr('保存名称'), self.tr('请输入保存名称'))
        if ok:
            export_path = f'{self.version_path}/{name}.txt'
            with open(export_path, 'w', encoding='utf-8') as f:
                for one in self.add_info:
                    f.write(f'{one}\n')

            QMessageBox.information(self, self.tr('已导出'), self.tr('已导出至"{}"').format(export_path))

    def show_menu(self):
        self.menu.exec(QCursor.pos())


if __name__ == '__main__':
    app = QApplication()
    info = []
    info.append(f'一yrftg6yy\t3\t30')
    info.append(f'一sd三sge\t3\t30')
    info.append(f'ssds\t3\t30')
    info.append(f'一二sdst\t3\t30')
    info.append(f'bg苹果\t3\t30')

    ui = ClassStatWidget(add_info=info)
    ui.show()
    app.exec()
