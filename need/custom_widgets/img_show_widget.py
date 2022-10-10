#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
import cv2
import numpy as np
from copy import deepcopy
import pdb
from PySide6.QtWidgets import QInputDialog, QFrame, QMessageBox, QApplication, QMenu, QListWidgetItem
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QSize
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QPen, QUndoStack, QCursor, QRegion, QPolygon, QAction, \
    QImageReader
from need.utils import point_in_shape, AnnUndo
from need.custom_signals import *
from need.custom_widgets import SelectWindow

signal_del_shape = IntSignal()
shape_type = StrSignal()
signal_move2new_folder = BoolSignal()
signal_open_label_window = BoolSignal()
signal_one_collection_done = StrSignal()
select_ui_ok_from_seg_collection = StrSignal()
selected_label_item = IntSignal()
signal_selected_shape = IntSignal()
signal_xy_color2ui = ListSignal()


class BaseImgFrame(QFrame):
    # 基础图片展示控件，只提供基本的图片显示、拖曳、缩放功能，不提供标注功能。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.painter = QPainter()
        self.painter.setRenderHint(QPainter.Antialiasing)
        self.painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setMouseTracking(True)
        self.resize(512, 512)
        # todo: bug, 不知道为什么基类的menu右键的时候不显示
        self.menu = QMenu(self)
        self.menu.addAction('最近邻插值缩放').triggered.connect(lambda: self.set_interpolation(Qt.FastTransformation))
        self.menu.addAction('双线性插值缩放').triggered.connect(lambda: self.set_interpolation(Qt.SmoothTransformation))
        self.customContextMenuRequested.connect(lambda: self.show_menu(self.menu))

        self.img, self.scaled_img = None, None
        self.img_tl_point = QPointF(0., 0.)  # 图片左上角在控件坐标系的坐标
        self.start_pos = None
        self.LeftClick = False  # 用于实现图片拖曳和标注拖曳功能
        self.interpolation = Qt.FastTransformation

        self.IsClosed = False

    def closeEvent(self, event):
        self.IsClosed = True
        self.close()

    def mouseDoubleClickEvent(self, e):  # 同时触发mousePressEvent()
        action_img = self.img
        self.scaled_img = action_img.scaled(self.size(), Qt.KeepAspectRatio, self.interpolation)
        self.center_point()
        self.update()

    def mouseMoveEvent(self, e):
        self.cursor_in_widget = e.position()  # 相当于self.mapFromGlobal(e.globalPosition())

        img_pixel_x, img_pixel_y, qcolor = self.widget_coor_to_img_coor(self.cursor_in_widget)
        if img_pixel_x is not None:  # 实时显示坐标，像素值
            signal_xy_color2ui.send([img_pixel_x, img_pixel_y, qcolor.red(), qcolor.green(), qcolor.blue()])

        self.move_pix_img()

    def mousePressEvent(self, e):
        self.setCursor(Qt.ClosedHandCursor)

        if e.button() == Qt.LeftButton:
            self.LeftClick = True
            self.start_pos = e.position()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.LeftClick = False

        self.setCursor(Qt.OpenHandCursor)

    def paintEvent(self, e):  # 程序调用show()之后就会调用此函数
        self.painter.begin(self)
        self.painter.drawPixmap(self.img_tl_point, self.scaled_img)
        self.painter.end()

    def wheelEvent(self, e):
        ex, ey = e.position().x(), e.position().y()
        img_w, img_h = self.scaled_img.width(), self.scaled_img.height()
        scale_ratio = 0.95
        old_x, old_y = self.img_tl_point.x(), self.img_tl_point.y()
        cur_center_x, cur_center_y = old_x + img_w / 2, old_y + img_h / 2
        offset_x, offset_y = (ex - cur_center_x) / img_w, (ey - cur_center_y) / img_h

        action_img = self.img
        if e.angleDelta().y() < 0:  # 缩小
            self.scaled_img = action_img.scaled(int(img_w * scale_ratio), int(img_h * scale_ratio),
                                                Qt.KeepAspectRatio, self.interpolation)
        elif e.angleDelta().y() > 0:  # 放大
            self.scaled_img = action_img.scaled(int(img_w * (1 / scale_ratio)), int(img_h * (1 / scale_ratio)),
                                                Qt.KeepAspectRatio, self.interpolation)

        new_img_w, new_img_h = self.scaled_img.width(), self.scaled_img.height()

        new_img_x = (1 / 2 + offset_x) * (img_w - new_img_w) + old_x
        new_img_y = (1 / 2 + offset_y) * (img_h - new_img_h) + old_y
        self.img_tl_point = QPointF(new_img_x, new_img_y)

        self.update()

    def center_point(self):  # 图片初始化居中显示
        new_x = (self.size().width() - self.scaled_img.width()) / 2
        new_y = (self.size().height() - self.scaled_img.height()) / 2
        self.img_tl_point = QPointF(new_x, new_y)  # 图片的坐上角在控件坐标系的坐标

    def get_border_coor(self):  # 获取图片在控件坐标系的左上角、右下角坐标
        t_l_x, t_l_y = self.img_tl_point.x(), self.img_tl_point.y()  # 图片左上角在控件坐标系的坐标，可为负
        img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
        b_r_x, b_r_y = t_l_x + img_w - 1, t_l_y + img_h - 1
        return t_l_x, t_l_y, b_r_x, b_r_y

    def move_pix_img(self):  # 拖曳图片功能
        if self.LeftClick:
            self.img_tl_point = self.img_tl_point + self.cursor_in_widget - self.start_pos
            self.start_pos = self.cursor_in_widget
        self.update()

    def paint_img(self, img_path_or_pix_map, re_center=True):
        if img_path_or_pix_map is None:  # 有时候是None，原因未知
            return

        self.img = QPixmap(img_path_or_pix_map)  # self.img始终保持为原图，

        if self.img.isNull():  # todo 如果图片太大，QPixmap或QImage会打不开，用QImageReader
            img = QImageReader(img_path_or_pix_map)
            img.setScaledSize(QSize(1024, 1024))
            print(img.canRead())
            print(img.size())
            kkk = img.read()
            print(kkk)

        if re_center:
            self.scaled_img = self.img.scaled(self.size(), Qt.KeepAspectRatio, self.interpolation)
            self.center_point()
        else:
            self.scaled_img = self.img.scaled(self.scaled_img.size(), Qt.KeepAspectRatio, self.interpolation)
        self.update()

    def set_interpolation(self, mode):
        self.interpolation = mode

    def shape_scale_convert(self, points, old_img_tl, scale_factor):
        new_points = []
        for one_p in points:
            x0_in_img, y0_in_img = one_p.x() - old_img_tl.x(), one_p.y() - old_img_tl.y()
            new_p = QPointF(x0_in_img * scale_factor[0], y0_in_img * scale_factor[1])
            new_p = new_p + self.img_tl_point
            new_points.append(new_p)

        return new_points

    def show_menu(self, ob):  # 在鼠标位置显示菜单
        ob.exec(QCursor.pos())

    def widget_coor_to_img_coor(self, rel_pos, border=None):  # 获取鼠标位置在图片坐标系内的坐标, 输入为控件坐标系的坐标
        rel_x, rel_y = rel_pos.x(), rel_pos.y()
        ori_w, ori_h = self.img.size().width(), self.img.size().height()

        if ori_h:
            img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
            img_pixel_real_pixel = img_h / ori_h  # 图片的一个像素点实际对于控件展示的图片有多少个像素点

            b_left, b_up, b_right, b_down = border if border else self.get_border_coor()
            if b_left <= rel_x <= b_right and b_up <= rel_y <= b_down:
                img_x, img_y = rel_x - b_left, rel_y - b_up
                qimg = self.scaled_img.toImage()
                qcolor = QColor.fromRgb(qimg.pixel(int(img_x), int(img_y)))
                return int(img_x / img_pixel_real_pixel), int(img_y / img_pixel_real_pixel), qcolor
            else:
                return None, None, None
        else:
            return None, None, None


class ImgShow(BaseImgFrame):
    def __init__(self, parent=None):  # parent=None 必须要实现
        super().__init__(parent)
        self.scaled_img_painted = None
        self.collection_ui = SelectWindow(parent=self, title='收藏的标注', button_signal=select_ui_ok_from_seg_collection)
        self.collected_shapes = {}

        self.ann_point_last = QPoint(0, 0)
        self.ann_point_cur = QPoint(0, 0)
        self.img_tl_point = QPointF(0., 0.)  # 图片左上角在控件坐标系的坐标

        self.seg_pen_size = 2
        self.seg_pen_color = QColor('red')
        self.ann_pen_size = 4
        self.ann_pen_color = QColor('red')
        self.ann_font_size = 20
        self.ann_font_color = QColor('white')

        self.all_polygons = []
        self.widget_points = []
        self.img_points = []
        self.widget_points_huan = []
        self.img_points_huan = []

        self.shape_type = '多边形'
        self.cursor_in_widget = QPointF(0., 0.)  # 鼠标在控件坐标系的实时坐标
        self.polygon_editing_i = None  # 正在编辑的标注的索引，即标注高亮时对应的索引
        self.scale_factor = (0., 0.)  # 图片伸缩因子
        self.offset = QPointF(0., 0.)  # 图片移动偏移量
        self.corner_index = None  # 标注角点的索引
        self.start_pos = None  # 左键按下时的控件坐标系坐标

        self.interpolation = Qt.FastTransformation

        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(30)
        undo_action = self.undo_stack.createUndoAction(self, "Undo")
        self.addAction(undo_action)

        pencil_pixmap = QPixmap('images/pencil.png')
        pencil_pixmap = pencil_pixmap.scaled(40, 40)
        self.pencil_cursor = QCursor(pencil_pixmap, 3, 3)

        self.ClsMode = True
        self.MClsMode = False
        self.SegMode = False
        self.SegEditMode = False
        self.AnnMode = False

        self.LeftClick = False  # 用于实现图片拖曳和标注拖曳功能
        self.ShapeDone = False  # 用于SegMode标识画完一个多边形
        # 如果触发了一次 '内环越界'，就置为True，在下次mouseReleaseEvent再置为False，确保不会不停的触发'内环越界'
        self.OutInConflict = False

        self.FlagDrawCollection = False
        selected_label_item.signal.connect(self.draw_selected_shape)
        shape_type.signal.connect(self.change_shape_type)
        select_ui_ok_from_seg_collection.signal.connect(self.collection_ui_ok)

        self.add_poly_to_collection = QAction('收藏标注', self)
        self.add_poly_to_collection.triggered.connect(lambda: self.collection_ui_show(False))
        self.add_poly_to_collection.setDisabled(True)
        self.menu.addAction(self.add_poly_to_collection)

        self.draw_collection_shape = QAction('绘制收藏的标注', self)
        self.draw_collection_shape.triggered.connect(lambda: self.collection_ui_show(True))
        self.draw_collection_shape.setDisabled(True)
        self.menu.addAction(self.draw_collection_shape)

        self.menu.addAction('移动至新文件夹').triggered.connect(self.move_to_new_folder)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.del_polygons()
        elif event.key() == Qt.Key_A:
            self.move_polygons(key_left=True)
        elif event.key() == Qt.Key_D:
            self.move_polygons(key_right=True)
        elif event.key() == Qt.Key_W:
            self.move_polygons(key_up=True)
        elif event.key() == Qt.Key_S:
            self.move_polygons(key_down=True)

    def mouseDoubleClickEvent(self, e):  # 同时触发 mousePressEvent()
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if self.AnnMode:
                input_dlg = QInputDialog()
                input_dlg.resize(400, 100)
                input_dlg.setLabelText('注释')
                is_ok = input_dlg.exec()

                self.painter.begin(self.scaled_img)
                self.painter.setPen(self.ann_font_color)
                self.painter.setFont(QFont('Decorative', self.ann_font_size))
                if is_ok:
                    pos = (e.position() - self.img_tl_point).toPoint()
                    self.painter.drawText(pos, input_dlg.textValue())
                self.painter.end()
                self.update()
                self.scaled_img_painted = self.scaled_img.copy()  # 保存一个绘图的副本用于伸缩功能
        else:
            if self.AnnMode and self.scaled_img_painted is not None:
                action_img = self.scaled_img_painted
            else:
                action_img = self.img

            old_img_tl = self.img_tl_point
            old_img_w, old_img_h = self.scaled_img.width(), self.scaled_img.height()
            self.scaled_img = action_img.scaled(self.size(), Qt.KeepAspectRatio, self.interpolation)

            scale_factor = (self.scaled_img.width() / old_img_w, self.scaled_img.height() / old_img_h)
            self.center_point()

            self.shape_scale_move(old_img_tl, scale_factor)
            self.update()

    def mouseMoveEvent(self, e):
        self.cursor_in_widget = e.position()  # 相当于self.mapFromGlobal(e.globalPosition())

        img_pixel_x, img_pixel_y, qcolor = self.widget_coor_to_img_coor(self.cursor_in_widget)
        if img_pixel_x is not None:  # 实时显示坐标，像素值
            signal_xy_color2ui.send([img_pixel_x, img_pixel_y, qcolor.red(), qcolor.green(), qcolor.blue()])

        if self.SegMode and QApplication.keyboardModifiers() == Qt.ControlModifier:  # 画标注功能
            self.update()
        elif self.SegMode and self.SegEditMode:
            # 标注角点拖动功能
            if self.corner_index is not None and self.LeftClick:
                offset = self.cursor_in_widget - self.start_pos
                if len(self.corner_index) == 2:
                    i, j = self.corner_index
                elif len(self.corner_index) == 3:
                    i, j, k = self.corner_index

                b_left, b_up, b_right, b_down = self.get_border_coor()
                border = (b_left, b_up, b_right, b_down)
                polygon = self.all_polygons[i]

                # 处理widget_points
                if polygon['shape_type'] == '环形':
                    new_x, new_y = (polygon['widget_points'][j][k] + offset).toTuple()
                    new_x, new_y = min(max(new_x, b_left), b_right), min(max(new_y, b_up), b_down)

                    if not self.OutInConflict:
                        out_c = [aa.toTuple() for aa in polygon['widget_points'][0]]
                        if j == 0:
                            in_c = polygon['widget_points'][1]
                            for one in in_c:
                                if point_in_shape(one.toTuple(), out_c, '多边形') is None:
                                    self.LeftClick = False
                                    self.OutInConflict = True
                                    QMessageBox.warning(self, '内环越界', '内环不完全在外环内部。')
                                    return
                        if j == 1:
                            if point_in_shape((new_x, new_y), out_c, '多边形') is None:
                                self.LeftClick = False
                                self.OutInConflict = True
                                QMessageBox.warning(self, '内环越界', '内环不完全在外环内部。')
                                return

                    polygon['widget_points'][j][k] = QPointF(new_x, new_y)
                else:
                    new_x, new_y = (polygon['widget_points'][j] + offset).toTuple()
                    new_x, new_y = min(max(new_x, b_left), b_right), min(max(new_y, b_up), b_down)
                    polygon['widget_points'][j] = QPointF(new_x, new_y)

                # 处理对应的img_points
                if polygon['shape_type'] == '多边形':
                    x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][j], border=border)
                    if x is not None:
                        polygon['img_points'][j] = (x, y)
                elif polygon['shape_type'] in ('矩形', '椭圆形'):
                    if j == 0:
                        x1, y1 = polygon['widget_points'][j].toTuple()
                        x2, y2 = polygon['widget_points'][1].toTuple()
                    elif j == 1:
                        x2, y2 = polygon['widget_points'][j].toTuple()
                        x1, y1 = polygon['widget_points'][0].toTuple()

                    polygon['widget_points'][0] = QPointF(x1, y1)
                    polygon['widget_points'][1] = QPointF(x2, y2)

                    for k in range(2):
                        x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][k], border=border)
                        if x is not None:
                            polygon['img_points'][k] = (x, y)
                elif polygon['shape_type'] == '环形':
                    x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][j][k], border=border)
                    if x is not None:
                        polygon['img_points'][j][k] = (x, y)

                self.start_pos = self.cursor_in_widget
                self.update()
            # 标注移动功能
            else:
                polygon = self.get_editing_polygon()
                if polygon is not None:
                    self.move_polygons()
                else:
                    self.polygon_editing_i = None
                    self.move_pix_img()

        elif self.AnnMode and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.ann_point_cur = self.cursor_in_widget - self.img_tl_point  # 绘图的坐标系应为图片坐标系
            self.painter.begin(self.scaled_img)
            self.painter.setPen(QPen(self.ann_pen_color, self.ann_pen_size))
            self.painter.drawLine(self.ann_point_last, self.ann_point_cur)
            self.painter.end()
            self.update()
            self.ann_point_last = self.ann_point_cur
            self.scaled_img_painted = self.scaled_img.copy()  # 保存一个绘图的副本
        else:
            self.move_pix_img()

    def mousePressEvent(self, e):
        if not self.SegMode:
            self.setCursor(Qt.ClosedHandCursor)

        if self.SegMode and QApplication.keyboardModifiers() == Qt.ControlModifier:
            if self.ShapeDone:
                if self.shape_type == '环形':
                    self.widget_points_huan.append(self.widget_points.copy())
                    self.img_points_huan.append(self.img_points.copy())
                    if len(self.widget_points_huan) < 2:
                        self.clear_widget_img_points()
                        self.update()
                    else:
                        out_c = [aa.toTuple() for aa in self.widget_points_huan[0]]
                        for one in self.widget_points_huan[1]:
                            if point_in_shape(one.toTuple(), out_c, '多边形') is None:
                                QMessageBox.warning(self, '内环越界', '内环不完全在外环内部。')
                                self.widget_points_huan.pop(1)
                                return

                        signal_open_label_window.send(True)
                else:
                    signal_open_label_window.send(True)
            else:
                self.cursor_in_widget = e.position()
                self.add_widget_img_pair(self.cursor_in_widget)
                self.update()

        elif self.AnnMode and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.setCursor(self.pencil_cursor)
            self.ann_point_cur = e.position() - self.img_tl_point
            self.ann_point_last = self.ann_point_cur

            command = AnnUndo(self, self.scaled_img.copy())
            self.undo_stack.push(command)  # 添加command用于撤销功能
        else:
            if e.button() == Qt.LeftButton:
                self.LeftClick = True
                self.start_pos = e.position()

    def mouseReleaseEvent(self, e):
        if self.OutInConflict:
            self.OutInConflict = False

        if e.button() == Qt.LeftButton:
            self.LeftClick = False

        if not self.SegMode and QApplication.keyboardModifiers() != Qt.ControlModifier:
            self.setCursor(Qt.OpenHandCursor)

        if QApplication.keyboardModifiers() == Qt.ControlModifier and self.SegMode:
            if self.shape_type in ('矩形', '椭圆形'):
                point_br = e.position()
                b_left, b_up, b_right, b_down = self.get_border_coor()

                if b_left <= point_br.x() <= b_right and b_up <= point_br.y() <= b_down:
                    if len(self.widget_points):
                        self.add_widget_img_pair(point_br)
                        signal_open_label_window.send(True)
                else:
                    self.clear_widget_img_points()

    def paintEvent(self, e):  # 程序调用show()之后就会调用此函数
        self.painter.begin(self)
        self.painter.drawPixmap(self.img_tl_point, self.scaled_img)

        if self.SegMode:
            self.ShapeDone = False
            self.draw_completed_polygons()

            if self.SegEditMode:
                self.cursor_close_to_corner()
                self.draw_editing_polygon()

            if QApplication.keyboardModifiers() == Qt.ControlModifier:
                if len(self.widget_points):
                    self.painter.setPen(QPen(self.seg_pen_color, self.seg_pen_size))
                    if self.shape_type in ('矩形', '椭圆形'):
                        if len(self.widget_points) in (0, 3):  # 一些误操作导致长度错误，直接清空重画
                            self.clear_widget_img_points()
                        else:
                            if len(self.widget_points) == 2:
                                x1, y1 = self.widget_points[0].toTuple()
                                x2, y2 = self.widget_points[1].toTuple()
                            elif len(self.widget_points) == 1:
                                x1, y1 = self.widget_points[0].toTuple()
                                x2, y2 = self.cursor_in_widget.toTuple()

                            if self.shape_type == '矩形':
                                self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                            elif self.shape_type == '椭圆形':
                                self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))

                    elif self.shape_type in ('多边形', '环形'):
                        if len(self.widget_points) >= 2:  # 画已完成的完整线段
                            for i in range(len(self.widget_points) - 1):
                                self.painter.drawLine(self.widget_points[i], self.widget_points[i + 1])
                        if len(self.widget_points):  # 画最后一个点到鼠标的线段
                            self.painter.drawLine(self.widget_points[-1], self.cursor_in_widget)

                        if len(self.widget_points) >= 3:  # 至少3个点才能绘制出polygon
                            # 判定是否到了第一个点
                            result = self.close_to_corner(self.widget_points[0])
                            if result:
                                self.ShapeDone = True

        self.painter.end()

    def wheelEvent(self, e):
        if self.polygon_editing_i is None:
            ex, ey = e.position().x(), e.position().y()
            img_w, img_h = self.scaled_img.width(), self.scaled_img.height()
            scale_ratio = 0.95
            old_x, old_y = self.img_tl_point.x(), self.img_tl_point.y()
            cur_center_x, cur_center_y = old_x + img_w / 2, old_y + img_h / 2
            offset_x, offset_y = (ex - cur_center_x) / img_w, (ey - cur_center_y) / img_h

            if self.AnnMode and self.scaled_img_painted is not None:
                action_img = self.scaled_img_painted
            else:
                action_img = self.img

            if e.angleDelta().y() < 0:  # 缩小
                self.scaled_img = action_img.scaled(int(img_w * scale_ratio), int(img_h * scale_ratio),
                                                    Qt.KeepAspectRatio, self.interpolation)
            elif e.angleDelta().y() > 0:  # 放大
                self.scaled_img = action_img.scaled(int(img_w * (1 / scale_ratio)), int(img_h * (1 / scale_ratio)),
                                                    Qt.KeepAspectRatio, self.interpolation)

            new_img_w, new_img_h = self.scaled_img.width(), self.scaled_img.height()

            new_img_x = (1 / 2 + offset_x) * (img_w - new_img_w) + old_x
            new_img_y = (1 / 2 + offset_y) * (img_h - new_img_h) + old_y
            self.img_tl_point = QPointF(new_img_x, new_img_y)

            if self.SegMode:  # 已标注图形的伸缩
                scale_factor = (new_img_w / img_w, new_img_h / img_h)
                self.shape_scale_move(QPointF(old_x, old_y), scale_factor)

        self.update()

    def add_widget_img_pair(self, qpointf):
        img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(qpointf)
        if img_pixel_x is not None:
            self.widget_points.append(qpointf)
            self.img_points.append([img_pixel_x, img_pixel_y])

    def collection_ui_ok(self, text):
        def compute_new_points(points, add_offset=QPointF(0, 0)):
            offset = self.cursor_in_widget - points[0]
            widget_points = [one + offset + add_offset for one in points]

            widget_points_2 = []
            b_left, b_up, b_right, b_down = self.get_border_coor()
            for one in widget_points:
                in_border_x = min(max(b_left, one.x()), b_right)
                in_border_y = min(max(b_up, one.y()), b_down)
                widget_points_2.append(QPointF(in_border_x, in_border_y))

            img_points = [list(self.widget_coor_to_img_coor(one)[:2]) for one in widget_points_2]
            return widget_points_2, img_points

        if self.FlagDrawCollection:  # 画收藏的标注
            if text not in self.collected_shapes.keys():
                return

            polygon = self.collected_shapes[text].copy()
            self.shape_type = polygon['shape_type']

            if self.shape_type == '环形':
                self.widget_points_huan, self.img_points_huan = [], []
                widget_points_out, img_points_out = compute_new_points(polygon['widget_points'][0])
                self.widget_points_huan.append(widget_points_out)
                self.img_points_huan.append(img_points_out)

                add_offset = polygon['widget_points'][1][0] - polygon['widget_points'][0][0]
                widget_points_in, img_points_in = compute_new_points(polygon['widget_points'][1], add_offset=add_offset)
                self.widget_points_huan.append(widget_points_in)
                self.img_points_huan.append(widget_points_in)
            else:
                self.widget_points, self.img_points = compute_new_points(polygon['widget_points'])

            signal_one_collection_done.send(polygon['category'])
            self.FlagDrawCollection = False
        else:  # 收藏标注
            if text in self.collected_shapes.keys():
                QMessageBox.warning(self, '名称重复', f'"{text}"已存在。')
            else:
                self.collected_shapes[text] = self.all_polygons[self.polygon_editing_i]
                self.collection_ui.ui.listWidget.addItem(QListWidgetItem(text))
                self.collection_ui.ui.lineEdit.setText('')

        self.collection_ui.ui.close()

    def collection_ui_show(self, draw):
        if draw:
            self.FlagDrawCollection = True

        self.collection_ui.ui.show()

    def compute_shape_attr(self):
        img_size = self.img.size().toTuple()
        zero_img = np.zeros(img_size, dtype='uint8')

        if self.shape_type == '环形':
            contours = [np.array(self.img_points_huan[0]), np.array(self.img_points_huan[1])]
            cv2.drawContours(zero_img, contours, -1, 1, -1)
        else:
            cv2.drawContours(zero_img, [np.array(self.img_points)], -1, 1, -1)

        area = zero_img.sum()
        # todo:  qpixmap 转 array
        defect_img = 1

        print(img_size)

    def cursor_close_to_corner(self):
        self.corner_index = None
        for i, polygon in enumerate(self.all_polygons):
            if polygon['shape_type'] == '环形':
                for j, huan in enumerate(polygon['widget_points']):
                    for k, point in enumerate(huan):
                        if self.close_to_corner(point):
                            self.corner_index = (i, j, k)
                            return
            else:
                for j, point in enumerate(polygon['widget_points']):
                    if polygon['shape_type'] == '椭圆形':
                        p_i = self.close_to_corner(polygon['widget_points'])
                        if type(p_i) == int:
                            self.corner_index = (i, p_i)
                            return
                    else:
                        if self.close_to_corner(point):
                            self.corner_index = (i, j)
                            return

    def change_pen(self, seg_pen_size=None, seg_pen_color=None, ann_pen_size=None, ann_pen_color=None):
        if seg_pen_size is not None:
            self.seg_pen_size = seg_pen_size
        if seg_pen_color is not None:
            self.seg_pen_color = seg_pen_color
        if ann_pen_size is not None:
            self.ann_pen_size = ann_pen_size
        if ann_pen_color is not None:
            self.ann_pen_color = ann_pen_color

    def change_font(self, ann_font_size=None, ann_font_color=None):
        if ann_font_size is not None:
            self.ann_font_size = ann_font_size
        if ann_font_color is not None:
            self.ann_font_color = ann_font_color

    def change_shape_type(self, shape_type):
        self.shape_type = shape_type
        self.clear_widget_img_points()

    def clear_scaled_img(self):
        command = AnnUndo(self, self.scaled_img.copy())
        self.undo_stack.push(command)

        self.scaled_img = self.img.scaled(self.scaled_img.size(), Qt.KeepAspectRatio, self.interpolation)
        self.update()
        self.scaled_img_painted = self.scaled_img.copy()

    def clear_all_polygons(self):
        self.all_polygons = []
        self.clear_widget_img_points()
        self.clear_widget_img_points_huan()

    def clear_widget_img_points(self):
        self.widget_points = []
        self.img_points = []

    def clear_widget_img_points_huan(self):
        self.widget_points_huan = []
        self.img_points_huan = []

    def close_to_corner(self, points, radius=3):
        self.painter.setPen(Qt.NoPen)
        self.painter.setBrush(QColor('lightgreen'))

        if type(points) == QPointF:
            x, y = points.toTuple()
            if (x - 3 < self.cursor_in_widget.x() < x + 3) and (y - 3 < self.cursor_in_widget.y() < y + 3):
                self.painter.drawEllipse(x - 2 * radius, y - 2 * radius, 12, 12)
                return True
        elif type(points) == list and len(points) == 2:
            x1, y1 = points[0].toTuple()
            x2, y2 = points[1].toTuple()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            cursor = self.cursor_in_widget.toTuple()
            if point_in_shape(cursor, [(x1, y1), (x2, y2)], shape_type='椭圆形') is None:
                if x1 <= cursor[0] <= cx and y1 <= cursor[1] <= cy:
                    self.painter.drawEllipse(x1 - 2 * radius, y1 - 2 * radius, 12, 12)
                    return 0
                elif cx <= cursor[0] <= x2 and cy <= cursor[1] <= y2:
                    self.painter.drawEllipse(x2 - 2 * radius, y2 - 2 * radius, 12, 12)
                    return 1
        else:
            return False
        return False

    def del_polygons(self):
        if self.SegMode and self.SegEditMode and self.polygon_editing_i is not None:
            self.all_polygons.pop(self.polygon_editing_i)
            signal_del_shape.send(self.polygon_editing_i)
            self.polygon_editing_i = None
        self.update()

    def draw_editing_polygon(self):  # 画正在编辑中的polygon
        if self.polygon_editing_i is not None:
            self.painter.setPen(Qt.NoPen)
            self.painter.setBrush(QColor(0, 255, 0, 150))
            editing_polygon = self.all_polygons[self.polygon_editing_i]

            if editing_polygon['shape_type'] in ('矩形', '椭圆形'):
                x1, y1 = editing_polygon['widget_points'][0].toTuple()
                x2, y2 = editing_polygon['widget_points'][1].toTuple()

                if editing_polygon['shape_type'] == '矩形':
                    self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                elif editing_polygon['shape_type'] == '椭圆形':
                    self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
            elif editing_polygon['shape_type'] == '多边形':
                self.painter.drawPolygon(editing_polygon['widget_points'])
            elif editing_polygon['shape_type'] == '环形':
                polygon1 = QPolygon([aa.toPoint() for aa in editing_polygon['widget_points'][0]])
                polygon2 = QPolygon([aa.toPoint() for aa in editing_polygon['widget_points'][1]])
                self.r1, self.r2 = QRegion(polygon1), QRegion(polygon2)
                self.painter.setClipRegion(self.r1 - self.r2)
                self.painter.fillRect(self.r1.boundingRect(), QColor(0, 255, 0, 150))

            signal_selected_shape.send(self.polygon_editing_i)

    def draw_completed_polygons(self):  # 在标注时画已完成的完整图形
        for one in self.all_polygons:
            self.painter.setPen(QPen(QColor(one['qcolor']), self.seg_pen_size))
            if one['shape_type'] == '多边形':
                self.painter.drawPolygon(one['widget_points'])
            elif one['shape_type'] in ('矩形', '椭圆形'):
                if len(one['widget_points']):
                    x1, y1 = one['widget_points'][0].toTuple()
                    x2, y2 = one['widget_points'][1].toTuple()
                    if one['shape_type'] == '矩形':
                        self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                    elif one['shape_type'] == '椭圆形':
                        self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
            elif one['shape_type'] == '环形':
                for one_p in one['widget_points']:
                    self.painter.drawPolygon(one_p)

        if self.shape_type == '环形' and len(self.widget_points_huan):
            self.painter.drawPolygon(self.widget_points_huan[0])

    def draw_selected_shape(self, i):
        self.polygon_editing_i = i
        self.update()

    def get_editing_polygon(self):
        polygon = None
        for i, one in enumerate(self.all_polygons):
            point = self.cursor_in_widget.toTuple()
            if one['shape_type'] == '环形':
                wp1 = [aa.toTuple() for aa in one['widget_points'][0]]
                wp2 = [aa.toTuple() for aa in one['widget_points'][1]]
                shape_points = [wp1, wp2]
            else:
                shape_points = [aa.toTuple() for aa in one['widget_points']]

            polygon = point_in_shape(point, shape_points, one['shape_type'])

            if polygon is not None:
                self.setFocus(Qt.OtherFocusReason)
                self.polygon_editing_i = i
                break
            else:
                self.clearFocus()

        return polygon

    def get_json_polygons(self):
        json_polygons = deepcopy(self.all_polygons)

        if len(json_polygons):
            for one in json_polygons:
                if one['shape_type'] == '环形':
                    out_c, in_c = one['widget_points'][0], one['widget_points'][1]
                    widget_points = [[aa.toTuple() for aa in out_c], [aa.toTuple() for aa in in_c]]
                else:
                    widget_points = [aa.toTuple() for aa in one['widget_points']]

                one['widget_points'] = widget_points

        return json_polygons

    def json_to_polygons(self, json_path, json_data=None):
        if json_data is None:
            with open(json_path, 'r') as f:
                content = json.load(f)
                polygons, ori_h, ori_w = content['polygons'], content['img_height'], content['img_width']
        else:
            polygons, ori_h, ori_w = json_data

        if int(ori_h) == 0:
            QMessageBox.critical(self, '文件错误', f'"{json_path}"记录的图片高度为0。')
            return

        self.center_point()
        img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
        img_pixel_real_pixel = img_h / ori_h  # 图片的一个像素点实际对于控件展示的图片有多少个像素点

        for one in polygons:
            if one['shape_type'] == '环形':
                img_points = [[QPointF(aa[0], aa[1]) for aa in one['img_points'][0]],
                              [QPointF(aa[0], aa[1]) for aa in one['img_points'][1]]]
                wp1 = [aa * img_pixel_real_pixel + self.img_tl_point for aa in img_points[0]]
                wp2 = [aa * img_pixel_real_pixel + self.img_tl_point for aa in img_points[1]]
                widget_points = [wp1, wp2]
            else:
                img_points = [QPointF(aa[0], aa[1]) for aa in one['img_points']]
                widget_points = [aa * img_pixel_real_pixel + self.img_tl_point for aa in img_points]

            one['widget_points'] = widget_points

        self.all_polygons = polygons

    def modify_polygon_class(self, i, new_class, new_color):
        polygon = self.all_polygons[i]
        polygon['category'] = new_class
        polygon['qcolor'] = new_color
        self.update()

    def move_pix_img(self):  # 拖曳图片功能
        if self.LeftClick:
            old_img_tl = self.img_tl_point
            self.img_tl_point = self.img_tl_point + self.cursor_in_widget - self.start_pos
            self.start_pos = self.cursor_in_widget
            self.shape_scale_move(old_img_tl)
        self.update()

    def move_polygons(self, key_left=False, key_right=False, key_up=False, key_down=False):
        offset = None
        img_w, img_h = self.img.width(), self.img.height()

        if key_left:
            offset = QPointF(-int(img_w / 300) - 1, 0)
        elif key_right:
            offset = QPointF(int(img_w / 300) + 1, 0)
        elif key_up:
            offset = QPointF(0, -int(img_h / 300) - 1)
        elif key_down:
            offset = QPointF(0, int(img_h / 300) + 1)
        elif self.LeftClick:
            offset = self.cursor_in_widget - self.start_pos

        if (offset is not None) and (self.polygon_editing_i is not None):
            b_left, b_up, b_right, b_down = self.get_border_coor()
            border = (b_left, b_up, b_right, b_down)
            editing_polygon = self.all_polygons[self.polygon_editing_i]
            if editing_polygon['shape_type'] == '环形':
                wp1, wp2 = editing_polygon['widget_points']
                editing_polygon['img_points'], editing_polygon['widget_points'] = [[], []], [[], []]

                for i, one_wp in enumerate([wp1, wp2]):
                    for one_point in one_wp:
                        one_point += offset
                        # 防止坐标越界
                        in_border_x = min(max(b_left, one_point.x()), b_right)
                        in_border_y = min(max(b_up, one_point.y()), b_down)
                        one_point = QPointF(in_border_x, in_border_y)
                        editing_polygon['widget_points'][i].append(one_point)

                        img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(one_point, border=border)
                        if img_pixel_x is not None:
                            editing_polygon['img_points'][i].append([img_pixel_x, img_pixel_y])

            else:
                widget_points = editing_polygon['widget_points']
                editing_polygon['img_points'], editing_polygon['widget_points'] = [], []

                for one_point in widget_points:
                    one_point += offset
                    # 防止坐标越界
                    in_border_x = min(max(b_left, one_point.x()), b_right)
                    in_border_y = min(max(b_up, one_point.y()), b_down)
                    one_point = QPointF(in_border_x, in_border_y)
                    editing_polygon['widget_points'].append(one_point)

                    img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(one_point, border=border)

                    if img_pixel_x is not None:
                        editing_polygon['img_points'].append([img_pixel_x, img_pixel_y])

            if self.LeftClick:
                self.start_pos = self.cursor_in_widget

        self.update()

    @staticmethod
    def move_to_new_folder():
        signal_move2new_folder.send(True)

    def one_polygon_done(self, qcolor, category):
        # self.compute_shape_attr()

        if self.shape_type == '环形':
            self.all_polygons.append({'category': category, 'qcolor': qcolor, 'shape_type': self.shape_type,
                                      'widget_points': self.widget_points_huan, 'img_points': self.img_points_huan})
            self.clear_widget_img_points_huan()
        else:
            self.all_polygons.append({'category': category, 'qcolor': qcolor, 'shape_type': self.shape_type,
                                      'widget_points': self.widget_points, 'img_points': self.img_points})
            self.clear_widget_img_points()

        self.update()

    def remove_widget_img_pair(self):
        if len(self.widget_points):
            self.widget_points.pop()
            self.img_points.pop()

    def set_angle(self, angle):
        self.angle = angle

    def set_mode(self, cls=False, m_cls=False, det=False, seg=False, seg_edit=False, ann=False):
        self.ClsMode, self.MClsMode, self.DetMode, self.SegMode, self.SegEditMode, self.AnnMode = \
            cls, m_cls, det, seg, seg_edit, ann

        self.setMouseTracking(not self.AnnMode)

        if cls:
            self.setCursor(Qt.OpenHandCursor)
        if m_cls:
            self.setCursor(Qt.OpenHandCursor)
        if det:
            self.setCursor(Qt.CrossCursor)
        if seg:
            self.setCursor(Qt.CrossCursor)
        if seg_edit:
            self.unsetCursor()
        if ann:
            self.setCursor(Qt.OpenHandCursor)

        if not ann:
            self.clear_scaled_img()

    def shape_scale_move(self, old_img_tl, scale_factor=(1., 1.)):
        for one in self.all_polygons:
            if one['shape_type'] == '环形':
                wp1 = self.shape_scale_convert(one['widget_points'][0], old_img_tl, scale_factor)
                wp2 = self.shape_scale_convert(one['widget_points'][1], old_img_tl, scale_factor)
                one['widget_points'] = [wp1, wp2]
            else:
                one['widget_points'] = self.shape_scale_convert(one['widget_points'], old_img_tl, scale_factor)

        self.widget_points = self.shape_scale_convert(self.widget_points, old_img_tl, scale_factor)

        for i, one in enumerate(self.widget_points_huan):
            moved = self.shape_scale_convert(one, old_img_tl, scale_factor)
            self.widget_points_huan[i] = moved

    def show_menu(self, ob):  # 在鼠标位置显示菜单
        self.add_poly_to_collection.setDisabled(self.polygon_editing_i is None)
        self.draw_collection_shape.setDisabled(not self.SegMode)
        ob.exec(QCursor.pos())
