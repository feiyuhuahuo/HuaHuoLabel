#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
import pdb
import cv2
import numpy as np
import glob

from os import path as osp
from PySide6.QtCore import QThread
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
            img_name = one.split('/')[-1]

            tv = 'none'
            if osp.exists(f'{self.img_dir}/imgs/train/{img_name}'):
                tv = 'train'
            elif osp.exists(f'{self.img_dir}/imgs/val/{img_name}'):
                tv = 'val'

            tv_img = f'{self.img_dir}/imgs/{tv}/{img_name}'

            if self.OneFileLabel:
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
                            file_remove(tv_img)
                            self.label_file_dict['labels'].pop(img_name)

            if self.SeparateLabel:
                img_pure_name = img_name[:-4]
                json_path = path_to(one, img2json=True)
                png_path = path_to(one, img2png=True)
                txt_path = path_to(one, img2txt=True)
                if not osp.exists(json_path):
                    continue

                tv_json = f'{self.img_dir}/labels/{tv}/{img_pure_name}.json'
                tv_png = f'{self.img_dir}/labels/{tv}/{img_pure_name}.png'
                tv_txt = f'{self.img_dir}/labels/{tv}/{img_pure_name}.txt'

                with open(json_path, 'r') as f:
                    content = json.load(f)

                polygons = content['polygons']
                if polygons != ['bg']:
                    new_polygons = []
                    for one_p in polygons:
                        if one_p['category'] != self.del_c:
                            new_polygons.append(one_p.copy())

                    if len(new_polygons) == 0:
                        file_remove(tv_img)
                        file_remove(json_path)
                        file_remove(tv_json)
                        file_remove(png_path)
                        file_remove(tv_png)
                        file_remove(txt_path)
                        file_remove(tv_txt)
                    else:
                        if len(new_polygons) != len(polygons):
                            content['polygons'] = new_polygons
                            with open(json_path, 'w') as f:
                                json.dump(content, f, sort_keys=False, ensure_ascii=False, indent=4)
                            if osp.exists(tv_json):
                                with open(tv_json, 'w') as f:
                                    json.dump(content, f, sort_keys=False, ensure_ascii=False, indent=4)

                            if self.WorkMode == '目标检测':
                                with open(txt_path, 'w') as f:
                                    for one_p in new_polygons:
                                        c_name = one_p['category']
                                        [x1, y1], [x2, y2] = one_p['img_points']
                                        f.writelines(f'{c_name} {x1} {y1} {x2} {y2}\n')
                                if osp.exists(tv_txt):
                                    with open(tv_txt, 'w') as f:
                                        for one_p in new_polygons:
                                            c_name = one_p['category']
                                            [x1, y1], [x2, y2] = one_p['img_points']
                                            f.writelines(f'{c_name} {x1} {y1} {x2} {y2}\n')

                        if self.WorkMode == '语义分割':
                            cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_UNCHANGED)
                            img_h, img_w = cv2_img.shape[:2]
                            seg_mask = get_seg_mask(self.classes, new_polygons, img_h, img_w)
                            if seg_mask is not None:
                                cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(png_path)
                                if osp.exists(tv_png):
                                    cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(tv_png)

        signal_docl_done.send(True)
