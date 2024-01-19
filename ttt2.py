#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
import pdb
import numpy as np

import cv2
cv2.namedWindow("aa", cv2.WINDOW_NORMAL)
# cv2.namedWindow("bb", cv2.WINDOW_NORMAL)

imgs = glob.glob('D:\Data\SIC_D\weiguan\edge_corner_overex/1/*')
for one in imgs:
    print(one)
    img = cv2.imread(one, cv2.IMREAD_GRAYSCALE)

    blur = cv2.GaussianBlur(img, (3, 3), 0)  # 用高斯滤波处理原图像降噪
    canny = cv2.Canny(blur, 10, 40)  # 50是最小阈值,150是最大阈值

    cv2.imshow('aa',canny)
    # cv2.imshow('bb', absY)
    cv2.waitKey()



