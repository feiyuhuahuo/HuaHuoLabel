#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import json

import cv2
import labelme
import numpy as np

class_names = ['background', '黑斑', '断栅', '划伤', '脏污']

label_count = {}
for aa in class_names:
    label_count[aa] = 0

# cv2.namedWindow('aa', cv2.WINDOW_NORMAL)
# cv2.resizeWindow('aa', 900, 900)

for aa in sorted(glob.glob('D://Data/EL_jingke/seg/*.json')):
    print(aa)
    with open(aa, 'r', encoding='utf-8') as f:
        label_data = json.load(f)

    img_h, img_w = label_data['imageHeight'], label_data['imageWidth']

    all_masks = []
    for shape in label_data['shapes']:
        points = shape['points']
        label = shape['label']
        assert label in class_names, f'Not existed class name: {label}.'
        label_count[label] += 1
        class_value = class_names.index(label)

        shape_type = shape.get('shape_type', None)
        mask = labelme.utils.shape_to_mask((img_h, img_w), points, shape_type)

        mask = np.asfortranarray(mask.astype(np.uint8))[:, :, None] * class_value
        all_masks.append(mask)

    # 根据像素数量来降序排序
    all_masks_num = np.array([(aa > 0).sum() for aa in all_masks])
    indices = (-1 * all_masks_num).argsort()  # * -1 来实现降序排序

    seg_mask = np.zeros((img_h, img_w, 1), dtype='int64')
    for ii in indices:
        mask = all_masks[ii]
        seg_mask *= (mask == 0)
        seg_mask += mask

    print(seg_mask.max())
    assert 0 < seg_mask.max() < len(class_names), 'Incorrect annotation.'
    # cv2.imshow('aa', (seg_mask * 50).astype('uint8'))
    # cv2.waitKey()
    cv2.imwrite(aa.replace('json', 'png'), seg_mask)

for kk, vv in label_count.items():
    print(kk, vv)

imgs = glob.glob('D://Data/EL_jingke/seg_ok/*.bmp')
for one in imgs:
    aa = np.zeros((512, 512), dtype='uint8')
    cv2.imwrite(one[:-3] + 'png', aa)
    print(aa)
