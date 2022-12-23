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
import random

import cv2
import os
import glob
import numpy as np




# from PySide6.QtUiTools import QUiLoader
# from PySide6.QtWidgets import QMainWindow
# from PySide6.QtWidgets import QApplication, QLabel, QHBoxLayout
# from PySide6.QtGui import QCursor, QPixmap, QImage


# # noinspection PyUnresolvedReferences
# class PP(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         loader = QUiLoader()
#         self.main_ui = loader.load('test.ui')
#         self.setCentralWidget(self.main_ui)
#
#         img = cv2.imread('1111.png', cv2.IMREAD_GRAYSCALE)
#         cv2.imshow('aa', img)
#         cv2.waitKey()
#
#         height, width = img.shape
#         print('shape:', img.shape, 'dtype:', img.dtype)
#         qimg = QImage(img.astype('uint8').data, width, height, width*1, QImage.Format_Grayscale8)
#
#         self.main_ui.label.setPixmap(QPixmap(qimg))
#         self.show()
#
#
# if __name__ == '__main__':
#     app = QApplication()
#     ui = PP()
#     app.exec()

# # noinspection PyUnresolvedReferences
# class PP(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         loader = QUiLoader()
#         self.main_ui = loader.load('test.ui')
#         self.setCentralWidget(self.main_ui)
#         self.main_ui.pushButton.clicked.connect(self.add_l)
#         self.resize(500, 150)
#         self.show()
#
#     def add_l(self):
#         print(self.main_ui.scrollArea.horizontalScrollBar().maximum())
#         self.main_ui.horizontalLayout_2.addWidget(QLabel('  ***aaaaa**  '))
#         print(self.main_ui.scrollArea.horizontalScrollBar().maximum())
#         print('--------------')
#         self.main_ui.scrollArea.horizontalScrollBar().setValue(9999)
#
#
# if __name__ == '__main__':
#     app = QApplication()
#     ui = PP()
#     app.exec()

img_name='sdsfdsgdg.bmp'
print(img_name[:-4])