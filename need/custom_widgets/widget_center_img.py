#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
from typing import List, Union
from copy import deepcopy
from PySide6.QtWidgets import QInputDialog, QMessageBox, QApplication, QMenu, QListWidgetItem, QLabel, QGraphicsView, \
    QGraphicsScene, QGraphicsRectItem, QGraphicsItem, QGraphicsPixmapItem
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QEvent
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QPen, QUndoStack, QCursor, QRegion, QPolygon, QAction, \
    QImageReader, QIcon
from PySide6 import QtCore
from need.utils import point_in_shape, AnnUndo, shape_type
from need.custom_signals import *
from need.custom_widgets import SelectItem, signal_select_window_close

signal_check_draw_enable = BoolSignal()
signal_del_shape = IntSignal()
signal_move2new_folder = BoolSignal()
signal_open_label_window = BoolSignal()
signal_one_collection_done = StrSignal()
signal_select_collection_ok = StrSignal()
signal_draw_selected_shape = IntSignal()
signal_set_shape_list_selected = IntSignal()
signal_shape_info_update = IntSignal()
signal_shape_type = StrSignal()
signal_xy_color2ui = ListSignal()
signal_select_tag_ok = StrSignal()


class BaseImgFrame(QLabel):
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
        # todo: bug, 不知道为什么基类的menu右键的时候不显示
        self.img_menu = QMenu('img_menu', self)
        self.img_menu.setFixedWidth(135)
        self.action_bilinear = QAction(self.tr('双线性插值缩放'), self)
        self.action_bilinear.triggered.connect(lambda: self.set_interpolation(Qt.SmoothTransformation))
        self.action_nearest = QAction(self.tr('最近邻插值缩放'), self)
        self.action_nearest.setIcon(QPixmap('images/icon_11.png'))
        self.action_nearest.triggered.connect(lambda: self.set_interpolation(Qt.FastTransformation))
        self.img_menu.addAction(self.action_nearest)
        self.img_menu.addAction(self.action_bilinear)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_menu)

        self.img, self.scaled_img = None, None
        self.img_tl = QPointF(0., 0.)  # 图片左上角在控件坐标系的坐标
        self.start_pos = None
        self.bm_start = None
        self.LeftClick = False  # 用于图片拖曳和标注拖曳功能中，判断左键是否按下
        self.interpolation = Qt.FastTransformation

        self.IsClosed = False

    def contextMenuEvent(self, event):
        self.img_menu.exec(self.mapToGlobal(event.pos()))

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
        self.painter.drawPixmap(self.img_tl, self.scaled_img)
        self.painter.end()

    def wheelEvent(self, e):
        ex, ey = e.position().x(), e.position().y()
        img_w, img_h = self.scaled_img.width(), self.scaled_img.height()
        scale_ratio = 0.95
        old_x, old_y = self.img_tl.x(), self.img_tl.y()
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
        self.img_tl = QPointF(new_img_x, new_img_y)

        self.update()

    def center_point(self):  # 图片居中显示
        new_x = (self.size().width() - self.scaled_img.width()) / 2
        new_y = (self.size().height() - self.scaled_img.height()) / 2
        self.img_tl = QPointF(new_x, new_y)  # 图片的坐上角在控件坐标系的坐标

    def get_border_coor(self):  # 获取图片在控件坐标系的左上角、右下角坐标
        t_l_x, t_l_y = self.img_tl.x(), self.img_tl.y()  # 图片左上角在控件坐标系的坐标，可为负
        img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
        b_r_x, b_r_y = t_l_x + img_w - 1, t_l_y + img_h - 1
        return t_l_x, t_l_y, b_r_x, b_r_y

    def get_widget_to_img_ratio(self):  # 图片的一个像素点实际对于控件展示区域有多少个坐标点
        ori_w, ori_h = self.img.size().width(), self.img.size().height()

        if ori_w and ori_h:
            img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
            img_h2real_h = img_h / ori_h
            img_w2real_w = img_w / ori_w
            return img_w2real_w, img_h2real_h
        else:
            return None, None

    def move_pix_img(self):  # 拖曳图片功能
        if self.LeftClick:
            self.img_tl = self.img_tl + self.cursor_in_widget - self.start_pos
            self.start_pos = self.cursor_in_widget
        self.update()

    def paint_img(self, img_path_or_pix_map, re_center=True):
        if img_path_or_pix_map is None:  # 有时候是None，原因未知
            return

        self.img = QPixmap(img_path_or_pix_map)  # self.img始终保持为原图，
        # if self.img.isNull():  # 如果图片太大，QPixmap或QImage会打不开，用QImageReader
        #     QImageReader.setAllocationLimit(256)
        #     img = QImageReader(img_path_or_pix_map)
        #     img.setScaledSize(QSize(1024, 1024))
        #     print(img.canRead())
        #     print(img.size())
        #     kkk = img.read()
        #     pass

        if re_center:
            if img_path_or_pix_map == 'images/bg.png':
                self.scaled_img = self.img.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self.scaled_img = self.img.scaled(self.size(), Qt.KeepAspectRatio, self.interpolation)
            self.center_point()
        else:
            self.scaled_img = self.img.scaled(self.scaled_img.size(), Qt.KeepAspectRatio, self.interpolation)

        self.update()

    def set_interpolation(self, mode):
        if mode == Qt.FastTransformation:
            self.action_nearest.setIcon(QPixmap('images/icon_11.png'))
            self.action_bilinear.setIcon(QPixmap(''))
        elif mode == Qt.SmoothTransformation:
            self.action_bilinear.setIcon(QPixmap('images/icon_11.png'))
            self.action_nearest.setIcon(QPixmap(''))
        self.interpolation = mode

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

    def widget_coor_to_img_coor(self, rel_pos: QtCore.QPointF):
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


class CenterImg(BaseImgFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scaled_img_painted = None
        self.collection_window = SelectItem(title=self.tr('收藏标注'), button_signal=signal_select_collection_ok)
        self.tag_window = SelectItem(title=self.tr('标签'), button_signal=signal_select_tag_ok)

        self.det_cross_color = QColor(120, 120, 120)
        self.seg_pen_size = 2
        self.seg_pen_color = QColor('red')
        self.ann_pen_size = 4
        self.ann_pen_color = QColor('red')
        self.ann_font_size = 20
        self.ann_font_color = QColor('white')

        self.collected_shapes = {}
        self.__all_polygons = []
        self.widget_points = []
        self.img_points = []
        self.widget_points_huan = []
        self.img_points_huan = []

        self.shape_type = self.tr('多边形')
        self.cursor_in_widget = QPointF(0., 0.)  # 鼠标在控件坐标系的实时坐标
        self.polygon_editing_i = None  # 正在编辑的标注的索引，即标注高亮时对应的索引
        self.ann_point_last = QPoint(0, 0)
        self.ann_point_cur = QPoint(0, 0)
        self.img_tl = QPointF(0., 0.)  # 图片左上角在控件坐标系的坐标
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
        pencil_pixmap = pencil_pixmap.scaled(30, 30)
        self.pencil_cursor = QCursor(pencil_pixmap, 3, 3)

        self.ClsMode = True
        self.MClsMode = False
        self.DetMode = False
        self.SegMode = False
        self.DrawMode = True
        self.ShapeEditMode = False
        self.AnnMode = False
        self.LeftClick = False  # 用于实现图片拖曳和标注拖曳功能
        self.PolygonLastPointDone = False  # 用于SegMode标识画完一个多边形
        self.PolygonLocked = False
        # 如果触发了一次 '内环越界'，就置为True，在下次mouseReleaseEvent再置为False，确保不会不停的触发'内环越界'
        self.OutInConflict = False
        self.HideCross = False
        self.MovingPolygon = False  # 仅在拖动标注移动时为True
        self.MovingCorner = False
        self.FlagDrawCollection = False

        self.draw_collection_shape = QAction(self.tr('绘制收藏的标注'), self)
        self.draw_collection_shape.setIcon(QIcon('images/draw.png'))
        self.draw_collection_shape.triggered.connect(lambda: self.show_collection_window(True))
        self.draw_collection_shape.setDisabled(True)
        self.action_move2folder = QAction(self.tr('移动至新文件夹'), self)
        self.action_move2folder.setIcon(QIcon('images/move_to.png'))
        self.action_move2folder.triggered.connect(self.move_to_new_folder)
        self.img_menu.addAction(self.draw_collection_shape)
        self.img_menu.addAction(self.action_move2folder)

        self.shape_menu = QMenu('shape_menu', self)
        self.action_add_collection = QAction(self.tr('收藏标注'), self)
        self.action_add_collection.setIcon(QIcon('images/favorite.png'))
        self.action_add_collection.triggered.connect(lambda: self.show_collection_window(False))
        self.shape_menu.addAction(self.action_add_collection)
        self.shape_menu.addAction(self.tr('添加标签')).triggered.connect(self.show_tag_window)

        signal_draw_selected_shape.signal.connect(self.draw_selected_shape)
        signal_shape_type.signal.connect(self.change_shape_type)
        signal_select_window_close.signal.connect(self.clear_widget_img_points)
        signal_select_collection_ok.signal.connect(self.select_collection_ok)
        # signal_select_tag_ok.signal.connect(self.select_tag_ok)  # todo--------------------------

    def keyPressEvent(self, event):
        if self.corner_index is None and self.polygon_editing_i is not None:
            if event.key() == Qt.Key_A:
                self.move_polygons(key_left=True)
            elif event.key() == Qt.Key_D:
                self.move_polygons(key_right=True)
            elif event.key() == Qt.Key_W:
                self.move_polygons(key_up=True)
            elif event.key() == Qt.Key_S:
                self.move_polygons(key_down=True)

        if event.key() == Qt.Key_Delete:
            self.del_polygons()

        if self.MovingPolygon:
            signal_shape_info_update.send(self.polygon_editing_i)
            self.MovingPolygon = False

    def mouseDoubleClickEvent(self, e, show_bg=False):  # 同时触发 mousePressEvent()
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if self.AnnMode:
                self.ann_add_text(e.position())
        else:
            if self.scaled_img is not None:
                if self.AnnMode and self.scaled_img_painted is not None:
                    action_img = self.scaled_img_painted
                else:
                    action_img = self.img

                old_img_tl = self.img_tl
                old_img_w, old_img_h = self.scaled_img.width(), self.scaled_img.height()
                interpolation = Qt.SmoothTransformation if show_bg else self.interpolation
                self.scaled_img = action_img.scaled(self.size(), Qt.KeepAspectRatio, interpolation)

                scale_factor = (self.scaled_img.width() / old_img_w, self.scaled_img.height() / old_img_h)
                self.center_point()
                self.shape_scale_move(old_img_tl, scale_factor)
                self.update()

    def mouseMoveEvent(self, e):
        self.cursor_in_widget = e.position()  # 相当于self.mapFromGlobal(e.globalPosition())

        if self.bm_start is not None:
            self.parent().moving_bookmark(self.cursor_in_widget - self.bm_start)
            self.bm_start = self.cursor_in_widget
        else:
            img_pixel_x, img_pixel_y, qcolor = self.widget_coor_to_img_coor(self.cursor_in_widget)
            if img_pixel_x is not None:  # 实时显示坐标，像素值
                signal_xy_color2ui.send([img_pixel_x, img_pixel_y, qcolor.red(), qcolor.green(), qcolor.blue()])

            if self.AnnMode:
                if QApplication.keyboardModifiers() == Qt.ControlModifier:
                    self.ann_draw()
                else:
                    self.move_pix_img()
            else:
                if self.DetMode:  # 触发画十字线
                    self.update()

                if QApplication.keyboardModifiers() == Qt.ControlModifier:
                    if self.DetMode or self.SegMode:
                        self.update()

                        if self.shape_type in shape_type('像素') and len(self.img_points):
                            self.add_widget_img_pair(self.cursor_in_widget, fill_mode=True)
                else:
                    if self.ShapeEditMode:
                        if QApplication.keyboardModifiers() != Qt.ShiftModifier:
                            # 有了self.polygon_editing_i后，在paintEvent()里触发draw_editing_polygon()才有效
                            if not self.MovingPolygon and not self.PolygonLocked:
                                self.polygon_editing_i = self.get_editing_polygon()

                            if self.LeftClick:
                                if not self.MovingPolygon and self.corner_index is not None:
                                    self.corner_point_move(self.corner_index)  # 角点移动功能先于标注移动功能
                                elif self.polygon_editing_i is not None:
                                    self.move_polygons()
                                else:
                                    self.move_pix_img()
                            else:
                                self.update()  # 为了触发draw_editing_polygon()
                    else:
                        self.move_pix_img()

        self.set_focus()

    def mousePressEvent(self, e):
        e_pos = e.pos().toTuple()
        bm_tl, bm_br = self.parent().bm_active_area()
        if bm_tl[0] < e_pos[0] < bm_br[0] and bm_tl[1] < e_pos[1] < bm_br[1]:  # move bookmark
            self.bm_start = e.pos()
        else:
            if self.AnnMode or self.ClsMode or self.MClsMode:
                self.setCursor(Qt.ClosedHandCursor)

            if QApplication.keyboardModifiers() == Qt.ControlModifier:
                signal_check_draw_enable.send(True)

                if self.AnnMode:
                    self.setCursor(self.pencil_cursor)
                    self.ann_point_cur = e.position() - self.img_tl
                    self.ann_point_last = self.ann_point_cur

                    command = AnnUndo(self, self.scaled_img.copy())
                    self.undo_stack.push(command)  # 添加command用于撤销功能
                else:
                    if self.DetMode or self.SegMode:
                        if self.PolygonLastPointDone:
                            self.shape_done_open_label_window()
                        else:
                            self.cursor_in_widget = e.position()
                            if self.shape_type in shape_type('像素'):
                                self.add_widget_img_pair(self.cursor_in_widget, fill_mode=True)
                            else:
                                self.add_widget_img_pair(self.cursor_in_widget)
            else:
                if e.button() == Qt.LeftButton:
                    self.LeftClick = True
                    self.start_pos = e.position()

    def mouseReleaseEvent(self, e):
        if self.bm_start is not None:
            self.parent().moved_bookmark()
            self.bm_start = None
        if self.MovingPolygon:
            signal_shape_info_update.send(self.polygon_editing_i)
            self.MovingPolygon = False
        if type(self.MovingCorner) == int:
            signal_shape_info_update.send(self.MovingCorner)
            self.MovingCorner = False

        if self.OutInConflict:
            self.OutInConflict = False

        if e.button() == Qt.LeftButton:
            self.LeftClick = False

        if self.AnnMode:
            self.setCursor(Qt.OpenHandCursor)

        if not (self.DetMode or self.SegMode) and QApplication.keyboardModifiers() != Qt.ControlModifier:
            self.setCursor(Qt.OpenHandCursor)

        if QApplication.keyboardModifiers() == Qt.ControlModifier and (self.DetMode or self.SegMode):
            if self.shape_type in shape_type(['矩形', '椭圆形']):
                point_br = e.position()
                b_left, b_up, b_right, b_down = self.get_border_coor()
                if b_left <= point_br.x() <= b_right and b_up <= point_br.y() <= b_down:
                    if len(self.widget_points):
                        self.add_widget_img_pair(point_br)

                        if len(self.widget_points) in (0, 3):  # 一些误操作导致长度错误，直接清空重画
                            self.clear_widget_img_points()
                        else:
                            signal_open_label_window.send(True)
                else:
                    self.clear_widget_img_points()
            elif self.shape_type in shape_type('像素'):
                signal_open_label_window.send(True)
        elif QApplication.keyboardModifiers() == Qt.ShiftModifier and self.ShapeEditMode:
            self.erase_paint_pixel(self.polygon_editing_i)
            signal_shape_info_update.send(self.polygon_editing_i)

    def paintEvent(self, e):  # 程序调用show()和update()之后就会调用此函数
        self.painter.begin(self)
        self.painter.drawPixmap(self.img_tl, self.scaled_img)

        if self.DetMode:
            if not self.HideCross:  # 画十字线
                self.painter.setPen(QPen(self.det_cross_color, 1, Qt.DashLine))
                x, y = self.cursor_in_widget.toTuple()
                self.painter.drawLine(0, y, 9999, y)
                self.painter.drawLine(x, 0, x, 9999)

        if self.DetMode or self.SegMode:
            self.PolygonLastPointDone = False
            self.draw_completed_polygons()

            if self.ShapeEditMode:
                if not self.MovingPolygon:
                    self.corner_index = self.cursor_close_to_corner()

                self.draw_editing_polygon()

            if QApplication.keyboardModifiers() == Qt.ControlModifier:
                if len(self.widget_points):
                    self.painter.setPen(QPen(self.seg_pen_color, self.seg_pen_size))
                    if self.shape_type in shape_type(['矩形', '椭圆形']):
                        if len(self.widget_points) in (0, 3):  # 一些误操作导致长度错误，直接清空重画
                            self.clear_widget_img_points()
                        else:
                            if len(self.widget_points) == 2:
                                x1, y1 = self.widget_points[0].toTuple()
                                x2, y2 = self.widget_points[1].toTuple()
                            elif len(self.widget_points) == 1:
                                x1, y1 = self.widget_points[0].toTuple()
                                x2, y2 = self.cursor_in_widget.toTuple()

                            if self.shape_type in shape_type('矩形'):
                                self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                            elif self.shape_type in shape_type('椭圆形'):
                                self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))

                    elif self.shape_type in shape_type(['多边形', '环形']):
                        if len(self.widget_points) >= 2:  # 画已完成的完整线段
                            for i in range(len(self.widget_points) - 1):
                                self.painter.drawLine(self.widget_points[i], self.widget_points[i + 1])
                        if len(self.widget_points):  # 画最后一个点到鼠标的线段
                            self.painter.drawLine(self.widget_points[-1], self.cursor_in_widget)

                        if len(self.widget_points) >= 3:  # 至少3个点才能绘制出polygon
                            # 判定是否到了第一个点
                            result = self.close_to_corner(self.widget_points[0])
                            if result:
                                self.PolygonLastPointDone = True

                    elif self.shape_type in shape_type('像素'):
                        self.fill_img_pixel(self.img_points, self.seg_pen_color)

        self.painter.end()

    def wheelEvent(self, e):
        if self.polygon_editing_i is None:
            ex, ey = e.position().x(), e.position().y()
            img_w, img_h = self.scaled_img.width(), self.scaled_img.height()
            scale_ratio = 0.95
            old_x, old_y = self.img_tl.x(), self.img_tl.y()
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
            self.img_tl = QPointF(new_img_x, new_img_y)

            if self.DetMode or self.SegMode:  # 已标注图形的伸缩
                scale_factor = (new_img_w / img_w, new_img_h / img_h)
                self.shape_scale_move(QPointF(old_x, old_y), scale_factor)

        self.update()

    def add_widget_img_pair(self, qpointf, fill_mode=False):
        img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(qpointf)

        if img_pixel_x is not None:
            img_p = [img_pixel_x, img_pixel_y]

            if fill_mode:
                if img_p not in self.img_points:
                    self.img_points.append(img_p)
                    self.widget_points.append(self.img_coor_to_widget_coor(img_p))
            else:
                self.img_points.append(img_p)
                self.widget_points.append(qpointf)

            self.update()

    def ann_add_text(self, ori_position):  # 注释模式添加文字功能
        input_dlg = QInputDialog()
        input_dlg.setWindowTitle(self.tr('文字注释'))
        input_dlg.resize(400, 100)
        input_dlg.setLabelText(self.tr('请输入注释：'))
        is_ok = input_dlg.exec()

        self.painter.begin(self.scaled_img)
        self.painter.setPen(self.ann_font_color)
        self.painter.setFont(QFont('Decorative', self.ann_font_size))
        if is_ok:
            pos = (ori_position - self.img_tl).toPoint()
            self.painter.drawText(pos, input_dlg.textValue())
        self.painter.end()
        self.update()
        self.scaled_img_painted = self.scaled_img.copy()  # 保存一个绘图的副本用于伸缩功能

    def ann_draw(self):  # 注释模式涂鸦功能
        self.ann_point_cur = self.cursor_in_widget - self.img_tl  # 绘图的坐标系应为图片坐标系
        self.painter.begin(self.scaled_img)
        self.painter.setPen(QPen(self.ann_pen_color, self.ann_pen_size))
        self.painter.drawLine(self.ann_point_last, self.ann_point_cur)
        self.painter.end()
        self.update()
        self.ann_point_last = self.ann_point_cur
        self.scaled_img_painted = self.scaled_img.copy()  # 保存一个绘图的副本

    def change_pen(self, det_cross_color=None, seg_pen_size=None, seg_pen_color=None,
                   ann_pen_size=None, ann_pen_color=None):
        if det_cross_color is not None:
            self.det_cross_color = det_cross_color
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

    def clear_all_polygons(self):
        self.__all_polygons = []
        self.clear_widget_img_points()
        self.clear_widget_img_points_huan()
        self.update()

    def clear_editing_i_corner(self):
        self.polygon_editing_i = None
        self.corner_index = None

    def clear_scaled_img(self, to_undo=True):
        if to_undo:
            command = AnnUndo(self, self.scaled_img.copy())
            self.undo_stack.push(command)

        self.scaled_img = self.img.scaled(self.scaled_img.size(), Qt.KeepAspectRatio, self.interpolation)
        self.update()
        self.scaled_img_painted = self.scaled_img.copy()

    def clear_widget_img_points(self):
        self.widget_points = []
        self.img_points = []

    def clear_widget_img_points_huan(self):
        self.widget_points_huan = []
        self.img_points_huan = []

    def close_to_corner(self, points, radius=3, is_ellipse=False):
        self.painter.setPen(Qt.NoPen)
        self.painter.setBrush(QColor('lightgreen'))

        if not is_ellipse:
            x, y = points.toTuple()
            if (x - 3 < self.cursor_in_widget.x() < x + 3) and (y - 3 < self.cursor_in_widget.y() < y + 3):
                self.painter.drawEllipse(x - 2 * radius, y - 2 * radius, 12, 12)
                return True
        else:
            x1, y1 = points[0].toTuple()
            x2, y2 = points[1].toTuple()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            cursor = self.cursor_in_widget.toTuple()
            if not point_in_shape(cursor, [(x1, y1), (x2, y2)], shape_type=self.tr('椭圆形')):
                if x1 <= cursor[0] <= cx and y1 <= cursor[1] <= cy:
                    self.painter.drawEllipse(x1 - 0 * radius, y1 - 0 * radius, 12, 12)
                    return 0
                elif cx <= cursor[0] <= x2 and cy <= cursor[1] <= y2:
                    self.painter.drawEllipse(x2 - 3 * radius, y2 - 3 * radius, 12, 12)
                    return 1

        return False

    def corner_point_move(self, corner_index):  # 标注角点的拖动功能
        offset = self.cursor_in_widget - self.start_pos
        if type(corner_index) == int:
            i = corner_index
        elif len(corner_index) == 2:
            i, j = corner_index
        elif len(corner_index) == 3:
            i, j, k = corner_index

        if self.PolygonLocked:
            if i != self.polygon_editing_i:
                return

        b_left, b_up, b_right, b_down = self.get_border_coor()
        polygon = self.__all_polygons[i]

        if polygon['shape_type'] in shape_type('像素'):  # 像素标注不具备这个功能
            return

        # 处理widget_points
        if polygon['shape_type'] in shape_type('环形'):
            new_x, new_y = (polygon['widget_points'][j][k] + offset).toTuple()
            new_x, new_y = min(max(new_x, b_left), b_right), min(max(new_y, b_up), b_down)

            if not self.OutInConflict:
                out_c = [aa.toTuple() for aa in polygon['widget_points'][0]]
                if j == 0:
                    in_c = polygon['widget_points'][1]
                    for one in in_c:
                        if not point_in_shape(one.toTuple(), out_c, self.tr('多边形')):
                            self.LeftClick = False
                            self.OutInConflict = True
                            QMessageBox.warning(self, self.tr('内环越界'), self.tr('内环不完全在外环内部。'))
                            return
                if j == 1:
                    if not point_in_shape((new_x, new_y), out_c, self.tr('多边形')):
                        self.LeftClick = False
                        self.OutInConflict = True
                        QMessageBox.warning(self, self.tr('内环越界'), self.tr('内环不完全在外环内部。'))
                        return

            polygon['widget_points'][j][k] = QPointF(new_x, new_y)
        else:
            new_x, new_y = (polygon['widget_points'][j] + offset).toTuple()
            new_x, new_y = min(max(new_x, b_left), b_right), min(max(new_y, b_up), b_down)
            polygon['widget_points'][j] = QPointF(new_x, new_y)

        # 处理对应的img_points
        if polygon['shape_type'] in shape_type('多边形'):
            x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][j])
            if x is not None:
                polygon['img_points'][j] = (x, y)
        elif polygon['shape_type'] in shape_type(['矩形', '椭圆形']):
            if j == 0:
                x1, y1 = polygon['widget_points'][j].toTuple()
                x2, y2 = polygon['widget_points'][1].toTuple()
            elif j == 1:
                x2, y2 = polygon['widget_points'][j].toTuple()
                x1, y1 = polygon['widget_points'][0].toTuple()

            polygon['widget_points'][0] = QPointF(x1, y1)
            polygon['widget_points'][1] = QPointF(x2, y2)

            for k in range(2):
                x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][k])
                if x is not None:
                    polygon['img_points'][k] = (x, y)
        elif polygon['shape_type'] in shape_type('环形'):
            x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][j][k])
            if x is not None:
                polygon['img_points'][j][k] = (x, y)

        self.start_pos = self.cursor_in_widget
        self.update()
        self.MovingCorner = i

    def cursor_close_to_corner(self):
        corner_index = None

        for i, polygon in enumerate(self.__all_polygons):
            if polygon['shape_type'] in shape_type('环形'):
                for j, huan in enumerate(polygon['widget_points']):
                    for k, point in enumerate(huan):
                        if self.close_to_corner(point):
                            corner_index = (i, j, k)
                            return corner_index
            elif polygon['shape_type'] in shape_type('像素'):
                pass
            else:
                for j, point in enumerate(polygon['widget_points']):
                    if polygon['shape_type'] in shape_type('椭圆形'):
                        p_i = self.close_to_corner(polygon['widget_points'], is_ellipse=True)
                        if type(p_i) == int:
                            corner_index = (i, p_i)
                            return corner_index
                    else:
                        if self.close_to_corner(point):
                            corner_index = (i, j)
                            return corner_index
        return corner_index

    def del_polygons(self):
        if (self.DetMode or self.SegMode) and self.ShapeEditMode and self.polygon_editing_i is not None:
            self.__all_polygons.pop(self.polygon_editing_i)
            signal_del_shape.send(self.polygon_editing_i)
            self.polygon_editing_i = None
        self.update()

    def draw_editing_polygon(self):  # 画正在编辑中的polygon
        if self.__all_polygons and self.polygon_editing_i is not None:
            self.painter.setPen(Qt.NoPen)
            self.painter.setBrush(QColor(0, 255, 0, 150))
            editing_poly = self.__all_polygons[self.polygon_editing_i]

            st = editing_poly['shape_type']
            if st in shape_type(['矩形', '椭圆形']):
                x1, y1 = editing_poly['widget_points'][0].toTuple()
                x2, y2 = editing_poly['widget_points'][1].toTuple()
                if st in shape_type('矩形'):
                    self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                elif st in shape_type('椭圆形'):
                    self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
            elif st in shape_type('多边形'):
                self.painter.drawPolygon(editing_poly['widget_points'])
            elif st in shape_type('环形'):
                polygon1 = QPolygon([aa.toPoint() for aa in editing_poly['widget_points'][0]])
                polygon2 = QPolygon([aa.toPoint() for aa in editing_poly['widget_points'][1]])
                self.r1, self.r2 = QRegion(polygon1), QRegion(polygon2)
                self.painter.setClipRegion(self.r1 - self.r2)
                self.painter.fillRect(self.r1.boundingRect(), QColor(0, 255, 0, 150))
            elif st in shape_type('像素'):
                self.fill_img_pixel(editing_poly['img_points'], QColor(0, 255, 0, 150))

            signal_set_shape_list_selected.send(self.polygon_editing_i)

    def draw_completed_polygons(self):  # 在标注时画已完成的完整图形
        # note: 在ShapeEditMode时，鼠标移动时也在频繁触发，要关注绘制数量较大时，是否会造成系统负担
        for one in self.__all_polygons:
            self.painter.setPen(QPen(QColor(one['qcolor']), self.seg_pen_size))
            if one['shape_type'] in shape_type('多边形'):
                self.painter.drawPolygon(one['widget_points'])
            elif one['shape_type'] in shape_type(['矩形', '椭圆形']):
                if len(one['widget_points']):
                    x1, y1 = one['widget_points'][0].toTuple()
                    x2, y2 = one['widget_points'][1].toTuple()
                    if one['shape_type'] in shape_type('矩形'):
                        self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                    elif one['shape_type'] in shape_type('椭圆形'):
                        self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
            elif one['shape_type'] in shape_type('环形'):
                for one_p in one['widget_points']:
                    self.painter.drawPolygon(one_p)
            elif one['shape_type'] in shape_type('像素'):
                self.fill_img_pixel(one['img_points'], QColor(one['qcolor']))

        if self.shape_type in shape_type('环形') and len(self.widget_points_huan):
            self.painter.drawPolygon(self.widget_points_huan[0])

    def draw_selected_shape(self, i):
        if self.ShapeEditMode:
            self.polygon_editing_i = i
            self.update()

    def erase_paint_pixel(self, fill_index):
        if fill_index is not None:
            x, y, _ = self.widget_coor_to_img_coor(self.cursor_in_widget)
            new_p = [x, y]
            img_points = self.__all_polygons[fill_index]['img_points']
            widget_points = self.__all_polygons[fill_index]['widget_points']

            if new_p in img_points:
                index = img_points.index(new_p)
                img_points.pop(index)
                widget_points.pop(index)
            else:
                img_points.append(new_p)
                widget_points.append(self.img_coor_to_widget_coor(new_p))

            self.update()

    def fill_img_pixel(self, img_points, qcolor):
        self.painter.setBrush(qcolor)
        img_w2real_w, img_h2real_h = self.get_widget_to_img_ratio()

        img_tl_tuple = self.img_tl.toTuple()

        tl_points = [(aa[0] * img_w2real_w, aa[1] * img_h2real_h) for aa in img_points]
        tl_points = [(aa[0] + img_tl_tuple[0], aa[1] + img_tl_tuple[1]) for aa in tl_points]

        br_points = [((aa[0] + 1) * img_w2real_w, (aa[1] + 1) * img_h2real_h) for aa in img_points]
        br_points = [(aa[0] + img_tl_tuple[0], aa[1] + img_tl_tuple[1]) for aa in br_points]

        for i in range(len(tl_points)):
            x1, y1 = int(tl_points[i][0]), int(tl_points[i][1])
            w, h = int(br_points[i][0]) - x1, int(br_points[i][1]) - y1
            self.painter.drawRect(x1, y1, w, h)

        self.painter.setBrush(Qt.NoBrush)

    def get_ann_img(self):
        return self.scaled_img_painted.scaled(self.img.size(), Qt.KeepAspectRatio, self.interpolation).toImage()

    def get_editing_polygon(self):
        editing_i = None

        for i, one in enumerate(self.__all_polygons):
            point = self.cursor_in_widget.toTuple()
            st = one['shape_type']

            if st in shape_type('环形'):
                wp1 = [aa.toTuple() for aa in one['widget_points'][0]]
                wp2 = [aa.toTuple() for aa in one['widget_points'][1]]
                shape_points = [wp1, wp2]
            elif st in shape_type('像素'):
                img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(self.cursor_in_widget)
                point = (img_pixel_x, img_pixel_y)
                shape_points = one['img_points']
            else:
                shape_points = [aa.toTuple() for aa in one['widget_points']]

            if point_in_shape(point, shape_points, st):
                editing_i = i
                break

        return editing_i

    def get_in_border_wp(self, w_p: QPointF) -> QPointF:  # 防止widget_points坐标越界
        b_left, b_up, b_right, b_down = self.get_border_coor()
        in_border_x = min(max(b_left, w_p.x()), b_right)
        in_border_y = min(max(b_up, w_p.y()), b_down)
        return QPointF(in_border_x, in_border_y)

    def get_one_polygon(self, i):
        return deepcopy(self.__all_polygons[i])

    def get_tuple_polygons(self):
        json_polygons = deepcopy(self.__all_polygons)

        if len(json_polygons):
            for one in json_polygons:
                if one['shape_type'] in shape_type('环形'):
                    out_c, in_c = one['widget_points'][0], one['widget_points'][1]
                    widget_points = [[aa.toTuple() for aa in out_c], [aa.toTuple() for aa in in_c]]
                else:
                    widget_points = [aa.toTuple() for aa in one['widget_points']]

                one['widget_points'] = widget_points

        return json_polygons

    def img_size(self):
        return self.img.size().toTuple()

    def prepare_polygons(self, polygons, ori_h, ori_w):
        img_h, img_w = self.img.size().height(), self.img.size().width()
        if ori_h != img_h or ori_w != img_w:
            QMessageBox.critical(self, self.tr('图片尺寸错误'),
                                 self.tr('记录的图片尺寸({}, {}) != 当前的图片尺寸({}, {})。')
                                 .format(ori_w, ori_h, img_w, img_h))
            return

        self.center_point()
        img_w2real_w, img_h2real_h = self.get_widget_to_img_ratio()

        if img_w2real_w is not None:
            for one in polygons:
                if one['shape_type'] in shape_type('环形'):
                    p1 = self.img_coor_to_widget_coor(one['img_points'][0])
                    p2 = self.img_coor_to_widget_coor(one['img_points'][1])
                    ps = [p1, p2]
                elif one['shape_type'] in shape_type(['多边形', '像素']):
                    ps = self.img_coor_to_widget_coor(one['img_points'])
                elif one['shape_type'] in shape_type(['矩形', '椭圆形']):
                    p1 = [one['img_points'][0][0], one['img_points'][0][1]]
                    p2 = [one['img_points'][1][0], one['img_points'][1][1]]
                    ps = self.img_coor_to_widget_coor([p1, p2])

                one['widget_points'] = ps

            self.__all_polygons = polygons
            self.update()

    def modify_polygon_class(self, i, new_class, new_color):
        polygon = self.__all_polygons[i]
        polygon['category'] = new_class
        polygon['qcolor'] = new_color
        self.update()

    def move_pix_img(self):  # 拖曳图片功能
        if self.LeftClick:
            old_img_tl = self.img_tl
            self.img_tl = self.img_tl + self.cursor_in_widget - self.start_pos
            self.start_pos = self.cursor_in_widget
            self.shape_scale_move(old_img_tl)
            self.update()

    def move_polygons(self, key_left=False, key_right=False, key_up=False, key_down=False):  # 标注整体移动功能
        editing_polygon = self.__all_polygons[self.polygon_editing_i]
        widget_points, img_points = editing_polygon['widget_points'], editing_polygon['img_points']
        st = editing_polygon['shape_type']

        offset = None
        img_w, img_h = self.img.width(), self.img.height()
        if key_left:
            if st in shape_type('像素'):
                for i, one_point in enumerate(img_points):
                    one_point[0] -= 1
                    w_p = self.img_coor_to_widget_coor(one_point)
                    widget_points[i] = self.get_in_border_wp(w_p)
            else:
                offset = QPointF(-int(img_w / 300), 0)
        elif key_right:
            if st in shape_type('像素'):
                for i, one_point in enumerate(img_points):
                    one_point[0] += 1
                    w_p = self.img_coor_to_widget_coor(one_point)
                    widget_points[i] = self.get_in_border_wp(w_p)
            else:
                offset = QPointF(int(img_w / 300), 0)
        elif key_up:
            if st in shape_type('像素'):
                for i, one_point in enumerate(img_points):
                    one_point[1] -= 1
                    w_p = self.img_coor_to_widget_coor(one_point)
                    widget_points[i] = self.get_in_border_wp(w_p)
            else:
                offset = QPointF(0, -int(img_h / 300))
        elif key_down:
            if st in shape_type('像素'):
                for i, one_point in enumerate(img_points):
                    one_point[1] += 1
                    w_p = self.img_coor_to_widget_coor(one_point)
                    widget_points[i] = self.get_in_border_wp(w_p)
            else:
                offset = QPointF(0, int(img_h / 300))

        elif self.LeftClick:
            offset = self.cursor_in_widget - self.start_pos

        if offset is not None:
            if st in shape_type('环形'):
                for i, one_wp in enumerate(widget_points):
                    for j, one_point in enumerate(one_wp):
                        one_point += offset
                        one_point = self.get_in_border_wp(one_point)
                        widget_points[i][j] = one_point
                        img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(one_point)
                        if img_pixel_x is not None:
                            img_points[i][j] = [img_pixel_x, img_pixel_y]
            else:
                for i, one_point in enumerate(widget_points):
                    one_point += offset
                    one_point = self.get_in_border_wp(one_point)
                    widget_points[i] = one_point
                    img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(one_point)
                    if img_pixel_x is not None:
                        img_points[i] = [img_pixel_x, img_pixel_y]

            if self.LeftClick:
                self.start_pos = self.cursor_in_widget

        self.update()
        self.MovingPolygon = True

    @staticmethod
    def move_to_new_folder():
        signal_move2new_folder.send(True)

    def one_polygon_done(self, qcolor, category):
        if self.FlagDrawCollection:
            st = self.FlagDrawCollection
            self.FlagDrawCollection = False
        else:
            st = self.shape_type

        if st in shape_type('环形'):
            self.__all_polygons.append({'category': category, 'qcolor': qcolor, 'shape_type': st,
                                        'widget_points': self.widget_points_huan, 'img_points': self.img_points_huan})
            self.clear_widget_img_points_huan()
        else:
            self.__all_polygons.append({'category': category, 'qcolor': qcolor, 'shape_type': st,
                                        'widget_points': self.widget_points, 'img_points': self.img_points})
            self.clear_widget_img_points()

        self.update()

    def remove_widget_img_pair(self):
        if len(self.widget_points):
            self.widget_points.pop()
            self.img_points.pop()
            self.update()

    def reset_cursor(self):
        self.cursor_in_widget = QPointF(-10, -10)

    def select_collection_ok(self, text):
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
            st = polygon['shape_type']
            self.FlagDrawCollection = st
            if st in shape_type('环形'):
                self.widget_points_huan, self.img_points_huan = [], []
                widget_points_out, img_points_out = compute_new_points(polygon['widget_points'][0])
                self.widget_points_huan.append(widget_points_out)
                self.img_points_huan.append(img_points_out)

                add_offset = polygon['widget_points'][1][0] - polygon['widget_points'][0][0]
                widget_points_in, img_points_in = compute_new_points(polygon['widget_points'][1], add_offset=add_offset)
                self.widget_points_huan.append(widget_points_in)
                self.img_points_huan.append(img_points_in)
            else:
                self.widget_points, self.img_points = compute_new_points(polygon['widget_points'])
            signal_one_collection_done.send(polygon['category'])
        else:  # 收藏标注
            if text in self.collected_shapes.keys():
                QMessageBox.warning(self, self.tr('名称重复'), self.tr('{}已存在。').format(text))
            else:
                self.collected_shapes[text] = self.__all_polygons[self.polygon_editing_i]
                self.collection_window.ui.listWidget.addItem(QListWidgetItem(text))
                self.collection_window.ui.lineEdit.setText('')

        self.collection_window.close()

    def set_ann_painted_img(self, path):
        if self.AnnMode:
            self.scaled_img_painted = QPixmap(path).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.scaled_img = self.scaled_img_painted
            self.update()

    def set_focus(self):
        if self.polygon_editing_i is not None or self.corner_index is not None:
            self.setFocus(Qt.OtherFocusReason)
        else:
            self.clearFocus()

    def set_hide_cross(self, hide):
        self.HideCross = hide
        self.reset_cursor()
        self.update()

    def set_shape_locked(self, lock):
        self.PolygonLocked = lock

    def set_task_mode(self, cls=False, m_cls=False, det=False, seg=False):
        self.ClsMode, self.MClsMode, self.DetMode, self.SegMode = cls, m_cls, det, seg
        self.setMouseTracking(True)

        if cls or m_cls:
            self.setCursor(Qt.OpenHandCursor)
        if det or seg:
            self.setCursor(Qt.CrossCursor)

    def set_tool_mode(self, draw=True, shape_edit=False, ann=False):
        self.DrawMode, self.ShapeEditMode, self.AnnMode = draw, shape_edit, ann

        if draw:
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(True)

        if shape_edit:
            self.unsetCursor()
        else:
            self.setCursor(Qt.CrossCursor)
            self.clear_editing_i_corner()

        if ann:
            self.setMouseTracking(False)
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.clear_scaled_img(to_undo=False)

    def shape_done_open_label_window(self):  # 一个标注完成，打开类别列表窗口
        if self.shape_type in shape_type('环形'):
            self.widget_points_huan.append(self.widget_points.copy())
            self.img_points_huan.append(self.img_points.copy())
            if len(self.widget_points_huan) < 2:
                self.clear_widget_img_points()
                self.update()
            else:
                out_c = [aa.toTuple() for aa in self.widget_points_huan[0]]
                for one in self.widget_points_huan[1]:
                    if not point_in_shape(one.toTuple(), out_c, self.tr('多边形')):
                        QMessageBox.warning(self, self.tr('内环越界'), self.tr('内环不完全在外环内部。'))
                        self.widget_points_huan.pop(1)
                        return

                signal_open_label_window.send(True)
        else:
            signal_open_label_window.send(True)

    def shape_scale_move(self, old_img_tl, scale_factor=(1., 1.)):
        for one in self.__all_polygons:
            if one['shape_type'] in shape_type('环形'):
                wp1 = self.shape_scale_convert(one['widget_points'][0], old_img_tl, scale_factor)
                wp2 = self.shape_scale_convert(one['widget_points'][1], old_img_tl, scale_factor)
                one['widget_points'] = [wp1, wp2]
            else:
                one['widget_points'] = self.shape_scale_convert(one['widget_points'], old_img_tl, scale_factor)

        self.widget_points = self.shape_scale_convert(self.widget_points, old_img_tl, scale_factor)

        for i, one in enumerate(self.widget_points_huan):
            moved = self.shape_scale_convert(one, old_img_tl, scale_factor)
            self.widget_points_huan[i] = moved

    def show_collection_window(self, draw):
        if draw:
            self.FlagDrawCollection = True

        self.collection_window.show()

    def show_menu(self):  # 在鼠标位置显示菜单
        if self.polygon_editing_i is None:
            self.draw_collection_shape.setDisabled(not (self.DetMode or self.SegMode))
            self.img_menu.exec(QCursor.pos())
        else:
            self.shape_menu.exec(QCursor.pos())

    def show_tag_window(self):
        self.tag_window.show()


class CenterImgView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.img_area = CenterImg(self)
        self.img_area.paint_img('images/bg.png')

        self.scene = QGraphicsScene(self)
        self.bookmark = QGraphicsPixmapItem()
        self.bookmark.setPixmap(QPixmap('images/bookmark/bookmark_red.png').scaled(48, 48))
        self.bookmark.setFlags(QGraphicsItem.ItemIsMovable)
        self.bookmark.setPos(0, -5)
        self.bookmark.setVisible(False)
        self.scene.addItem(self.bookmark)
        self.setScene(self.scene)

    def adjust_area(self):  # 窗口大小改变时，图片大小也随着改变
        view_w, view_h = self.size().toTuple()
        self.scene.setSceneRect(0, 0, view_w, view_h)
        self.img_area.resize(view_w, view_h)
        self.img_area.mouseDoubleClickEvent(None, True)

    def bm_active_area(self):
        if self.bookmark.isVisible():
            tl = self.bookmark.pos() + QPoint(12, 0)
            br = self.bookmark.pos() + QPoint(40, 40)
            return tl.toTuple(), br.toTuple()
        else:
            return (-10, -10), (-10, -10)

    def moving_bookmark(self, offset: QPoint):
        self.bookmark.setPos(self.bookmark.pos() + offset)

    def moved_bookmark(self):
        x, y = self.bookmark.pos().toTuple()
        view_w, view_h = self.size().toTuple()
        new_x = min(max(-10, x), view_w - 40)
        new_y = min(max(-5, y), view_h - 50)
        if y < 10:
            new_y = -5
        self.bookmark.setPos(new_x, new_y)

    def show_bookmark(self):
        self.bookmark.setVisible(not self.bookmark.isVisible())
