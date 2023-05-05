#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QPixmap
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

    def set_pixmap(self, path, del_img=False):
        super().setPixmap(path)
        self.deleted_img = del_img

    def set_stat(self, stat):
        if stat == 'undo':
            self.setStyleSheet('')
        elif stat == 'doing':
            self.setStyleSheet('border-width: 4px; border-style: solid; border-color: rgb(0, 200, 0);')
        elif stat == 'done':
            self.setStyleSheet('border-width: 4px; border-style: solid; border-color: rgb(220, 140, 0);')


class Marquees(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.addStretch()
        self.setLayout(layout)
        self.mar_i = -1
        self.marquee_num = 30  # 越大，占用内存越多
        self.marquee_size = 150
        self.del_map = QPixmap('images/图片已删除.png').scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio)

    def add_marquee(self, img_path):
        m_label = MarqueeLabel(img_path=img_path, stat='doing', parent=self)
        m_label.set_pixmap(QPixmap(img_path).scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio))
        self.layout().insertWidget(self.layout().count() - 1, m_label)
        self.mar_i += 1

    def insert_marquee(self, img_path, first=False, last=True):
        m_label = MarqueeLabel(img_path=img_path, stat='doing', parent=self)
        m_label.setPixmap(QPixmap(img_path).scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio))

        if first:
            self.del_marquee(self.marquee_num - 1)
            self.layout().insertWidget(0, m_label)
        elif last:
            self.del_marquee(0)
            self.layout().insertWidget(self.layout().count() - 1, m_label)

    def clear(self):
        while self.layout().count() > 1:
            self.del_marquee(0)

    def del_marquee(self, i):
        # widget = self.marquees_layout.takeAt(0).widget()
        # widget.setParent(None)
        # self.marquees_layout.removeWidget(widget)
        widget = self.layout().itemAt(i).widget()
        self.layout().takeAt(i)
        widget.deleteLater()

    def set_deleted(self):
        self.layout().itemAt(self.mar_i).widget().setPixmap(self.del_map, del_img=True)

    def set_stat(self, stat):
        self.layout().itemAt(self.mar_i).widget().set_stat(stat)
