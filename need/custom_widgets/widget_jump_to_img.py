#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QPushButton, QApplication, QWidget, QSpinBox


class JumpToImg(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spinBox = QSpinBox(self)
        self.spinBox.setObjectName('round_spin')
        self.spinBox.setMinimum(1)
        self.spinBox.setMaximum(9999)
        self.spinBox.setValue(0)
        self.spinBox.setFixedSize(54, 24)
        font = QFont()
        font.setPointSize(10)
        self.spinBox.setFont(font)

        self.spinBox.setStyleSheet("QSpinBox{border: 1px solid gray; border-radius: 4px;}"
                                   "QSpinBox::down-button {border: 1px solid grey;"
                                   "background-color: rgb(235, 235, 235);"
                                   "border-image:url(images/direction/down3.png)}"
                                   "QSpinBox::down-button:hover {background-color:rgb(225, 225, 225);}"
                                   "QSpinBox::down-button:pressed {background-color:rgb(215, 215, 215);}"
                                   "QSpinBox::up-button {border: 1px solid gray;"
                                   "background-color: rgb(235, 235, 235);"
                                   "border-image:url(images/direction/up3.png)}"
                                   "QSpinBox::up-button:hover {background-color:rgb(225, 225, 225);}"
                                   "QSpinBox::up-button:pressed {background-color:rgb(215, 215, 215);}")

        self.pushButton_jump = QPushButton(self)
        self.pushButton_jump.setFixedSize(32, 24)
        self.pushButton_jump.setIcon(QIcon('images/jump_to.png'))
        self.pushButton_jump.setToolTip(self.tr('跳转至'))
        self.pushButton_jump.setStyleSheet(
            """
            QPushButton {
            background-color: rgb(235, 235, 235);
            border: 1px solid gray;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            }

            QPushButton:hover {background-color:rgb(225, 225, 225);}
            QPushButton:pressed {background-color:rgb(215, 215, 215);}
            """
        )

        self.setFixedSize(84, 24)
        self.spinBox.move(0, 0)
        self.pushButton_jump.move(52, 0)


if __name__ == '__main__':
    app = QApplication()
    img_edit = JumpToImg()
    img_edit.show()
    app.exec()
