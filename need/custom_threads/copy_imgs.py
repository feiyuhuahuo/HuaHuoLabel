#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import shutil

from PySide6.QtCore import QThread
from need.custom_signals import BoolSignal

signal_copy_imgs_done = BoolSignal()


class CopyImgs(QThread):
    def __init__(self, imgs, dst_path, method='copy'):
        super().__init__()
        self.imgs = imgs
        self.dst_path = dst_path
        self.method = method

    def run(self):
        for one in self.imgs:
            if self.method == 'cut':
                shutil.move(one, self.dst_path)
            elif self.method == 'copy':
                shutil.copy(one, self.dst_path)

        signal_copy_imgs_done.send(True)
