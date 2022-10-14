#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pdb


# import cv2
# import numpy as np
# from need.utils import douglas_peuker
#
# Src = cv2.imread("mm.png")
#
#
# # 转为灰度图
# dst = cv2.cvtColor(Src, cv2.COLOR_BGR2GRAY)
# ret, thresh = cv2.threshold(dst, 0, 255, cv2.THRESH_BINARY)
# # cv2.imshow("thresh", thresh)
# # cv2.waitKey()
#
# # # 获取轮廓信息
# contours, hierarchy = cv2.findContours(thresh, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
# print(hierarchy)
# pdb.set_trace()
# contours_sq = []
# for one in contours:
#     one_sq = one.squeeze(1)
#     print(one_sq.shape)
#     result = douglas_peuker(one_sq.tolist(), threshold=2)
#     print(len(result))
#     contours_sq.append(np.array(result)[:, None, :])
#
# scr1 = Src.copy()
# scr2 = Src.copy()
# result = cv2.drawContours(scr1, contours, -1, (0, 0, 255), 1)
# result_sq = cv2.drawContours(scr2, contours_sq, -1, (0, 0, 255), 1)
# cv2.imshow("result", result)
# cv2.imshow("result_sq", result_sq)
# cv2.waitKey()
#

import numpy as np
import cv2
import glob
# from PySide6.QtGui import QImageReader, QImage
# from PIL import Image
#
# img = QImageReader('1000000139#OK#20220928101924#84.8.bmp')
# new_i = img.read()
# print(new_i, '\n')
# print(img.error(), '\n')
# print(img.errorString(), '\n')
# print('---------------------------------------')
# img = QImageReader('Image-0015.bmp')
# new_i = img.read()
# print(new_i, '\n')
# print(img.error(), '\n')
# print(img.errorString(), '\n')
#
# img1 = Image.open('1000000139#OK#20220928101924#84.8.bmp')
# print(img1.format)
#
# img2 = Image.open('Image-0015.bmp')
# print(img2.format)
import os
imgs = glob.glob('D:\Data\硅片分选/前后崩/大图/*.bmp')

for k, one in enumerate(imgs):
    cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_GRAYSCALE)
    # cv2_img = cv2.resize(cv2_img, (3072, 3072))
    name = one.split(os.path.sep)[-1][:-4]
    print(name)
    # for i in range(3):
    #     for j in range(3):
    #         piece = cv2_img[i*1024:(i+1)*1024, j*1024:(j+1)*1024]
    #         cv2.imencode('.bmp', piece)[1].tofile(f'D:\Data\硅片分选/表面崩边/{name}_{i}_{j}.bmp')

    piece1 = cv2_img[:, 0: 1600]
    piece2 = cv2_img[:, 1600:3200]
    piece3 = cv2_img[:, 3200:4800]
    piece4 = cv2_img[:, 4800:6400]
    cv2.imencode('.bmp', piece1)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_1.bmp')
    cv2.imencode('.bmp', piece2)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_2.bmp')
    cv2.imencode('.bmp', piece3)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_3.bmp')
    cv2.imencode('.bmp', piece4)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_4.bmp')
