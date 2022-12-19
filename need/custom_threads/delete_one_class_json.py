#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
import pdb
import cv2
import numpy as np
import glob

from os import path as osp
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox
from need.utils import get_seg_mask, uniform_path, path_to, file_remove
from need.custom_signals import BoolSignal

signal_docl_done = BoolSignal()


class DeleteOneClassLabels(QThread):
    def __init__(self, img_dir, work_mode, one_file_label, separate_label, label_file_dict, classes, del_c):
        super().__init__()
        self.img_dir = img_dir
        self.WorkMode = work_mode
        self.OneFileLabel = one_file_label
        self.SeparateLabel = separate_label
        self.label_file_dict = label_file_dict
        self.classes = classes
        self.del_c = del_c
        self.classes.remove(self.del_c)

    def run(self):
        imgs = glob.glob(f'{self.img_dir}/原图/*')
        imgs = [uniform_path(aa) for aa in imgs]
        imgs.sort()

        for i, one in enumerate(imgs):
            if self.OneFileLabel:
                img_name = one.split('/')[-1]
                img_dict = self.label_file_dict['labels'].get(img_name)
                if img_dict:
                    polygons = img_dict['polygons']
                    if polygons != ['bg']:
                        new_polygons = []
                        for one_p in polygons:
                            if one_p['category'] != self.del_c:
                                new_polygons.append(one_p.copy())

                        if len(new_polygons):
                            img_dict['polygons'] = new_polygons
                        else:
                            self.label_file_dict['labels'].pop(img_name)

            if self.SeparateLabel:
                json_path = path_to(one, img2json=True)
                png_path = path_to(one, img2png=True)
                txt_path = path_to(one, img2txt=True)
                if not osp.exists(json_path):
                    continue

                with open(json_path, 'r') as f:
                    content = json.load(f)

                polygons = content['polygons']
                if polygons != ['bg']:
                    new_polygons = []
                    for one_p in polygons:
                        if one_p['category'] != self.del_c:
                            new_polygons.append(one_p.copy())

                    if len(new_polygons) == 0:
                        file_remove(json_path)
                        file_remove(png_path)
                        file_remove(txt_path)
                    else:
                        if len(new_polygons) != len(polygons):
                            content['polygons'] = new_polygons
                            with open(json_path, 'w') as f:
                                json.dump(content, f, sort_keys=False, ensure_ascii=False, indent=4)

                            if self.WorkMode == '目标检测':
                                with open(txt_path, 'w') as f:
                                    for one_p in new_polygons:
                                        c_name = one_p['category']
                                        [x1, y1], [x2, y2] = one['img_points']
                                        f.writelines(f'{c_name} {x1} {y1} {x2} {y2}\n')

                        if self.WorkMode == '语义分割':
                            cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_UNCHANGED)
                            img_h, img_w = cv2_img.shape[:2]
                            seg_mask = get_seg_mask(self.classes, new_polygons, img_h, img_w)

                            if seg_mask.__class__ == str:
                                QMessageBox.critical(None, '类别不存在', f'类别"{seg_mask}"不存在。')
                                signal_docl_done.send(False)
                                return

                            if not (0 < seg_mask.max() <= len(self.classes)):
                                QMessageBox.critical(None, '标注错误',
                                                     f'当前仅有{len(self.classes)}类，但标注最大值为{seg_mask.max()}。')
                                signal_docl_done.send(False)
                                return

                            cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(png_path)

        signal_docl_done.send(True)
