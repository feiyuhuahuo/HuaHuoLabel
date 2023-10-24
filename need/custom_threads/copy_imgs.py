#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import shutil

from PySide6.QtCore import QThread
from need.custom_signals import StrSignal
from PIL import Image, ImageOps

signal_copy_imgs_done = StrSignal()


class CopyImgs(QThread):
    def __init__(self, imgs, dst_path):
        super().__init__()
        self.imgs = imgs
        self.dst_path = dst_path
        self.support_mode = ('P', 'RGB', 'RGBA')

    def run(self):
        ImgFiltered = False
        for one in self.imgs:
            img = Image.open(one)  # 处理exif旋转信息

            if img.mode not in self.support_mode:
                ImgFiltered = True
                continue

            if (img.getexif()).get(274):
                img = ImageOps.exif_transpose(img)
                img_name = one.split('/')[-1]
                img.save(f'{self.dst_path}/{img_name}')
            else:
                shutil.copy(one, self.dst_path)

        if ImgFiltered:
            signal_copy_imgs_done.send(self.tr('部分图片的模式不支持，已过滤。'))
        else:
            signal_copy_imgs_done.send('')
