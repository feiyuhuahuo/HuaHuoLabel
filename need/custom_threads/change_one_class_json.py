#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
import cv2
import numpy as np

from os import path as osp
from PySide6.QtCore import QThread
from need.algorithms import get_seg_mask
from need.custom_signals import ListSignal

signal_cocc_done = ListSignal()


class ChangeOneClassCategory(QThread):
    def __init__(self, imgs, work_mode, one_file_label, separate_label,
                 label_file_dict, classes, old_c, new_c, main_window):
        super().__init__()
        self.imgs = imgs
        self.WorkMode = work_mode
        self.OneFileLabel = one_file_label
        self.SeparateLabel = separate_label
        self.label_file_dict = label_file_dict
        self.old_classes = classes
        self.old_c = old_c
        self.new_c = new_c
        self.classes = self.old_classes.copy()
        self.main_window = main_window

        if new_c in self.old_classes:
            self.classes.remove(old_c)
        else:
            ind = self.old_classes.index(old_c)
            self.classes[ind] = new_c

    def run(self):
        for i, one in enumerate(self.imgs):
            if '图片已删除' in one:
                continue

            if self.OneFileLabel:
                img_name = one.split('/')[-1]
                img_dict = self.label_file_dict['labels'].get(img_name)
                if img_dict:
                    polygons = img_dict['polygons']
                    if polygons != ['bg']:
                        for one_p in polygons:
                            if one_p['category'] == self.old_c:
                                one_p['category'] = self.new_c

            if self.SeparateLabel:
                Changed = False
                img_name = one.split('/')[-1]
                img_pure_name = img_name[:-4]
                json_path = self.main_window.get_separate_label(one, 'json')
                if not osp.exists(json_path):
                    continue

                png_path = self.main_window.get_separate_label(one, 'png')
                txt_path = self.main_window.get_separate_label(one, 'txt')

                tv = 'none'
                if osp.exists(f'{self.main_window.get_root("tv")}/imgs/train/{img_name}'):
                    tv = 'train'
                elif osp.exists(f'{self.main_window.get_root("tv")}/imgs/val/{img_name}'):
                    tv = 'val'

                tv_json = f'{self.main_window.get_root("tv")}/labels/{tv}/{img_pure_name}.json'
                tv_png = f'{self.main_window.get_root("tv")}/labels/{tv}/{img_pure_name}.png'
                tv_txt = f'{self.main_window.get_root("tv")}/labels/{tv}/{img_pure_name}.txt'

                with open(json_path, 'r') as f:
                    content = json.load(f)
                    polygons = content['polygons']

                if polygons == ['bg']:
                    continue

                for one_p in polygons:
                    if one_p['category'] == self.old_c:
                        one_p['category'] = self.new_c
                        Changed = True

                if Changed:
                    with open(json_path, 'w') as f:
                        json.dump(content, f, sort_keys=False, ensure_ascii=False, indent=4)
                    if osp.exists(tv_json):
                        with open(tv_json, 'w') as f:
                            json.dump(content, f, sort_keys=False, ensure_ascii=False, indent=4)

                    if self.WorkMode in ('目标检测', 'Obj Det'):
                        with open(txt_path, 'w') as f:
                            for one_p in polygons:
                                c_name = one_p['category']
                                [x1, y1], [x2, y2] = one_p['img_points']
                                f.writelines(f'{c_name} {x1} {y1} {x2} {y2}\n')
                        if osp.exists(tv_txt):
                            with open(tv_txt, 'w') as f:
                                for one_p in polygons:
                                    c_name = one_p['category']
                                    [x1, y1], [x2, y2] = one_p['img_points']
                                    f.writelines(f'{c_name} {x1} {y1} {x2} {y2}\n')

                if self.WorkMode in ('语义分割', 'Sem Seg'):
                    cates = [one['category'] for one in polygons]
                    cates = [self.classes.index(one) for one in cates]
                    # 只有新类别在原类别列表中，且类别索引最大值大于等于删除的类别索引，才需要重绘PNG
                    if self.new_c in self.old_classes and max(cates) >= self.old_classes.index(self.old_c):
                        cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_UNCHANGED)
                        img_h, img_w = cv2_img.shape[:2]

                        seg_mask = get_seg_mask(self.classes, polygons, img_h, img_w)
                        if seg_mask is not None:
                            cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(png_path)
                            if osp.exists(tv_png):
                                cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(tv_png)

        signal_cocc_done.send([True, self.new_c])
