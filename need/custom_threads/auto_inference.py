#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
import pdb
import math
import cv2
from os import sep as os_sep
import numpy as np
from PySide6.QtCore import QThread
from need.utils import douglas_peuker
from need.custom_signals import StrSignal, IntSignal, BoolSignal

signal_ai_progress_text = StrSignal()
signal_ai_progress_value = IntSignal()
signal_auto_infer_done = BoolSignal()


class RunInference(QThread):
    def __init__(self, sess, imgs, classes, dp_para=(2, 4, 40), filter_area=16):
        super().__init__()
        self.sess = sess
        self.imgs = imgs
        self.classes = classes
        self.dp_para = dp_para
        self.filter_area = filter_area

    def run(self):
        img_num = len(self.imgs)
        inp = self.sess.get_inputs()[0]
        in_shape, in_name = tuple(inp.shape), inp.name
        img_root = self.imgs[0].split(os_sep)[0]
        colors = list(ColorCode.keys())

        for i, one in enumerate(self.imgs):
            signal_ai_progress_value.send(int((i + 1) / img_num * 100))

            img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_COLOR)
            img_shape = img.shape
            if img_shape != in_shape:
                img = cv2.resize(img, in_shape[:2])

            result = self.sess.run(None, {in_name: img})[0][0]
            result = cv2.resize(result.astype('uint8'), img_shape[:2], interpolation=cv2.INTER_NEAREST)

            json_dict = {'img_height': img_shape[0], 'img_width': img_shape[1], 'polygons': []}
            dp_thre = math.sqrt((img_shape[0] * img_shape[1]) / (512 * 512)) * self.dp_para[0]

            for l in range(len(self.classes)):
                one_c_png = (result == (l + 1)).astype('uint8')
                if one_c_png.sum() > 0:
                    ret, thresh = cv2.threshold(one_c_png, 0, 255, cv2.THRESH_BINARY)
                    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

                    contours_sq = []
                    for one_con in contours:
                        sq = douglas_peuker(one_con.squeeze(1).tolist(), dp_thre, self.dp_para[1], self.dp_para[2])
                        contours_sq.append(sq)

                    for j in range(len(contours_sq)):
                        bg = np.zeros(img_shape[:2], dtype='uint8')
                        hie = hierarchy[0][j]

                        if hie[2] == hie[3] == -1:
                            con = contours_sq[j]
                            bg = cv2.drawContours(bg, [np.array(con)], -1, 1, -1)
                            if bg.sum() > self.filter_area:
                                json_dict['polygons'].append({'category': self.classes[l], 'qcolor': colors[l]})
                                json_dict['polygons'][-1]['shape_type'] = '多边形'
                                json_dict['polygons'][-1]['img_points'] = con
                        else:
                            if hie[2] != -1:
                                con = [contours_sq[j], contours_sq[hie[2]]]
                                bg = cv2.drawContours(bg, [np.array(con[0]), np.array(con[1])], -1, 1, -1)
                                if bg.sum() > self.filter_area:
                                    json_dict['polygons'].append({'category': self.classes[l], 'qcolor': colors[l]})
                                    json_dict['polygons'][-1]['shape_type'] = '环形'
                                    json_dict['polygons'][-1]['img_points'] = con

            save_path = img_root.replace('原图', '自动标注')
            png_name = one.split(os_sep)[-1][:-3] + 'png'
            cv2.imencode('.png', result)[1].tofile(f'{save_path}/{png_name}')

            json_name = one.split(os_sep)[-1][:-3] + 'json'
            with open(f'{save_path}/{json_name}', 'w') as f:
                json.dump(json_dict, f, sort_keys=False, ensure_ascii=False, indent=4)

            signal_ai_progress_text.send(f'{i + 1}/{img_num}')

        signal_auto_infer_done.send(True)
