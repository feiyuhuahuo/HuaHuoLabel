#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QLabel


class LabelTrainBar(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_tv(self, train_num, val_num):
        total_num = train_num + val_num
        train_ratio = train_num / total_num
        width = abs(0.5 - train_ratio) * 2
        self.setText(f' train: {train_num}, {train_ratio * 100:.1f}%')
        train_base_ss = "border-top-left-radius: 4px;border-bottom-left-radius: 4px;"

        if train_ratio > 0.5:
            self.setStyleSheet(train_base_ss + "background-color: rgb(243, 81, 122)")
        else:
            self.setStyleSheet(train_base_ss +
                               f"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, "
                               f"stop:{1 - width} rgb(243, 81, 122), stop:{1.0001 - width} rgb(85, 170, 255))")
