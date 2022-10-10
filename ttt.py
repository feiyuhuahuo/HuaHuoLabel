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

from PySide6.QtGui import QImageReader, QImage
from PIL import Image

img = QImageReader('1000000139#OK#20220928101924#84.8.bmp')
new_i = img.read()
print(new_i, '\n')
print(img.error(), '\n')
print(img.errorString(), '\n')
print('---------------------------------------')
img = QImageReader('Image-0015.bmp')
new_i = img.read()
print(new_i, '\n')
print(img.error(), '\n')
print(img.errorString(), '\n')

img1 = Image.open('1000000139#OK#20220928101924#84.8.bmp')
print(img1.format)

img2 = Image.open('Image-0015.bmp')
print(img2.format)