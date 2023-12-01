#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QLabel


class LabelTrainVal(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_train(self):
        self.setText('train')
        self.setStyleSheet('border-radius: 6px;'
                           'background-color: rgb(243, 81, 122);')

    def set_val(self):
        self.setText('val')
        self.setStyleSheet('border-radius: 6px;'
                           'background-color: rgb(85, 170, 255);')

    def set_none(self):
        self.setText('none')
        self.setStyleSheet('border-radius: 6px;'
                           'background-color: rgb(200, 200, 200);')
