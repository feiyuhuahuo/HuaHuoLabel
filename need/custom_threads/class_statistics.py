#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import json
import os

from os import sep as os_sep
from os import path as osp
from PySide6.QtCore import QThread
from need.custom_signals import ListSignal

signal_stat_info = ListSignal()


class ClassStatistics(QThread):
    def __init__(self, work_mode, img_root_path, img_num, one_file_label, label_file_dict, separate_label):
        super().__init__()
        self.WorkMode = work_mode
        self.img_root_path = img_root_path
        self.img_num = img_num
        self.OneFileLabel = one_file_label
        self.label_file_dict = label_file_dict
        self.SeparateLabel = separate_label

    def run(self):
        add_info = ['----------总图库----------']
        all_stat, t_stat, v_stat = {}, {}, {}
        total_num = 0
        if self.OneFileLabel:
            if self.label_file_dict.get('labels'):
                total_num = len(self.label_file_dict['labels'].keys())

                for one in self.label_file_dict['labels'].values():
                    tv = one['tv']
                    if self.WorkMode in ('单分类', 'Single Cls'):
                        c_name = one['class']
                        all_stat.setdefault(c_name, 0)
                        all_stat[c_name] += 1

                        if tv == 'train':
                            t_stat.setdefault(c_name, 0)
                            t_stat[c_name] += 1
                        elif tv == 'val':
                            v_stat.setdefault(c_name, 0)
                            v_stat[c_name] += 1

                    elif self.WorkMode in ('多分类', 'Multi Cls'):
                        c_name = one['class']
                        for one_c in c_name:
                            all_stat.setdefault(one_c, 0)
                            all_stat[one_c] += 1

                            if tv == 'train':
                                t_stat.setdefault(one_c, 0)
                                t_stat[one_c] += 1
                            elif tv == 'val':
                                v_stat.setdefault(one_c, 0)
                                v_stat[one_c] += 1

                    elif self.WorkMode in ('语义分割', 'Sem Seg', '目标检测', 'Obj Det', '实例分割', 'Ins Seg'):
                        polygons = one['polygons']
                        if polygons == ['bg']:
                            polygons = []

                        if polygons:
                            for one_p in polygons:
                                c_name = one_p['category']
                                all_stat.setdefault(c_name, 0)
                                all_stat[c_name] += 1

                                if tv == 'train':
                                    t_stat.setdefault(c_name, 0)
                                    t_stat[c_name] += 1
                                elif tv == 'val':
                                    v_stat.setdefault(c_name, 0)
                                    v_stat[c_name] += 1
        elif self.SeparateLabel:
            if self.WorkMode in ('单分类', 'Single Cls'):
                files = glob.glob(f'{self.img_root_path}/{self.WorkMode}/原图/*')
                for one in files:
                    if os.path.isdir(one):
                        c_name = one.split(os_sep)[-1]
                        if c_name != 'imgs':
                            c_imgs = glob.glob(f'{one}/*')
                            c_num = len(c_imgs)
                            total_num += c_num
                            all_stat.setdefault(c_name, c_num)

                            for one_img in c_imgs:
                                name = one_img.split(os_sep)[-1]
                                if osp.exists(f'{self.img_root_path}/{self.WorkMode}/imgs/train/{c_name}/{name}'):
                                    t_stat.setdefault(c_name, 0)
                                    t_stat[c_name] += 1
                                elif osp.exists(f'{self.img_root_path}/{self.WorkMode}/imgs/val/{c_name}/{name}'):
                                    v_stat.setdefault(c_name, 0)
                                    v_stat[c_name] += 1

            elif self.WorkMode in ('多分类', 'Multi Cls'):
                files = glob.glob(f'{self.img_root_path}/{self.WorkMode}/标注/*.txt')
                for one in files:
                    file_name = one.split(os_sep)[-1]

                    with open(one, 'r', encoding='utf-8') as f:
                        names = f.readlines()
                    if names:
                        total_num += 1
                        for one_c in names:
                            c_name = one_c.strip()
                            all_stat.setdefault(c_name, 0)
                            all_stat[c_name] += 1

                            if osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/train/{file_name}'):
                                t_stat.setdefault(c_name, 0)
                                t_stat[c_name] += 1
                            elif osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/val/{file_name}'):
                                v_stat.setdefault(c_name, 0)
                                v_stat[c_name] += 1

            elif self.WorkMode in ('语义分割', 'Sem Seg', '目标检测', 'Obj Det', '实例分割', 'Ins Seg'):
                files = glob.glob(f'{self.img_root_path}/{self.WorkMode}/标注/*.json')
                for one in files:
                    file_name = one.split(os_sep)[-1]
                    has_t, has_v = False, False
                    if osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/train/{file_name}'):
                        has_t = True
                    elif osp.exists(f'{self.img_root_path}/{self.WorkMode}/labels/val/{file_name}'):
                        has_v = True

                    if 'labels.json' not in one:
                        with open(one, 'r') as f:
                            content = json.load(f)

                        total_num += 1
                        polygons = content['polygons']
                        if polygons == ['bg']:
                            all_stat.setdefault('背景', 0)
                            all_stat['背景'] += 1

                            if has_t:
                                t_stat.setdefault('背景', 0)
                                t_stat['背景'] += 1
                            elif has_v:
                                v_stat.setdefault('背景', 0)
                                v_stat['背景'] += 1
                        else:
                            for one_shape in polygons:
                                c_name = one_shape['category']
                                all_stat.setdefault(c_name, 0)
                                all_stat[c_name] += 1

                                if has_t:
                                    t_stat.setdefault(c_name, 0)
                                    t_stat[c_name] += 1
                                elif has_v:
                                    v_stat.setdefault(c_name, 0)
                                    v_stat[c_name] += 1

        for k, v in all_stat.items():
            add_info.append(f'{k}: {v}')

        add_info += [f'\n已标注图片数量：{total_num}', f'总图片数量：{self.img_num}']
        add_info.append('\n----------训练集----------')
        for k, v in t_stat.items():
            add_info.append(f'{k}: {v}')
        add_info.append('\n----------验证集----------')
        for k, v in v_stat.items():
            add_info.append(f'{k}: {v}')

        signal_stat_info.send(add_info)
