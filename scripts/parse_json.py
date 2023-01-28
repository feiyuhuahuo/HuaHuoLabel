#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

import cv2
import json
import numpy as np


def get_seg_mask(classes, polygons, img_h, img_w):
    all_masks = []
    for i, shape in enumerate(polygons):
        label = shape['category']
        if label not in classes:
            print(f'Error, 类别"{label}"不存在。')
            return None

        class_value = classes.index(label) + 1
        mask = np.zeros((img_h, img_w), dtype=np.uint8)

        if shape['shape_type'] in ('多边形', 'Polygon'):
            points = [np.array([list(point) for point in shape['img_points']])]
            cv2.fillPoly(mask, points, 1)
        elif shape['shape_type'] in ('矩形', 'Rectangle'):
            cv2.rectangle(mask, tuple(shape['img_points'][0]), tuple(shape['img_points'][1]), 1, -1)
        elif shape['shape_type'] in ('椭圆形', 'Ellipse'):
            tl, br = tuple(shape['img_points'][0]), tuple(shape['img_points'][1])
            cx, cy = int((tl[0] + br[0]) / 2), int((tl[1] + br[1]) / 2)
            half_l, half_s = int((br[0] - tl[0]) / 2), int((br[1] - tl[1]) / 2)
            cv2.ellipse(mask, (cx, cy), (half_l, half_s), 0, 0, 360, color=1, thickness=-1)
        elif shape['shape_type'] in ('环形', 'Ring'):
            mask1 = np.zeros((img_h, img_w), dtype=np.uint8)
            mask2 = np.zeros((img_h, img_w), dtype=np.uint8)
            points1 = [np.array([tuple(point) for point in shape['img_points'][0]])]
            points2 = [np.array([tuple(point) for point in shape['img_points'][1]])]
            cv2.fillPoly(mask1, points1, 1)
            cv2.fillPoly(mask2, points2, 1)
            mask1 = np.asfortranarray(mask1, dtype='uint8')
            mask2 = np.asfortranarray(mask2, dtype='uint8')
            mask2 = ~(mask2.astype('bool'))
            mask = mask1 * mask2
        elif shape['shape_type'] in ('像素', 'Pixel'):
            for point in shape['img_points']:
                mask[point[1], point[0]] = 1

        mask = np.asfortranarray(mask, dtype='uint8') * class_value
        all_masks.append(mask)

    # 若标注有重叠区域，需要合并
    all_masks_num = np.array([(aa > 0).sum() for aa in all_masks])  # 根据像素数量来降序排序
    indices = (-1 * all_masks_num).argsort()  # * -1 来实现降序排序
    seg_mask = np.zeros((img_h, img_w), dtype='int64')
    for ii in indices:
        mask = all_masks[ii]
        seg_mask *= (mask == 0)
        seg_mask += mask

    if not (0 <= seg_mask.max() <= len(classes)):
        print(f'当前有{len(classes)}类，但mask最大值为{seg_mask.max()}。')
        return None

    return seg_mask.astype('uint8')


def load_json(path):
    with open(path, 'r') as f:
        label_file_dict = json.load(f)

    work_mode = label_file_dict['work_mode']
    all_list, train_list, val_list = [], [], []
    if work_mode in ('单分类', 'Single Cls', '多分类', 'Multi Cls'):
        for k, v in label_file_dict['labels'].items():
            info = (k, v['class'])
            all_list.append(info)
            if v['tv'] == 'train':
                train_list.append(info)
            elif v['tv'] == 'val':
                val_list.append(info)
        return all_list, train_list, val_list, label_file_dict['classes']

    if work_mode in ('语义分割', 'Sem Seg'):
        classes = label_file_dict['classes']
        for k, v in label_file_dict['labels'].items():
            img_w, img_h = v['img_width'], v['img_height']
            polygons = v['polygons']
            if polygons == ['bg']:
                polygons = []

            mask = get_seg_mask(classes, polygons, img_h, img_w)
            info = (k, mask)
            all_list.append(info)
            if v['tv'] == 'train':
                train_list.append(info)
            elif v['tv'] == 'val':
                val_list.append(info)
        return all_list, train_list, val_list, classes

    if work_mode in ('目标检测', 'Obj Det'):
        for k, v in label_file_dict['labels'].items():
            img_w, img_h = v['img_width'], v['img_height']
            targets = []
            for one in v['polygons']:
                c_name = one['category']
                img_points = one['img_points']
                x1, y1 = img_points[0]
                x2, y2 = img_points[1]
                x1 /= img_w
                x2 /= img_w
                y1 /= img_h
                y2 /= img_h
                targets.append([c_name, x1, y1, x2, y2])

            info = (k, targets)
            all_list.append(info)
            if v['tv'] == 'train':
                train_list.append(info)
            elif v['tv'] == 'val':
                val_list.append(info)
        return all_list, train_list, val_list, label_file_dict['classes']

    if work_mode in ('实例分割', 'Ins Seg'):
        classes = label_file_dict['classes']
        for k, v in label_file_dict['labels'].items():
            img_w, img_h = v['img_width'], v['img_height']

            all_boxes, all_masks = [], []
            for one in v['polygons']:
                c_name = one['category']
                mask = get_seg_mask(classes, [one], img_h, img_w)

                yy, xx = np.where(mask > 0)
                x1, x2 = int(min(xx)), int(max(xx))
                y1, y2 = int(min(yy)), int(max(yy))
                x1 /= img_w
                x2 /= img_w
                y1 /= img_h
                y2 /= img_h

                all_boxes.append([c_name, x1, y1, x2, y2])
                all_masks.append(mask)

            info = (k, all_boxes, all_masks)
            all_list.append(info)
            if v['tv'] == 'train':
                train_list.append(info)
            elif v['tv'] == 'val':
                val_list.append(info)
        return all_list, train_list, val_list, classes


if __name__ == '__main__':
    all_list, train_list, val_list, classes = load_json('E:\HuaHuoLabel_new\待分类图片\实例分割\标注/labels.json')
    print(all_list, train_list, val_list, classes)
