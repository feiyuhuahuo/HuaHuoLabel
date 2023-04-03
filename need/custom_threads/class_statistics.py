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
    def __init__(self, work_mode, img_num, classes, one_file_label, label_file_dict,
                 separate_label, main_window, language='CN'):
        super().__init__()
        self.WorkMode = work_mode
        self.img_num = img_num
        self.classes = classes
        self.OneFileLabel = one_file_label
        self.label_file_dict = label_file_dict
        self.SeparateLabel = separate_label
        self.main_window = main_window
        self.language = language

    def run(self):
        add_info = []
        img_all, img_t, img_v, shape_all, shape_t, shape_v = {}, {}, {}, {}, {}, {}
        total_num, train_num, val_num = 0, 0, 0
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
                    if tv == 'train':
                        train_num += 1
                    elif tv == 'val':
                        val_num += 1

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
                            if self.language == 'CN':
                                c_name = '背景'
                            elif self.language == 'EN':
                                c_name = 'BG'

                            polygons = [{'category': c_name}]

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
                files = glob.glob(f'{self.main_window.get_root("separate")}/*')
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
                            if osp.exists(f'{self.main_window.get_root("tv")}/imgs/train/{c_name}/{name}'):
                                train_num += 1
                                shape_t.setdefault(c_name, 0)
                                shape_t[c_name] += 1
                                img_t.setdefault(c_name, 0)
                                img_t[c_name] += 1
                            if osp.exists(f'{self.main_window.get_root("tv")}/imgs/val/{c_name}/{name}'):
                                val_num += 1
                                shape_v.setdefault(c_name, 0)
                                shape_v[c_name] += 1
                                img_v.setdefault(c_name, 0)
                                img_v[c_name] += 1

            elif self.WorkMode in ('多分类', 'Multi Cls'):
                files = glob.glob(f'{self.main_window.get_root("separate")}/*.txt')
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

                            if osp.exists(f'{self.main_window.get_root("tv")}/labels/train/{file_name}'):
                                train_num += 1
                                shape_t.setdefault(c_name, 0)
                                shape_t[c_name] += 1
                                img_t.setdefault(c_name, 0)
                                img_t[c_name] += 1
                            if osp.exists(f'{self.main_window.get_root("tv")}/labels/val/{file_name}'):
                                val_num += 1
                                shape_v.setdefault(c_name, 0)
                                shape_v[c_name] += 1
                                img_v.setdefault(c_name, 0)
                                img_v[c_name] += 1

            elif self.WorkMode in ('语义分割', 'Sem Seg', '目标检测', 'Obj Det', '实例分割', 'Ins Seg'):
                files = glob.glob(f'{self.main_window.get_root("separate")}/*.json')
                for one in files:
                    class_set = set()
                    file_name = one.split(os_sep)[-1]
                    has_t, has_v = False, False
                    if osp.exists(f'{self.main_window.get_root("tv")}/labels/train/{file_name}'):
                        train_num += 1
                        has_t = True
                    if osp.exists(f'{self.main_window.get_root("tv")}/labels/val/{file_name}'):
                        val_num += 1
                        has_v = True

                    if 'labels.json' not in one:
                        with open(one, 'r', encoding='utf-8') as f:
                            content = json.load(f)

                        total_num += 1
                        polygons = content['polygons']
                        if polygons == ['bg']:
                            if self.language == 'CN':
                                c_name = '背景'
                            elif self.language == 'EN':
                                c_name = 'BG'

                            polygons = [{'category': c_name}]

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

        if self.language == 'CN':
            add_info.append('类别            图片数量       目标数量       目标/图片')
            add_info.append(self.set_title(f'总集 ({total_num})'))
        elif self.language == 'EN':
            add_info.append('Class           Image Num       Obj Num       Obj/Image')
            add_info.append(self.set_title(f'Total Set ({total_num})'))

        for k, v in img_all.items():
            shape_num = shape_all[k]
            ratio = 0. if v == 0 else round(float(shape_num / v), 1)
            add_info.append(self.format(k, v, shape_num, ratio))

        unl_num, und_num = self.img_num - total_num, total_num - train_num - val_num
        if self.language == 'CN':
            add_info.append(f'\n总图片数量：{self.img_num}，未标注数量：{unl_num}，未划分数量：{und_num}')
        elif self.language == 'EN':
            add_info.append(f'\nTotal: {total_num}, Unlabelled: {unl_num}, Undivided: {und_num}')

        if self.language == 'CN':
            add_info.append('\n' + self.set_title(f'训练集 ({train_num})'))
        elif self.language == 'EN':
            add_info.append('\n' + self.set_title(f'Train Set ({train_num})'))
        for k, v in img_t.items():
            shape_num = shape_t[k]
            ratio = 0. if v == 0 else round(float(shape_num / v), 1)
            add_info.append(self.format(k, v, shape_num, ratio))

        if self.language == 'CN':
            add_info.append('\n' + self.set_title(f'验证集 ({val_num})'))
        elif self.language == 'EN':
            add_info.append('\n' + self.set_title(f'Val Set ({val_num})'))
        for k, v in img_v.items():
            shape_num = shape_v[k]
            ratio = 0. if v == 0 else round(float(shape_num / v), 1)
            add_info.append(self.format(k, v, shape_num, ratio))

        signal_stat_info.send(add_info)

    def format(self, t1, t2, t3, t4):
        ch_num, en_num = 0, 0
        for one in t1:
            if u'\u4e00' <= one <= u'\u9fff':
                ch_num += 1
            else:
                en_num += 1

        if ch_num == 0:
            if en_num <= 9:
                t1 += '\t'
        elif ch_num == 1:
            if en_num <= 7:
                t1 += '\t'
        elif ch_num == 2:
            if en_num <= 5:
                t1 += '\t'
        elif ch_num == 3:
            if en_num <= 3:
                t1 += '\t'
        elif ch_num == 4:
            if en_num <= 1:
                t1 += '\t'

        return f'{t1}\t{t2}\t     {t3}\t         {t4}'

    def set_title(self, title):
        title_len = 0
        for one in title:
            if u'\u4e00' <= one <= u'\u9fff':
                title_len += 2
            else:
                title_len += 1

        line_len = 55 - title_len
        if line_len % 2 == 0:
            left_len = right_len = line_len // 2
        else:
            right_len = line_len // 2
            left_len = right_len + 1

        return '-' * left_len + title + '-' * right_len
