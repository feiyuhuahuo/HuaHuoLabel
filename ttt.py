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

# import sys
#
# import numpy as np
# import cv2
# import glob
# from PySide6.QtCore import QSize
# from PySide6.QtGui import QImageReader, QImage
# from PIL import Image
#
# QImageReader.setAllocationLimit(256)
#
# img = QImageReader('images/bg.png')
# print(sys.getsizeof(img))
# #img.setScaledSize(QSize(1024, 1024))
# print(sys.getsizeof(img))
# print(img.allocationLimit())
# new_i = img.read()
# print(sys.getsizeof(new_i))
# print(new_i, '\n')
# print(img.error(), '\n')
# print(img.errorString(), '\n')


# import os
# imgs = glob.glob('D:\Data\硅片分选/前后崩/大图/*.bmp')
#
# for k, one in enumerate(imgs):
#     cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_GRAYSCALE)
#     # cv2_img = cv2.resize(cv2_img, (3072, 3072))
#     name = one.split(os.path.sep)[-1][:-4]
#     print(name)
#     # for i in range(3):
#     #     for j in range(3):
#     #         piece = cv2_img[i*1024:(i+1)*1024, j*1024:(j+1)*1024]
#     #         cv2.imencode('.bmp', piece)[1].tofile(f'D:\Data\硅片分选/表面崩边/{name}_{i}_{j}.bmp')
#
#     piece1 = cv2_img[:, 0: 1600]
#     piece2 = cv2_img[:, 1600:3200]
#     piece3 = cv2_img[:, 3200:4800]
#     piece4 = cv2_img[:, 4800:6400]
#     cv2.imencode('.bmp', piece1)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_1.bmp')
#     cv2.imencode('.bmp', piece2)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_2.bmp')
#     cv2.imencode('.bmp', piece3)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_3.bmp')
#     cv2.imencode('.bmp', piece4)[1].tofile(f'D:\Data\硅片分选/前后崩/piece/{name}_4.bmp')

# import cv2
#
# aa = 0
# for one in range(3):
#     img = cv2.imread(f'E:/c_sharp_deploy/result_cv2_{one}.png', cv2.IMREAD_GRAYSCALE)
#     # print(img.sum())
#     # cv2.imshow("aa", img*200)
#     # cv2.waitKey()

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout

from need.custom_signals import *


class SelectWindow(QWidget):
    # parent=None必须要实现，否则由其它界面呼起时，好像只能看，其它功能会失灵
    def __init__(self, parent=None, title='窗口', button_signal=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.ui = loader.load('label_window.ui')
        layout = QVBoxLayout()
        layout.addWidget(self.ui)
        self.setLayout(layout)
        self.button_signal = None
        self.resize(300, 800)

    def closeEvent(self, event):
        print('*****************')
        self.close()


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    app = QApplication()
    ui = SelectWindow(title='你好')

    ui.show()
    app.exec()
