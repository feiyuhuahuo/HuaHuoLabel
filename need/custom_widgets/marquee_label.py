#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from need.custom_signals import ListSignal

signal_show_plain_img = ListSignal()
signal_show_label_img = ListSignal()


class MarqueeLabel(QLabel):
    def __init__(self, img_path, stat=None, parent=None):  # parent=None 必须要实现
        super().__init__(parent)
        self.img_path = img_path
        self.deleted_img = False
        self.set_stat(stat)

    def mousePressEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            if not self.deleted_img:
                signal_show_plain_img.send([self.img_path, False])
        elif e.buttons() == Qt.RightButton:
            if not self.deleted_img:
                signal_show_label_img.send([self.img_path, True])

    def setPixmap(self, path, del_img=False):
        super().setPixmap(path)
        self.deleted_img = del_img

    def set_stat(self, stat):
        if stat == 'undo':
            self.setStyleSheet('')
        elif stat == 'doing':
            self.setStyleSheet('border-width: 3px; border-style: solid; border-color: rgb(0, 200, 0);')
        elif stat == 'done':
            self.setStyleSheet('border-width: 3px; border-style: solid; border-color: rgb(220, 160, 30);')
