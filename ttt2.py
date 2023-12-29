#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
import pdb
import numpy as np

import cv2

img = cv2.imread('images/color_cursor.png', cv2.IMREAD_UNCHANGED)

img_bin = (img[:, :, 3] != 0)

img_255 = img_bin.astype('uint8') * 255
img_255 = np.repeat(img_255[:, :, None], 3, axis=2)

final = img[:, :, 3]
img2 = np.concatenate([img_255, final[:, :, None]], axis=2)
# print(img_255.sum())
# cv2.imshow("aa", img2)
# cv2.waitKey()

cv2.imwrite('images/color_cursor2.png', img2)