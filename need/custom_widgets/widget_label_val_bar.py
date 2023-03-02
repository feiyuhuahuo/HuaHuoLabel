#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QLabel


class LabelValBar(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_tv(self, train_num, val_num):
        total_num = train_num + val_num
        train_ratio = train_num / total_num
        width = abs(0.5 - train_ratio) * 2

        self.setText(f'val: {val_num}, {(1 - train_ratio) * 100:.1f}% ')
        val_base_ss = "border-top-right-radius: 4px;border-bottom-right-radius: 4px;"

        if train_ratio > 0.5:
            self.setStyleSheet(val_base_ss +
                               f"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, "
                               f"stop:{width} rgb(243, 81, 122), stop:{width + 0.0001} rgb(85, 170, 255))")
        else:
            self.setStyleSheet(val_base_ss + "background-color: rgb(85, 170, 255)")
