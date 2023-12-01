#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
from typing import List, Union
from copy import deepcopy
from PySide6.QtWidgets import QInputDialog, QMessageBox, QApplication, QMenu, QListWidgetItem, QLabel, QGraphicsView, \
    QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QPushButton, QFileDialog
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QObject, QSize
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QPen, QUndoStack, QCursor, QRegion, QPolygon, QAction, \
    QImageReader, QIcon, QImage
from need.algorithms import point_in_shape
from need.utils import AnnUndo, INS_shape_type
from need.custom_signals import *
from need.custom_widgets import SelectItem, signal_select_window_close
from need.functions import get_HHL_parent

signal_del_shape = IntSignal()
signal_move2new_folder = BoolSignal()
signal_open_label_window = BoolSignal()
signal_one_collection_done = StrSignal()
signal_select_collection_ok = StrSignal()
signal_draw_selected_shape = IntSignal()
signal_set_shape_list_selected = IntSignal()
signal_shape_info_update = IntSignal()
signal_shape_type = StrSignal()


class BaseImgFrame_optimal(QLabel):
    # 基础图片展示控件，只提供基本的图片显示、拖曳、缩放功能，不提供标注功能。
    def __init__(self, parent=None, title='base_frame'):
        super().__init__(parent)
        self.painter = QPainter()
        self.painter.setRenderHint(QPainter.Antialiasing)
        self.painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setMouseTracking(True)
        self.resize(512, 512)

        self.img_reader = QImageReader()
        self.img_reader.setAllocationLimit(512)

        self.img_menu = QMenu('img_menu', self)
        self.img_menu.setFixedWidth(135)
        self.action_bilinear = QAction(self.tr('双线性插值缩放'), self)
        self.action_bilinear.triggered.connect(self.set_interpolation)
        self.action_nearest = QAction(self.tr('最近邻插值缩放'), self)
        self.action_nearest.setIcon(QPixmap('images/icon_11.png'))
        self.action_nearest.triggered.connect(self.set_interpolation)
        self.action_to_100 = QAction(self.tr('缩放至100%尺寸'), self)
        self.action_to_100.triggered.connect(self.to_100_size)
        self.action_pixel_cursor = QAction(self.tr('像素指针'), self)
        self.action_pixel_cursor.triggered.connect(self.set_pixel_cursor)
        self.action_to_file_path = QAction(self.tr('打开图片所在路径'), self)
        self.action_to_file_path.triggered.connect(self.open_file_path)
        self.img_menu.addAction(self.action_nearest)
        self.img_menu.addAction(self.action_bilinear)
        self.img_menu.addAction(self.action_to_100)
        self.img_menu.addAction(self.action_pixel_cursor)
        self.img_menu.addAction(self.action_to_file_path)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_menu)

        self.img, self.scaled_img = None, None
        self.img_path = ''
        self.img_tl = QPointF(0., 0.)  # 图片左上角在控件坐标系的坐标
        self.start_pos = None
        self.bm_start = None
        self.mouse_event_pos = None  # 记录鼠标在窗口坐标系的坐标
        self.interpolation = Qt.FastTransformation
        self.setCursor(Qt.OpenHandCursor)

        pixel_cursor = QPixmap('images/color_cursor.png').scaled(16, 16, mode=Qt.SmoothTransformation)
        self.pixel_cursor = QCursor(pixel_cursor, 0, pixel_cursor.height())

        self.LeftClick = False  # 用于图片拖曳和标注拖曳功能中，判断左键是否按下
        self.IsClosed = False

        self.signal_xy_color2ui = ListSignal()
        self.signal_img_size2ui = TupleSignal()
        self.signal_img_time2ui = StrSignal()

    def contextMenuEvent(self, event):
        self.img_menu.exec(self.mapToGlobal(event.pos()))

    def closeEvent(self, event):
        self.IsClosed = True
        self.close()

    def mouseDoubleClickEvent(self, e):  # 同时触发mousePressEvent()
        self.scaled_img = self.img.scaled(self.size(), Qt.KeepAspectRatio, self.interpolation)
        self.center_point()
        self.signal_img_size2ui.send(self.scaled_img.size().toTuple())
        self.update()

    def mouseMoveEvent(self, e):
        self.cursor_in_widget = e.position()  # 相当于self.mapFromGlobal(e.globalPosition())

        img_pixel_x, img_pixel_y, qcolor = self.widget_coor_to_img_coor(self.cursor_in_widget)
        if img_pixel_x is not None:  # 实时显示坐标，像素值
            self.signal_xy_color2ui.send([img_pixel_x, img_pixel_y, qcolor.red(), qcolor.green(), qcolor.blue()])

        self.move_pix_img()

    def mousePressEvent(self, e):
        self.set_cursor(press=True)

        if e.button() == Qt.LeftButton:
            self.LeftClick = True
            self.start_pos = e.position()
        elif e.button() == Qt.RightButton:
            self.mouse_event_pos = e.position()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.LeftClick = False

        self.set_cursor(release=True)

    def paintEvent(self, e):  # 程序调用show()之后就会调用此函数
        self.painter.begin(self)
        self.painter.drawPixmap(self.img_tl, self.scaled_img)
        self.painter.end()

    def wheelEvent(self, e):
        if self.is_bg():
            return

        scale_ratio = 0.95
        if e.angleDelta().y() < 0:  # 缩小
            pass
        elif e.angleDelta().y() > 0:  # 放大
            scale_ratio = 1 / scale_ratio

        self.scale_img(e.position(), scale_ratio)

    def center_point(self):  # 计算图片居中显示时的图片左上角坐标
        new_x = (self.size().width() - self.scaled_img.width()) / 2
        new_y = (self.size().height() - self.scaled_img.height()) / 2
        self.img_tl = QPointF(new_x, new_y)  # 图片的坐上角在控件坐标系的坐标

    def get_border_coor(self):  # 获取图片在控件坐标系的左上角、右下角坐标
        t_l_x, t_l_y = self.img_tl.x(), self.img_tl.y()  # 图片左上角在控件坐标系的坐标，可为负
        img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
        b_r_x, b_r_y = t_l_x + img_w - 1, t_l_y + img_h - 1
        return t_l_x, t_l_y, b_r_x, b_r_y

    def get_widget_to_img_ratio(self):  # 图片的一个像素点实际对于控件展示区域有多少个坐标点
        ori_w, ori_h = self.ori_img_size()

        if ori_w and ori_h:
            img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
            img_h2real_h = img_h / ori_h
            img_w2real_w = img_w / ori_w
            return img_w2real_w, img_h2real_h
        else:
            return None, None

    def is_bg(self):
        return self.img_path == 'images/bg.png'

    def move_pix_img(self):  # 拖曳图片功能
        if self.LeftClick:
            self.img_tl = self.img_tl + self.cursor_in_widget - self.start_pos
            self.start_pos = self.cursor_in_widget
        self.update()

    def open_file_path(self):
        if not self.is_bg():
            QFileDialog(self).getOpenFileName(self, dir=self.img_path)

    def ori_img_size(self) -> tuple:
        return self.img_reader.size().toTuple()

    def paint_img(self, img_path_or_pix_map, img_path='', re_center=True, img_info_update=True):
        if img_path_or_pix_map is None:  # 有时候是None，原因未知
            return
        if img_info_update:
            assert img_path, 'img_path is None.'

        self.img_path = img_path

        self.img_reader.setFileName(img_path_or_pix_map)
        img_w, img_h = self.img_reader.size().toTuple()
        area_w, area_h = self.size().toTuple()
        resize_scale = min(area_w / img_w, area_h / img_h)
        resize_w, resize_h = int(img_w * resize_scale), int(img_h * resize_scale)
        self.img_reader.setScaledSize(QSize(resize_w, resize_h))
        self.scaled_img = QPixmap(self.img_reader.read())

        self.old_img_w, self.old_img_h = self.scaled_img.size().toTuple()

        if re_center:
            self.center_point()
        else:
            pass
            # self.scaled_img = self.img.scaled(self.scaled_img.size(), Qt.KeepAspectRatio, self.interpolation)

        self.update()

        if img_info_update and not self.is_bg():
            self.signal_img_size2ui.send(self.scaled_img.size().toTuple())
            self.signal_img_time2ui.send(self.img_path)

    def scale_img(self, mouse_event_pos, scale_ratio):
        if self.is_bg():
            return

        ex, ey = mouse_event_pos.x(), mouse_event_pos.y()

        old_x, old_y = self.img_tl.x(), self.img_tl.y()
        cur_center_x, cur_center_y = old_x + self.old_img_w / 2, old_y + self.old_img_h / 2
        offset_x, offset_y = (ex - cur_center_x) / self.old_img_w, (ey - cur_center_y) / self.old_img_h

        if scale_ratio == 1:
            # self.scaled_img = self.img
            pass
        else:
            # self.scaled_img = self.img.scaled(int(old_img_w * scale_ratio), int(old_img_h * scale_ratio),
            #                                   Qt.KeepAspectRatio, self.interpolation)
            # new_img_w, new_img_h = self.scaled_img.width(), self.scaled_img.height()

            # todo: 为显示超大图片优化的读图逻辑，1.缩放不跟鼠标；2.坐标计算还需要检查；3.可能存在float到int的精度损失；
            #  4.QimageReader还无法指定缩放算法，导致无法查看到像素点
            new_img_w, new_img_h = int(self.old_img_w * scale_ratio), int(self.old_img_h * scale_ratio)
            new_img_x = (1 / 2 + offset_x) * (self.old_img_w - new_img_w) + old_x
            new_img_y = (1 / 2 + offset_y) * (self.old_img_h - new_img_h) + old_y

            widget_w, widget_h = self.size().toTuple()
            x1_in_img, y1_in_img = -new_img_x, -new_img_y
            x2_in_img, y2_in_img = x1_in_img + widget_w, y1_in_img + widget_h
            rect_x1, rect_y1 = max(0, x1_in_img), max(0, y1_in_img)
            rect_w, rect_h = min(x2_in_img - x1_in_img, new_img_w), min(y2_in_img - y1_in_img, new_img_h)

            ori_img_w, ori_img_h = self.ori_img_size()

            rr_x1, rr_y1 = int((rect_x1 / new_img_w) * ori_img_w), int((rect_y1 / new_img_h) * ori_img_h)
            rr_w, rr_h = int((rect_w / new_img_w) * ori_img_w), int((rect_h / new_img_h) * ori_img_h)

            self.img_reader.setFileName(self.img_path)
            self.img_reader.setClipRect(QRect(rr_x1, rr_y1, rr_w, rr_h))
            self.img_reader.setScaledSize(QSize(min(widget_w, new_img_w), min(widget_h, new_img_h)))
            self.scaled_img = QPixmap(self.img_reader.read())

            self.img_tl = QPointF(max(0, new_img_x), max(0, new_img_y))
            self.old_img_w, self.old_img_h = new_img_w, new_img_h

            self.signal_img_size2ui.send(self.scaled_img.size().toTuple())
            self.update()

    def set_cursor(self, press=False, moving=False, release=False):
        if self.is_bg():
            return

        if 'null' in str(self.action_pixel_cursor.icon()):
            self.setCursor(Qt.OpenHandCursor)

            if press:
                self.setCursor(Qt.ClosedHandCursor)
            if release:
                self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(self.pixel_cursor)

    def set_interpolation(self):
        if self.sender() is self.action_nearest:
            self.action_nearest.setIcon(QPixmap('images/icon_11.png'))
            self.action_bilinear.setIcon(QPixmap(''))
            self.interpolation = Qt.FastTransformation
        elif self.sender() is self.action_bilinear:
            self.action_bilinear.setIcon(QPixmap('images/icon_11.png'))
            self.action_nearest.setIcon(QPixmap(''))
            self.interpolation = Qt.SmoothTransformation

    def set_pixel_cursor(self):
        if not self.is_bg():
            if 'null' in str(self.action_pixel_cursor.icon()):
                self.action_pixel_cursor.setIcon(QPixmap('images/icon_11.png'))
                self.set_cursor()
            else:
                self.action_pixel_cursor.setIcon(QIcon())
                self.set_cursor()

    def shape_scale_convert(self, points, old_img_tl, scale_factor):
        new_points = []
        for one_p in points:
            x0_in_img, y0_in_img = one_p.x() - old_img_tl.x(), one_p.y() - old_img_tl.y()
            new_p = QPointF(x0_in_img * scale_factor[0], y0_in_img * scale_factor[1])
            new_p = new_p + self.img_tl
            new_points.append(new_p)

        return new_points

    def show_menu(self):  # 在鼠标位置显示菜单
        self.img_menu.exec(QCursor.pos())

    def to_100_size(self):
        self.scale_img(self.mouse_event_pos, 1)

    def widget_coor_to_img_coor(self, rel_pos: QPointF):
        # 获取鼠标位置在图片坐标系内的坐标, 输入为控件坐标系的坐标
        rel_x, rel_y = rel_pos.x(), rel_pos.y()
        img_w2real_w, img_h2real_h = self.get_widget_to_img_ratio()

        if img_w2real_w is not None:
            b_left, b_up, b_right, b_down = self.get_border_coor()
            if b_left <= rel_x <= b_right and b_up <= rel_y <= b_down:
                img_x, img_y = rel_x - b_left, rel_y - b_up
                qcolor = QColor.fromRgb(self.scaled_img.toImage().pixel(int(img_x), int(img_y)))
                return int(img_x / img_w2real_w), int(img_y / img_h2real_h), qcolor
            else:
                return None, None, None
        else:
            return None, None, None

    def img_coor_to_widget_coor(self, point: Union[List, List[List]]):
        img_w2real_w, img_h2real_h = self.get_widget_to_img_ratio()
        b_left, b_up, b_right, b_down = self.get_border_coor()

        if type(point[0]) == int:
            point = QPointF(point[0] * img_w2real_w, point[1] * img_h2real_h) + self.img_tl
            if b_left <= point.x() <= b_right and b_up <= point.y() <= b_down:
                return point
            else:
                return None
        elif type(point[0]) == list:
            widget_points = []
            for one_p in point:
                widget_points.append(QPointF(one_p[0] * img_w2real_w, one_p[1] * img_h2real_h) + self.img_tl)
            return widget_points
        else:
            return None
