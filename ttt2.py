#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
import pdb
import numpy as np

import cv2

cv2.namedWindow('aa', cv2.WINDOW_NORMAL)
imgs = glob.glob('D:\Data\weiguan\guobao\SourceImg/*')

for one in imgs:
    if 'MappingLite' in one:
        continue
    if 'bin' in one:
        continue
    if 'contour' in one:
        continue
    if 'part' in one:
        continue

    img = cv2.imread(one, cv2.IMREAD_GRAYSCALE)
    if (img > 150).sum() > 6400:
        img_name = one.split('\\')[-1]
        img_bin = cv2.threshold(img, 10, 255, cv2.THRESH_BINARY)[1]
        contours = cv2.findContours(img_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        img_contour = cv2.drawContours(cv2.cvtColor(img_bin, cv2.COLOR_GRAY2BGR), contours, -1, (0, 0, 255), 1)
        # cv2.imwrite(f'D:\Data\weiguan\guobao\SourceImg/{img_name}_contour_external.jpg', img_contour)

        for i, one_contour in enumerate(contours):
            area = cv2.contourArea(one_contour)
            if area > 10000:
                print(f'D:\Data\weiguan\guobao\SourceImg/{img_name}_part_{i}.jpg')
                mask = np.zeros(img.shape, dtype='uint8')
                cv2.fillConvexPoly(mask, one_contour, 255)
                part = cv2.bitwise_and(img, mask)

                pixel_sum = cv2.sumElems(part)[0]
                num = cv2.countNonZero(part)

                print(pixel_sum, num, pixel_sum/num)

        print('--------------------------------------------')
