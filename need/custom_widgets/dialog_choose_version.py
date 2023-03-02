#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import os

from PySide6.QtWidgets import QHBoxLayout, QLabel, QComboBox, QDialog, QFileDialog, QPushButton, QVBoxLayout, \
    QSpacerItem, QSizePolicy, QApplication
from PySide6.QtWidgets import QMessageBox as QMB
from PySide6.QtGui import QFont


class ChooseVersion(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(160, 60)
        font = QFont()
        font.setPointSize(10)

        title = self.tr('选择版本')
        self.setWindowTitle(title)
        self.file_select_dlg = QFileDialog()
        self.__version = ''

        self.label = QLabel(title)
        self.label.setFont(font)
        self.comboBox_versions = QComboBox()

        self.ok_putton = QPushButton(self.tr('确定'))
        self.ok_putton.setFont(font)
        self.ok_putton.setMaximumWidth(50)
        self.ok_putton.setDefault(True)
        self.ok_putton.clicked.connect(lambda: self.set_result(True))
        self.cancel_putton = QPushButton(self.tr('取消'))
        self.cancel_putton.setFont(font)
        self.cancel_putton.setMaximumWidth(50)
        self.cancel_putton.clicked.connect(lambda: self.set_result(False))
        h_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout1 = QHBoxLayout()
        layout1.addWidget(self.label)
        layout1.addWidget(self.comboBox_versions)

        layout2 = QHBoxLayout()
        layout2.addItem(h_spacer)
        layout2.addWidget(self.ok_putton)
        layout2.addWidget(self.cancel_putton)

        layout3 = QVBoxLayout()
        layout3.addLayout(layout1)
        layout3.addLayout(layout2)
        self.setLayout(layout3)

    def exec(self):
        if self.comboBox_versions.count():
            super().exec()
        else:
            QMB.warning(self, self.tr('未找到标注'), self.tr('未找到任何标注版本，请新建任务。'))

        return self.__version

    def set_path(self, label_path):
        versions = [one for one in os.listdir(label_path) if one.startswith('v')]
        versions = [one for one in versions if os.path.isdir(f'{label_path}/{one}')]
        self.comboBox_versions.clear()
        for one in versions:
            self.comboBox_versions.addItem(one)

    def set_result(self, result):
        if result:
            self.__version = self.comboBox_versions.currentText()
        else:
            self.__version = ''

        self.close()


if __name__ == '__main__':
    app = QApplication()
    wl = ChooseVersion()
    wl.show()
    app.exec()
