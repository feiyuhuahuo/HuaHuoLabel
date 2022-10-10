#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
import cv2
import numpy as np
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox
from need.utils import ClassStatDict, get_seg_mask
from need.custom_signals import IntSignal

signal_docj_done = IntSignal()


class DeleteOneClassJsons(QThread):
    def __init__(self, imgs, old_c, old_c_i):
        super().__init__()
        self.imgs = imgs
        self.old_c = old_c
        self.old_c_i = old_c_i

    def run(self):
        for i, one in enumerate(self.imgs):
            json_path = one.replace('分割/原图', '分割/标注')[:-3] + 'json'
            with open(json_path, 'r') as f:
                content = json.load(f)
                polygons = content['polygons']

                polygons_copy = []
                for one_p in polygons:
                    if one_p['category'] != self.old_c:
                        polygons_copy.append(one_p)

            content['polygons'] = polygons_copy

            # save json
            with open(json_path, 'w') as f:
                json.dump(content, f, sort_keys=False, ensure_ascii=False, indent=4)

            # save png
            cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_UNCHANGED)
            img_h, img_w = cv2_img.shape[:2]
            seg_class_names = [aa for aa in ClassStatDict.keys()]
            seg_mask = get_seg_mask(seg_class_names, polygons_copy, img_h, img_w)

            if seg_mask.__class__ == str:
                QMessageBox.critical(self, '类别不存在', f'类别"{seg_mask}"不存在。')
                return

            if len(polygons_copy) and not (0 < seg_mask.max() <= len(seg_class_names)):
                QMessageBox.critical(self, '标注错误',
                                     f'当前仅有{len(seg_class_names)}类，但标注最大值为{seg_mask.max()}。')
                return

            cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(json_path[:-4] + 'png')

        signal_docj_done.send(self.old_c_i)
