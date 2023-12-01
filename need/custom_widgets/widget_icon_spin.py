#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QApplication, QWidget, QSpinBox, QLabel


class IconSpin(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_label = QLabel(self)
        self.icon_label.resize(24, 24)
        self.icon_label.setScaledContents(True)
        self.icon_label.setStyleSheet('QLabel{border: 1px solid gray;'
                                      'border-top-left-radius: 4px;'
                                      'border-bottom-left-radius: 4px;'
                                      'border-right:none;}')

        self.spinBox = QSpinBox(self)
        self.spinBox.setFixedSize(40, 24)
        font = QFont()
        font.setPointSize(10)
        self.spinBox.setFont(font)
        self.spinBox.setStyleSheet("QSpinBox{border: 1px solid gray;}"
                                   "QSpinBox::down-button {border: 1px solid grey;"
                                   "background-color: rgb(235, 235, 235);"
                                   " border-image:url(images/direction/down3.png)}"
                                   "QSpinBox::down-button:hover {background-color:rgb(225, 225, 225);}"
                                   "QSpinBox::down-button:pressed {background-color:rgb(215, 215, 215);}"
                                   "QSpinBox::up-button {border: 1px solid gray;"
                                   "background-color: rgb(235, 235, 235);"
                                   " border-image:url(images/direction/up3.png)}"
                                   "QSpinBox::up-button:hover {background-color:rgb(225, 225, 225);}"
                                   "QSpinBox::up-button:pressed {background-color:rgb(215, 215, 215);}")
        self.setFixedSize(64, 24)
        self.spinBox.move(24, 0)

    def value(self):
        return self.spinBox.value()

    def set_default(self, icon_img: str, minimum: int, maximum: int, value: int, step: int = 1, padding_icon: int = 4):
        self.icon_label.setPixmap(QPixmap(icon_img))
        self.spinBox.setMinimum(minimum)
        self.spinBox.setMaximum(maximum)
        self.spinBox.setValue(value)
        self.spinBox.setSingleStep(step)
        base_ss = self.icon_label.styleSheet()
        self.icon_label.setStyleSheet(base_ss + 'QLabel{padding:' + f'{padding_icon}px;' + '}')


if __name__ == '__main__':
    app = QApplication()
    img_edit = IconSpin()
    img_edit.show()
    app.exec()
