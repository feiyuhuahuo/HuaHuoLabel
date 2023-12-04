#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QLabel, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QSize
from need.custom_signals import ListSignal
from need.functions import img_path2_qpixmap

signal_show_plain_img = ListSignal()
signal_show_label_img = ListSignal()


class ImgLabel(QLabel):
    def __init__(self, img_path, stat='doing', parent=None):
        super().__init__(parent)
        self.img_path = img_path
        self.fixed_size = 150
        self.setMargin(2)  # 往内缩进2
        self.setAlignment(Qt.AlignCenter)
        self.IsDeleted = False
        self.set_stat(stat)

        # todo: 优化，pixmap是原尺寸的QPixmap，图很大的话会很占内存,需要在img_path2_qpixmap里实现KeepAspectRatio的resize
        if (pixmap := img_path2_qpixmap(img_path)) is not None:
            self.setPixmap(pixmap.scaled(self.fixed_size, self.fixed_size, Qt.KeepAspectRatio,
                                         mode=Qt.SmoothTransformation))

    def mousePressEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            if not self.IsDeleted:
                signal_show_plain_img.send([self.img_path, False])
        elif e.buttons() == Qt.RightButton:
            if not self.IsDeleted:
                signal_show_label_img.send([self.img_path, True])

    def set_as_deleted(self):
        self.setPixmap(QPixmap('images/图片已删除.png').scaled(self.fixed_size, self.fixed_size, Qt.KeepAspectRatio,
                                                               mode=Qt.SmoothTransformation))
        self.IsDeleted = True

    def set_stat(self, stat):
        if stat == 'undo':
            self.setStyleSheet('')
        elif stat == 'doing':
            self.setStyleSheet('border-width: 4px; border-style: solid; border-color: rgb(0, 200, 0);')
        elif stat == 'done':
            self.setStyleSheet('border-width: 4px; border-style: solid; border-color: rgb(220, 140, 0);')


class ImgsFlow(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.button_full = QPushButton(self)
        self.button_full.setIconSize(QSize(14, 14))
        self.button_full.setIcon(QIcon('images/full_screen_black.png'))
        self.button_full.setStyleSheet('QPushButton {background-color: rgb(235, 235, 235, 0.7); '
                                       'border: 1px solid gray; border-radius: 4px;}'
                                       'QPushButton:hover {background-color:  rgb(225, 225, 225);}'
                                       'QPushButton:pressed {background-color:  rgb(215, 215, 215);}')
        self.button_full.resize(22, 22)
        self.button_full.setToolTip(self.tr('页面视图'))

        self.img_i = -1
        self.max_num = 20  # 越大，占用内存越多

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.button_full.move(self.width() - 26, 3)

    def add_img(self, img_path):
        item, img_label = self.new_img_item(img_path)
        self.addItem(item)
        self.setItemWidget(item, img_label)
        self.scrollToItem(item)
        self.img_i += 1

    def clear(self):
        while self.count() > 0:
            self.takeItem(0)

        self.img_i = -1

    def img_flowing(self, img_path, left=False, right=False):
        if left:
            if self.img_i > 0:
                self.img_i -= 1
                self.set_cur_stat('doing')
            else:
                self.takeItem(self.max_num - 1)
                item, img_label = self.new_img_item(img_path)
                self.insertItem(0, item)
                self.setItemWidget(item, img_label)
        elif right:
            if self.img_i < self.count() - 1:
                self.img_i += 1
                self.set_cur_stat('doing')
            else:
                if self.count() >= self.max_num:
                    self.takeItem(0)

                self.add_img(img_path)

        self.img_i = min(max(self.img_i, 0), self.max_num - 1)
        self.scrollToItem(self.item(self.img_i))

    def new_img_item(self, img_path):
        img_label = ImgLabel(img_path=img_path, stat='doing', parent=self)
        item = QListWidgetItem()
        item.setSizeHint(img_label.sizeHint())  # 设置自定义的QListWidgetItem的sizeHint，不然无法显示
        return item, img_label

    def set_cur_deleted(self):
        widget = self.itemWidget(self.item(self.img_i))
        widget.set_as_deleted()

    def set_cur_stat(self, stat):
        widget = self.itemWidget(self.item(self.img_i))
        widget.set_stat(stat)

    def set_stat(self, i, stat):
        widget = self.itemWidget(self.item(i))
        widget.set_stat(stat)
