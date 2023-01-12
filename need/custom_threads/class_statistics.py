#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import json
import os
import pdb

from os import sep as os_sep
from os import path as osp
from PySide6.QtCore import QThread
from need.custom_signals import ListSignal
from need.utils import uniform_path

signal_stat_info = ListSignal()


class ClassStatistics(QThread):
    def __init__(self, work_mode, img_root_path, img_num, classes, one_file_label, label_file_dict,
                 separate_label, language='CN'):
        super().__init__()
        self.WorkMode = work_mode
        self.img_root_path = img_root_path
        self.img_num = img_num
        self.classes = classes
        self.OneFileLabel = one_file_label
        self.label_file_dict = label_file_dict
        self.SeparateLabel = separate_label
        self.language = language
        if self.language == 'CN':
            self.img_folder = '原图'
            self.label_folder = '标注'
        elif self.language == 'EN':
            self.img_folder = 'Original Images'
            self.label_folder = 'Label Files'

    def run(self):
        add_info = []

        if self.language == 'CN':
            add_info.append('类别           图片数量        目标数量        目标/图片')
            add_info.append('-----------------------总图库-----------------------')
        elif self.language == 'EN':
            add_info.append('Class     Image Num  Object Num  Object/Image')
            add_info.append('----------------------Total Set----------------------')

        img_all, img_t, img_v, shape_all, shape_t, shape_v = {}, {}, {}, {}, {}, {}
        total_num = 0
        for one in self.classes:  # 通过手动setdefault来固定类别的顺序
            img_all.setdefault(one, 0)
            img_t.setdefault(one, 0)
            img_v.setdefault(one, 0)
            shape_all.setdefault(one, 0)
            shape_t.setdefault(one, 0)
            shape_v.setdefault(one, 0)

        if self.OneFileLabel:
            if self.label_file_dict.get('labels'):
                total_num = len(self.label_file_dict['labels'].keys())

                for one in self.label_file_dict['labels'].values():
                    tv = one['tv']
                    class_set = set()
                    if self.WorkMode in ('单分类', 'Single Cls'):
                        c_name = one['class']
                        class_set.add(c_name)
                        shape_all.setdefault(c_name, 0)
                        shape_all[c_name] += 1

                        if tv == 'train':
                            shape_t.setdefault(c_name, 0)
                            shape_t[c_name] += 1
                        elif tv == 'val':
                            shape_v.setdefault(c_name, 0)
                            shape_v[c_name] += 1

                    elif self.WorkMode in ('多分类', 'Multi Cls'):
                        c_name = one['class']
                        for one_c in c_name:
                            class_set.add(one_c)
                            shape_all.setdefault(one_c, 0)
                            shape_all[one_c] += 1

                            if tv == 'train':
                                shape_t.setdefault(one_c, 0)
                                shape_t[one_c] += 1
                            elif tv == 'val':
                                shape_v.setdefault(one_c, 0)
                                shape_v[one_c] += 1

                    elif self.WorkMode in ('语义分割', 'Sem Seg', '目标检测', 'Obj Det', '实例分割', 'Ins Seg'):
                        polygons = one['polygons']
                        if polygons == ['bg']:
                            polygons = []

                        if polygons:
                            for one_p in polygons:
                                c_name = one_p['category']
                                class_set.add(c_name)
                                shape_all.setdefault(c_name, 0)
                                shape_all[c_name] += 1

                                if tv == 'train':
                                    shape_t.setdefault(c_name, 0)
                                    shape_t[c_name] += 1
                                elif tv == 'val':
                                    shape_v.setdefault(c_name, 0)
                                    shape_v[c_name] += 1

                    for one_c in class_set:
                        img_all.setdefault(one_c, 0)
                        img_all[one_c] += 1

                        if tv == 'train':
                            img_t.setdefault(one_c, 0)
                            img_t[one_c] += 1
                        elif tv == 'val':
                            img_v.setdefault(one_c, 0)
                            img_v[one_c] += 1

        elif self.SeparateLabel:
            if self.WorkMode in ('单分类', 'Single Cls'):
                files = glob.glob(f'{self.img_root_path}/{self.WorkMode}/{self.img_folder}/*')
                files = [uniform_path(one) for one in files]

                for one in files:
                    if not os.path.isdir(one):
                        continue

                    c_name = one.split('/')[-1]
                    if c_name != 'imgs':
                        c_imgs = glob.glob(f'{one}/*')
                        c_num = len(c_imgs)
                        total_num += c_num
                        shape_all.setdefault(c_name, 0)
                        shape_all[c_name] += c_num
                        img_all.setdefault(c_name, 0)
                        img_all[c_name] += c_num

                        for one_img in c_imgs:
                            name = one_img.split(os_sep)[-1]
                            if osp.exists(f'{self.img_root_path}/{self.WorkMode}/imgs/train/{c_name}/{name}'):
                                shape_t.setdefault(c_name, 0)
                                shape_t[c_name] += 1
                                img_t.setdefault(c_name, 0)
                                img_t[c_name] += 1
                            if osp.exists(f'{self.img_root_path}/{self.WorkMode}/imgs/val/{c_name}/{name}'):
                                shape_v.setdefault(c_name, 0)
                                shape_v[c_name] += 1
                                img_v.setdefault(c_name, 0)
                                img_v[c_name] += 1

            elif self.WorkMode in ('多分类', 'Multi Cls'):
                files = glob.glob(f'{self.img_root_path}/{self.WorkMode}/{self.label_folder}/*.txt')
                for one in files:
                    file_name = one.split(os_sep)[-1]

                    with open(one, 'r', encoding='utf-8') as f:
                        names = f.readlines()
                    if names:
                        total_num += 1
                        for one_c in names:
                            c_name = one_c.strip()
                            shape_all.setdefault(c_name, 0)
                            shape_all[c_name] += 1
                            img_all.setdefault(c_name, 0)
                            img_all[c_name] += 1

                            if osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/train/{file_name}'):
                                shape_t.setdefault(c_name, 0)
                                shape_t[c_name] += 1
                                img_t.setdefault(c_name, 0)
                                img_t[c_name] += 1
                            if osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/val/{file_name}'):
                                shape_v.setdefault(c_name, 0)
                                shape_v[c_name] += 1
                                img_v.setdefault(c_name, 0)
                                img_v[c_name] += 1

            elif self.WorkMode in ('语义分割', 'Sem Seg', '目标检测', 'Obj Det', '实例分割', 'Ins Seg'):
                files = glob.glob(f'{self.img_root_path}/{self.WorkMode}/{self.label_folder}/*.json')
                for one in files:
                    class_set = set()
                    file_name = one.split(os_sep)[-1]
                    has_t, has_v = False, False
                    if osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/train/{file_name}'):
                        has_t = True
                    if osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/val/{file_name}'):
                        has_v = True

                    if 'labels.json' not in one:
                        with open(one, 'r') as f:
                            content = json.load(f)

                        total_num += 1
                        polygons = content['polygons']
                        if polygons == ['bg']:
                            if self.language == 'CN':
                                bg_key = '背景'
                            elif self.language == 'EN':
                                bg_key = 'background'

                            class_set.add(bg_key)
                            shape_all.setdefault(bg_key, 0)
                            shape_all[bg_key] += 1

                            if has_t:
                                shape_t.setdefault(bg_key, 0)
                                shape_t[bg_key] += 1
                            if has_v:
                                shape_v.setdefault(bg_key, 0)
                                shape_v[bg_key] += 1
                        else:
                            for one_shape in polygons:
                                c_name = one_shape['category']
                                class_set.add(c_name)
                                shape_all.setdefault(c_name, 0)
                                shape_all[c_name] += 1

                                if has_t:
                                    shape_t.setdefault(c_name, 0)
                                    shape_t[c_name] += 1
                                if has_v:
                                    shape_v.setdefault(c_name, 0)
                                    shape_v[c_name] += 1

                    for one_c in class_set:
                        img_all.setdefault(one_c, 0)
                        img_all[one_c] += 1

                        if has_t:
                            img_t.setdefault(one_c, 0)
                            img_t[one_c] += 1
                        elif has_v:
                            img_v.setdefault(one_c, 0)
                            img_v[one_c] += 1

        for k, v in img_all.items():
            shape_num = shape_all[k]
            ratio = 0. if v == 0 else round(float(shape_num / v), 1)
            add_info.append(f'{k:{chr(12288)}<7}{v}\t           {shape_num:<12}\t{ratio}')

        if self.language == 'CN':
            add_info += [f'\n已标注图片数量：{total_num}', f'总图片数量：{self.img_num}']
        elif self.language == 'EN':
            add_info += [f'\nLabeled Count: {total_num}', f'Total Count: {self.img_num}']

        if self.language == 'CN':
            add_info.append('\n-----------------------训练集-----------------------')
        elif self.language == 'EN':
            add_info.append('\n----------------------Train Set----------------------')
        for k, v in img_t.items():
            shape_num = shape_t[k]
            ratio = 0. if v == 0 else round(float(shape_num / v), 1)
            add_info.append(f'{k:{chr(12288)}<7}{v}\t           {shape_num:<12}\t{ratio}')

        if self.language == 'CN':
            add_info.append('\n-----------------------验证集-----------------------')
        elif self.language == 'EN':
            add_info.append('\n-----------------------Val Set-----------------------')
        for k, v in img_v.items():
            shape_num = shape_v[k]
            ratio = 0. if v == 0 else round(float(shape_num / v), 1)
            add_info.append(f'{k:{chr(12288)}<7}{v}\t           {shape_num:<12}\t{ratio}')

        signal_stat_info.send(add_info)
