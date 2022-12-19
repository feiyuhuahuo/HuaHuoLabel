#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import json
import os

from os import sep as os_sep
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
        add_info, stat = [], {}
        total_num = 0
        if self.OneFileLabel:
            if self.label_file_dict.get('labels'):
                for one in self.label_file_dict['labels'].values():
                    if self.WorkMode == '单分类':
                        c_name = one['class']
                        if c_name:
                            total_num += 1
                            stat.setdefault(c_name, 0)
                            stat[c_name] += 1
                        final_info = [f'已分类图片数量：{total_num}', f'总图片数量：{self.img_num}']
                    elif self.WorkMode == '多分类':
                        c_name = one['class']
                        if c_name:
                            total_num += 1
                            for one_c in c_name:
                                stat.setdefault(one_c, 0)
                                stat[one_c] += 1
                        final_info = [f'已分类图片数量：{total_num}', f'总图片数量：{self.img_num}']
                    elif self.WorkMode in ('语义分割', '目标检测', '实例分割'):
                        polygons = one['polygons']
                        if polygons == ['bg']:
                            polygons = []
                        if polygons:
                            total_num += 1
                            for one_p in polygons:
                                c_name = one_p['category']
                                stat.setdefault(c_name, 0)
                                stat[c_name] += 1
                        final_info = [f'带标注图片数量：{total_num}', f'总图片数量：{self.img_num}']

                for k, v in stat.items():
                    add_info.append(f'{k}: {v}')
                add_info += final_info
        elif self.SeparateLabel:
            if self.WorkMode == '单分类':
                files = glob.glob(f'{self.img_root_path}/单分类/*')
                for one in files:
                    if os.path.isdir(one):
                        c_name = one.split(os_sep)[-1]
                        if c_name != 'imgs':
                            c_num = len(glob.glob(f'{one}/*'))
                            add_info.append(f'{c_name}: {c_num}')
                            total_num += c_num

                add_info += [f'已分类图片数量：{total_num}', f'总图片数量：{self.img_num}']
            elif self.WorkMode == '多分类':
                files = glob.glob(f'{self.img_root_path}/多分类/标注/*.txt')
                for one in files:
                    with open(one, 'r', encoding='utf-8') as f:
                        names = f.readlines()
                    if names:
                        total_num += 1
                        for one_c in names:
                            c_name = one_c.strip()
                            stat.setdefault(c_name, 0)
                            stat[c_name] += 1

                for k, v in stat.items():
                    add_info.append(f'{k}: {v}')
                add_info += [f'已分类图片数量：{total_num}', f'总图片数量：{self.img_num}']
            elif self.WorkMode in ('语义分割', '目标检测', '实例分割'):
                files = glob.glob(f'{self.img_root_path}/{self.WorkMode}/标注/*.json')
                for one in files:
                    if 'labels.json' not in one:
                        with open(one, 'r') as f:
                            content = json.load(f)

                        polygons = content['polygons']
                        if polygons == ['bg']:
                            polygons = []
                        if polygons:
                            total_num += 1
                            for one_shape in polygons:
                                c_name = one_shape['category']
                                stat.setdefault(c_name, 0)
                                stat[c_name] += 1

                for k, v in stat.items():
                    add_info.append(f'{k}: {v}')
                add_info += [f'带标注图片数量：{total_num}', f'总图片数量：{self.img_num}']

        signal_stat_info.send(add_info)
