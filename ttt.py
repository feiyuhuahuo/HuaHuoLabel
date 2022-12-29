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

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
from PySide6.QtGui import QCursor, QAction
from PySide6.QtCore import QTranslator, QEvent


class PP(QMainWindow):
    def __init__(self):
        super().__init__()

        loader = QUiLoader()

        loader.setLanguageChangeEnabled(True)
        print(loader.isLanguageChangeEnabled())

        self.app = QApplication.instance()

        # self.trans_window = QTranslator()
        # self.trans_window.load('test.qm')
        # self.app.installTranslator(self.trans_window)
        #
        # self.trans_main = QTranslator()
        # self.trans_main.load('ttt.qm')
        # self.app.installTranslator(self.trans_main)


        self.main_ui = loader.load('test.ui')
        self.setCentralWidget(self.main_ui)
        self.main_ui.pushButton.clicked.connect(self.trans_ui)

        self.menu = QMenu(self)
        self.action = QAction(self.tr('hello'))
        self.action.triggered.connect(self.trans_code)
        self.menu.addAction(self.action)
        self.main_ui.pushButton.customContextMenuRequested.connect(self.show_menu)

        self.show()

    def changeEvent(self, event):
        if 'LanguageChange' in event.__repr__():
            # self.action.setText(self.tr('hello'))
            print(event)

    def load_qm(self):
        self.trans_window = QTranslator()
        self.trans_window.load('test.qm')
        self.app.installTranslator(self.trans_window)

        self.trans_main = QTranslator()
        self.trans_main.load('ttt.qm')
        self.app.installTranslator(self.trans_main)

    def trans_ui(self):
        self.load_qm()

    def trans_code(self):
        if not self.main_ui.label.text():
            self.main_ui.label.setText(self.tr('pear'))

        QMessageBox.information(self, self.tr('cat'), self.tr('apple'))

    def show_menu(self):
        self.menu.exec(QCursor.pos())


if __name__ == '__main__':
    app = QApplication()
    ui = PP()
    app.exec()

# self.WorkMode in ('单分类', 'Single Cls'):
# self.WorkMode in ('多分类', 'Multi Cls'):
# self.WorkMode in ('语义分割', 'Sem Seg'):
# self.WorkMode in ('目标检测', 'Obj Det'):
# self.WorkMode in ('实例分割', 'Ins Seg'):
#
# self.WorkMode in ('单分类', 'Single Cls', '多分类', 'Multi Cls'):
# self.WorkMode in ('语义分割', 'Sem Seg', '实例分割', 'Ins Seg'):
#
# self.WorkMode in ('语义分割', 'Sem Seg', '目标检测', 'Obj Det', '实例分割', 'Ins Seg'):
# self.WorkMode in ('多分类', 'Multi Cls', '语义分割', 'Sem Seg', '目标检测', 'Obj Det', '实例分割', 'Ins Seg'):

# (self.tr('多分类'), self.tr('语义分割'), self.tr('目标检测'), self.tr('实例分割'))