#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import os
import pdb

from PySide6.QtWidgets import QHBoxLayout, QLabel, QComboBox, QDialog, QFileDialog, QPushButton, QVBoxLayout, \
    QSpacerItem, QSizePolicy, QApplication, QLineEdit
from PySide6.QtGui import QFont


class ChooseVersion(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 115)
        font = QFont()
        font.setPointSize(10)

        title = self.tr('选择版本')
        self.setWindowTitle(title)
        self.file_select_dlg = QFileDialog()
        self.__version = ''

        self.label = QLabel(title)
        self.label.setFont(font)
        self.comboBox_versions = QComboBox()
        self.comboBox_versions.setFont(font)
        self.comboBox_versions.setMinimumWidth(70)
        self.comboBox_versions.setMaximumWidth(70)

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

        self.new_button = QLabel(self.tr('新建版本'))
        self.new_button.setFont(font)
        self.version_edit = QLineEdit()
        self.version_edit.setFont(font)
        self.version_edit.setMinimumWidth(70)
        self.version_edit.setMaximumWidth(70)

        self.comboBox_versions.currentIndexChanged.connect(lambda: self.version_edit.clear())

        layout1 = QHBoxLayout()
        layout1.addWidget(self.label)
        layout1.addWidget(self.comboBox_versions)

        layout2 = QHBoxLayout()
        layout2.addItem(h_spacer)
        layout2.addWidget(self.ok_putton)
        layout2.addWidget(self.cancel_putton)

        layout4 = QHBoxLayout()
        layout4.addWidget(self.new_button)
        layout4.addWidget(self.version_edit)

        layout3 = QVBoxLayout()
        layout3.addLayout(layout1)
        layout3.addLayout(layout4)
        layout3.addLayout(layout2)
        self.setLayout(layout3)

    def exec(self):
        super().exec()
        return self.__version

    def get_versions(self, label_path):
        self.comboBox_versions.clear()
        self.__version = ''

        if os.path.exists(label_path):
            versions = [one for one in os.listdir(label_path)]
            versions = [one for one in versions if os.path.isdir(f'{label_path}/{one}')]

            for one in versions:
                self.comboBox_versions.addItem(one)

    def set_result(self, result):
        if result:
            new_version = self.version_edit.text()
            if new_version:
                self.__version = new_version
            else:
                self.__version = self.comboBox_versions.currentText()
        else:
            self.__version = ''

        self.close()


if __name__ == '__main__':
    app = QApplication()
    wl = ChooseVersion()
    wl.show()
    app.exec()
