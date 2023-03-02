#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
import cv2

from os import path as osp
from PySide6.QtCore import QThread
from PySide6.QtGui import QPixmap
from need.utils import get_seg_mask, file_remove
from need.custom_signals import ListSignal

signal_usp_done = ListSignal()
signal_usp_progress_value = ListSignal()
signal_usp_progress_text = ListSignal()


# 经测试，线程里面不能有静态的QMessageBox，否则唤起后软件会崩溃
class UpdateSemanticPngs(QThread):
    def __init__(self, imgs, classes, main_window):
        super().__init__()
        self.imgs = imgs
        self.classes = classes
        self.img_num = len(self.imgs)
        self.main_window = main_window

    def run(self):
        num = 0
        for i, one in enumerate(self.imgs):
            if '图片已删除' in one:
                continue

            signal_usp_progress_value.send([self.__class__, int((i + 1) / self.img_num * 100)])

            img_name = one.split('/')[-1]
            img_w, img_h = QPixmap(one).size().toTuple()
            json_path = self.main_window.get_separate_label(one, 'json')
            png_path = self.main_window.get_separate_label(one, 'png')
            png_name = png_path.split('/')[-1]

            tv = 'none'
            if osp.exists(f'{self.main_window.get_toot("tv")}/imgs/train/{img_name}'):
                tv = 'train'
            elif osp.exists(f'{self.main_window.get_toot("tv")}/imgs/val/{img_name}'):
                tv = 'val'

            tv_img = f'{self.main_window.get_toot("tv")}/imgs/{tv}/{img_name}'
            tv_json = f'{self.main_window.get_toot("tv")}/labels/{tv}/{img_name[:-4]}.json'
            tv_png = f'{self.main_window.get_toot("tv")}/labels/{tv}/{png_name}'

            if osp.exists(json_path):
                with open(json_path, 'r') as f:
                    content = json.load(f)
                    polygons = content['polygons']

                if polygons:
                    if polygons == ['bg']:
                        polygons = []

                    seg_mask = get_seg_mask(self.classes, polygons, img_h, img_w)
                    if seg_mask is not None:
                        cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(png_path)
                        if osp.exists(tv_png):
                            cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(tv_png)
                else:
                    file_remove([tv_img, json_path, tv_json, png_path, tv_png])

                num += 1
                signal_usp_progress_text.send([self.__class__, f'{num}'])

        signal_usp_done.send([True, f'{num}'])
