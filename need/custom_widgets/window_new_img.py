#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QIcon
from need.functions import get_file_cmtime
from need.custom_widgets.ui_from_file.base_img_window import Ui_MainWindow


class BaseImgWindow(QMainWindow):
    def __init__(self, parent=None, title='base_frame'):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon('images/icon.png'))

        width = self.ui.img_area.width()  # 确保img_area能以512*512的大小展示，否则影响其坐标计算等
        height = self.ui.img_area.height() + self.ui.label_xyrgb.height() + 6 + 4  # 6是layout spacing, 4是测出来的误差
        self.resize(width, height)

        self.ui.img_area.signal_xy_color2ui.signal.connect(self.img_xy_color_update)
        self.ui.img_area.signal_img_time2ui.signal.connect(self.img_time_info_update)
        self.ui.img_area.signal_img_size2ui.signal.connect(self.img_size_info_update)

    def paint_img(self, img_path_or_pix_map, img_path, re_center=True, img_info_update=True):
        self.ui.img_area.paint_img(img_path_or_pix_map, img_path, re_center, img_info_update)

    def img_size_info_update(self, wh: tuple):
        ori_w, ori_h = self.ui.img_area.ori_img_size()
        text = self.tr(f'宽: {ori_w}, 高: {ori_h}')
        scale = int(round(wh[0] / ori_w * 100))
        text += f' ({wh[0]}, {wh[1]}, {scale}%)'
        self.ui.label_size_info.setText(text)

    def img_time_info_update(self, img_path):
        c_time, m_time = get_file_cmtime(img_path)
        self.ui.label_time_info.setText(self.tr(f'创建: {c_time}, 修改: {m_time}'))

    def img_xy_color_update(self, info):
        x, y, r, g, b = info
        self.ui.label_xyrgb.setText(f'X: {x}, Y: {y} <br>'  # &nbsp; 加入空格
                                    f'<font color=red> R: {r}, </font>'
                                    f'<font color=green> G: {g}, </font>'
                                    f'<font color=blue> B: {b} </font>')
