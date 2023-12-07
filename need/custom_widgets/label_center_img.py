#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
from typing import List, Union
from copy import deepcopy
from PySide6.QtWidgets import QInputDialog, QMessageBox, QApplication, QMenu, QListWidgetItem, QLabel, QGraphicsView, \
    QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QPushButton, QFileDialog
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QSize
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QPen, QUndoStack, QCursor, QAction, QIcon
from need.algorithms import point_in_shape
from need.utils import AnnUndo, INS_shape_type
from need.custom_signals import *
from need.custom_widgets import SelectItem, signal_select_window_close, CustomMessageBox
from need.functions import get_HHL_parent
from need.SharedWidgetStatFlags import stat_flags

signal_draw_shape_done = BoolSignal()
signal_one_collection_done = StrSignal()
signal_select_collection_ok = StrSignal()
signal_draw_selected_shape = IntSignal()
signal_set_shape_list_selected = IntSignal()
signal_shape_info_update = IntSignal()


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

        pixel_cursor = QPixmap('images/color_cursor.png').scaled(16, 16, mode=Qt.SmoothTransformation)
        self.pixel_cursor = QCursor(pixel_cursor, 0, pixel_cursor.height())

        self.img_menu = QMenu('img_menu', self)
        self.img_menu.setFixedWidth(135)
        self.action_bilinear = QAction(self.tr('双线性插值缩放'), self)
        self.action_bilinear.triggered.connect(self.set_interpolation)
        self.action_nearest = QAction(QIcon('images/icon_11.png'), self.tr('最近邻插值缩放'), self)
        self.action_nearest.triggered.connect(self.set_interpolation)
        self.action_to_100 = QAction(QIcon('images/to_100.png'), self.tr('缩放至100%尺寸'), self)
        self.action_to_100.triggered.connect(self.to_100_size)
        self.action_pixel_cursor = QAction(self.tr('像素指针'), self)
        self.action_pixel_cursor.triggered.connect(self.set_pixel_cursor)
        self.action_to_file_path = QAction(QIcon('images/file_folder/open_file.png'), self.tr('打开图片所在路径'), self)
        self.action_to_file_path.triggered.connect(self.open_file_path)
        self.img_menu.addAction(self.action_nearest)
        self.img_menu.addAction(self.action_bilinear)
        self.img_menu.addAction(self.action_to_100)
        self.img_menu.addAction(self.action_pixel_cursor)
        self.img_menu.addAction(self.action_to_file_path)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__show_menu)

        self.img, self.scaled_img = None, None
        self.img_path = ''
        self.img_tl = QPointF(0., 0.)  # 图片左上角在控件坐标系的坐标
        self.cursor_in_widget = QPoint(0, 0)
        self.start_pos = None
        self.bm_start = None
        self.mouse_event_pos = None  # 记录鼠标在窗口坐标系的坐标
        self.interpolation = Qt.FastTransformation
        self.setCursor(Qt.OpenHandCursor)

        self.LeftClick = False  # 用于图片拖曳和标注拖曳功能中，判断左键是否按下

        self.signal_xy_color2ui = ListSignal()
        self.signal_img_size2ui = TupleSignal()
        self.signal_img_time2ui = StrSignal()

    def contextMenuEvent(self, event):
        self.img_menu.exec(self.mapToGlobal(event.pos()))

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

        self.__move_pix_img()

    def mousePressEvent(self, e):
        self.__set_cursor(press=True)

        if e.button() == Qt.LeftButton:
            self.LeftClick = True
            self.start_pos = e.position()
        elif e.button() == Qt.RightButton:
            self.mouse_event_pos = e.position()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.LeftClick = False

        self.__set_cursor(release=True)

    def paintEvent(self, e):  # 程序调用show()之后就会调用此函数
        self.painter.begin(self)
        self.painter.drawPixmap(self.img_tl, self.scaled_img)
        self.painter.end()

    def wheelEvent(self, e):
        if self.is_bg():
            return

        cur_img_w, cur_img_h = self.scaled_img.size().toTuple()
        if cur_img_w * cur_img_h > 16000 * 16000:
            size_info = CustomMessageBox('warning', self.tr('图片缩放过大'), hide_dsa=False)
            size_info.show(
                self.tr(f'图片缩放过大(总面积需<16000 * 16000像素），程序将占用较多内存，图片的显示也会较为耗时，请留意。'))

        scale_ratio = 0.95
        if e.angleDelta().y() < 0:  # 缩小
            pass
        elif e.angleDelta().y() > 0:  # 放大
            img_w2real_w, img_h2real_h = self.get_widget_to_img_ratio()
            if img_w2real_w is not None and img_h2real_h is not None and img_w2real_w > 16 and img_h2real_h > 16:
                return

            scale_ratio = 1 / scale_ratio

        self.__scale_img(e.position(), scale_ratio)

    def __move_pix_img(self):  # 拖曳图片功能
        if self.LeftClick:
            self.img_tl = self.img_tl + self.cursor_in_widget - self.start_pos
            self.start_pos = self.cursor_in_widget
        self.update()

    def __scale_img(self, mouse_event_pos, scale_ratio):
        if self.is_bg():
            return

        ex, ey = mouse_event_pos.x(), mouse_event_pos.y()
        old_img_w, old_img_h = self.scaled_img.width(), self.scaled_img.height()
        old_x, old_y = self.img_tl.x(), self.img_tl.y()
        cur_center_x, cur_center_y = old_x + old_img_w / 2, old_y + old_img_h / 2
        offset_x, offset_y = (ex - cur_center_x) / old_img_w, (ey - cur_center_y) / old_img_h

        if scale_ratio == 1:
            self.scaled_img = self.img
        else:
            self.scaled_img = self.img.scaled(int(old_img_w * scale_ratio), int(old_img_h * scale_ratio),
                                              Qt.KeepAspectRatio, self.interpolation)

        new_img_w, new_img_h = self.scaled_img.width(), self.scaled_img.height()

        new_img_x = (1 / 2 + offset_x) * (old_img_w - new_img_w) + old_x
        new_img_y = (1 / 2 + offset_y) * (old_img_h - new_img_h) + old_y
        self.img_tl = QPointF(new_img_x, new_img_y)

        self.signal_img_size2ui.send(self.scaled_img.size().toTuple())
        self.update()

    def __set_cursor(self, press=False, moving=False, release=False):
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

    def __show_menu(self):  # 在鼠标位置显示菜单
        self.img_menu.exec(QCursor.pos())

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
        ori_w, ori_h = self.img.size().width(), self.img.size().height()

        if ori_w and ori_h:
            img_w, img_h = self.scaled_img.size().width(), self.scaled_img.size().height()
            img_h2real_h = img_h / ori_h
            img_w2real_w = img_w / ori_w
            return img_w2real_w, img_h2real_h
        else:
            return None, None

    def is_bg(self):
        return self.img_path == 'images/bg.png'

    def open_file_path(self):
        if not self.is_bg():
            QFileDialog(self).getOpenFileName(self, dir=self.img_path)

    def ori_img_size(self) -> tuple:
        return self.img.size().toTuple()

    def paint_img(self, img_path_or_pix_map, img_path='', re_center=True, img_info_update=True):
        if img_path_or_pix_map is None:  # 有时候是None，原因未知
            return
        if img_info_update:
            assert img_path, 'img_path is None.'

        self.img_path = img_path
        self.img = QPixmap(img_path_or_pix_map)  # self.img始终保持为原图

        if re_center:
            if self.is_bg():
                self.scaled_img = self.img.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self.scaled_img = self.img.scaled(self.size(), Qt.KeepAspectRatio, self.interpolation)

            self.center_point()
        else:
            self.scaled_img = self.img.scaled(self.scaled_img.size(), Qt.KeepAspectRatio, self.interpolation)

        self.update()

        if img_info_update and not self.is_bg():
            self.signal_img_size2ui.send(self.scaled_img.size().toTuple())
            self.signal_img_time2ui.send(self.img_path)

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
                self.__set_cursor()
            else:
                self.action_pixel_cursor.setIcon(QIcon())
                self.__set_cursor()

    def shape_scale_convert(self, points, old_img_tl, scale_factor):
        new_points = []
        for one_p in points:
            x0_in_img, y0_in_img = one_p.x() - old_img_tl.x(), one_p.y() - old_img_tl.y()
            new_p = QPointF(x0_in_img * scale_factor[0], y0_in_img * scale_factor[1])
            new_p = new_p + self.img_tl
            new_points.append(new_p)

        return new_points

    def to_100_size(self):
        self.__scale_img(self.mouse_event_pos, 1)

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


class CenterImg(BaseImgFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.collection_window = SelectItem(title=self.tr('收藏标注'), button_signal=signal_select_collection_ok)
        pencil = QPixmap('images/pencil.png').scaled(24, 24, mode=Qt.SmoothTransformation)
        self.pencil_cursor = QCursor(pencil, 0, pencil.height())

        self.cross_color = QColor(190, 0, 0)
        self.seg_pen_size = 2
        self.seg_pen_color = QColor('red')
        self.ann_pen_size = 3
        self.ann_pen_color = QColor('red')
        self.ann_font_size = 20
        self.ann_font_color = QColor('white')

        self.__all_shapes = []
        self.widget_points = []
        self.img_points = []
        # self.__shape_temp = {'classes': [], 'tags': [], 'qcolor': QColor('red'),
        #                      'shape_type': '', 'sub_shapes': [], 'combo': []}
        self.__shape_temp = []
        self.shape_type = self.tr('多边形')
        self.cursor_in_widget = QPointF(0., 0.)  # 鼠标在控件坐标系的实时坐标
        self.scaled_img_painted = None
        self.editing_shape_i = None  # 正在编辑的标注的索引，即标注高亮时对应的索引
        self.collected_shapes = {}
        self.ann_point_last = QPoint(0, 0)
        self.ann_point_cur = QPoint(0, 0)
        self.img_tl = QPointF(0., 0.)  # 图片左上角在控件坐标系的坐标
        self.scale_factor = (0., 0.)  # 图片伸缩因子
        self.offset = QPointF(0., 0.)  # 图片移动偏移量
        self.corner_index = None  # 标注角点的索引
        self.start_pos = None  # 左键按下时的控件坐标系坐标
        self.interpolation = Qt.FastTransformation

        self.DrawMode = True
        self.ShapeEditMode = False
        self.AnnMode = False
        self.LeftClick = False  # 用于实现图片拖曳和标注拖曳功能
        self.PolygonLastPointDone = False  # 用于标识画完一个多边形
        self.SelectingCateTag = False
        self.PolygonLocked = False
        self.HideCross = True
        self.MovingShape = False  # 仅在拖动标注移动时为True
        self.MovingCorner = False
        self.FlagDrawCollection = False
        self.ShowOriImg = False

        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(30)
        self.addAction(self.undo_stack.createUndoAction(self, "Undo"))

        self.draw_collection_shape = QAction(self.tr('绘制收藏的标注'), self)
        self.draw_collection_shape.setIcon(QIcon('images/draw.png'))
        self.draw_collection_shape.triggered.connect(lambda: self.__show_collection_window(True))
        self.draw_collection_shape.setDisabled(True)
        self.action_move2folder = QAction(self.tr('移动至新文件夹'), self)
        self.action_move2folder.setIcon(QIcon('images/move_to.png'))
        self.action_move2folder.triggered.connect(self.__move_to_new_folder)
        self.img_menu.addAction(self.draw_collection_shape)
        self.img_menu.addAction(self.action_move2folder)

        self.shape_menu = QMenu('shape_menu', self)
        self.action_add_collection = QAction(self.tr('收藏标注'), self)
        self.action_add_collection.setIcon(QIcon('images/favorite.png'))
        self.action_add_collection.triggered.connect(lambda: self.__show_collection_window(False))
        self.shape_menu.addAction(self.action_add_collection)

        self.button_show_ori = QPushButton(self)
        self.button_show_ori.setIconSize(QSize(14, 14))
        self.button_show_ori.setIcon(QIcon('images/look/look2.png'))
        self.button_show_ori.setStyleSheet('QPushButton {background-color: rgb(235, 235, 235, 0.7); '
                                           'border: 1px solid gray; border-radius: 4px;}'
                                           'QPushButton:hover {background-color:  rgb(225, 225, 225);}'
                                           'QPushButton:pressed {background-color:  rgb(215, 215, 215);}')
        self.button_show_ori.resize(22, 22)
        self.button_show_ori.setToolTip(self.tr('屏蔽标注'))
        self.button_show_ori.clicked.connect(self.__ori_img_show)

        signal_draw_selected_shape.signal.connect(self.__draw_selected_shape)
        # signal_select_window_close.signal.connect(self.__clear_widget_img_points)
        signal_select_collection_ok.signal.connect(self.__select_collection_ok)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.split('.')[-1] in ('jpg', 'jpeg', 'png', 'bmp'):
                get_HHL_parent(self).new_img_window(file_path)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.focus_set_img_area(ctrl_release=True)

    def keyPressEvent(self, event):
        if self.is_bg():
            return

        key = event.key()
        # 判断Ctrl是否按下，与event.key() == Qt.Key_Control不同，仅按Ctrl进入keyPressEvent后，无法同时使其为真
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if key == Qt.Key_Z:
                if self.AnnMode:
                    self.undo_stack.undo()
                else:
                    if not self.SelectingCateTag:
                        self.__remove_widget_img_pair()
        else:
            if key in (Qt.Key_A, Qt.Key_D, Qt.Key_W, Qt.Key_S):
                if self.corner_index is None and self.editing_shape_i is not None:
                    self.__move_polygons(key=key)
                else:  # 此时在尝试切图
                    if not get_HHL_parent(self).check_warnings('selecting_cate_tag'):
                        return

            if key == Qt.Key_Delete:
                self.del_polygons()
            if key == Qt.Key_Shift:
                self.__set_cursor(shift=True)

            if self.MovingShape:
                signal_shape_info_update.send(self.editing_shape_i)
                self.MovingShape = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.button_show_ori.move(self.width() - 22, 3)

    def mouseDoubleClickEvent(self, e):  # 同时触发 mousePressEvent()
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if self.AnnMode:
                self.__ann_add_text(e.position())
        else:
            if self.scaled_img is not None:
                if self.AnnMode and self.scaled_img_painted is not None:
                    action_img = self.scaled_img_painted
                else:
                    action_img = self.img

                old_img_tl = self.img_tl
                old_img_w, old_img_h = self.scaled_img.width(), self.scaled_img.height()

                if self.is_bg():
                    self.scaled_img = action_img.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.center_point()
                else:
                    self.scaled_img = action_img.scaled(self.size(), Qt.KeepAspectRatio, self.interpolation)
                    self.center_point()
                    scale_factor = (self.scaled_img.width() / old_img_w, self.scaled_img.height() / old_img_h)
                    self.__shape_scale_move(old_img_tl, scale_factor)
                    self.signal_img_size2ui.send(self.scaled_img.size().toTuple())

                self.update()

    def mouseMoveEvent(self, e):
        self.focus_set_img_area(moving=True)
        self.cursor_in_widget = e.position()  # 相当于self.mapFromGlobal(e.globalPosition())

        if self.bm_start is not None:
            self.parent().moving_bookmark(self.cursor_in_widget - self.bm_start)
            self.bm_start = self.cursor_in_widget
        else:
            img_pixel_x, img_pixel_y, qcolor = self.widget_coor_to_img_coor(self.cursor_in_widget)
            if img_pixel_x is not None:  # 实时显示坐标，像素值
                self.signal_xy_color2ui.send([img_pixel_x, img_pixel_y, qcolor.red(), qcolor.green(), qcolor.blue()])

            if self.AnnMode:
                if QApplication.keyboardModifiers() == Qt.ControlModifier:
                    self.__ann_draw()
                else:
                    self.__move_pix_img()
            else:
                self.update()

                if QApplication.keyboardModifiers() == Qt.ControlModifier:
                    if self.shape_type in INS_shape_type('像素') and len(self.img_points) and not self.SelectingCateTag:
                        self.__add_widget_img_pair(self.cursor_in_widget)  # 添加像素点坐标
                else:
                    if self.ShapeEditMode:
                        if QApplication.keyboardModifiers() != Qt.ShiftModifier:
                            # 有了self.polygon_editing_i后，在paintEvent()里触发draw_editing_polygon()才有效
                            if not self.MovingShape and not self.PolygonLocked:
                                self.editing_shape_i = self.__get_editing_polygon()

                            if self.LeftClick:
                                if not self.MovingShape and self.corner_index is not None:
                                    self.__corner_point_move(self.corner_index)  # 角点移动功能先于标注移动功能
                                elif self.editing_shape_i is not None:
                                    self.__move_polygons()
                                else:
                                    self.__move_pix_img()
                            else:
                                self.update()  # 为了触发draw_editing_polygon()
                    else:
                        self.__move_pix_img()

    def mousePressEvent(self, e):
        if self.is_bg():
            return

        self.__set_cursor(press=True)

        e_pos = e.pos().toTuple()
        bm_tl, bm_br = self.parent().bm_active_area()
        if bm_tl[0] < e_pos[0] < bm_br[0] and bm_tl[1] < e_pos[1] < bm_br[1]:  # 书签移到功能
            self.bm_start = e.pos()
        else:
            if QApplication.keyboardModifiers() == Qt.ControlModifier:
                if self.AnnMode:
                    self.ann_point_cur = e.position() - self.img_tl
                    self.ann_point_last = self.ann_point_cur

                    command = AnnUndo(self, self.scaled_img.copy())
                    self.undo_stack.push(command)  # 添加command用于撤销功能
                else:
                    if self.PolygonLastPointDone:
                        self.__one_shape_drawed()
                    else:
                        self.cursor_in_widget = e.position()
                        self.__add_widget_img_pair(self.cursor_in_widget)
            else:
                if e.button() == Qt.LeftButton:
                    self.LeftClick = True
                    self.start_pos = e.position()
                elif e.button() == Qt.RightButton:
                    self.mouse_event_pos = e.position()

    def mouseReleaseEvent(self, e):
        if self.is_bg():
            return

        self.__set_cursor(release=True)

        if self.bm_start is not None:
            self.parent().moved_bookmark()
            self.bm_start = None
        if self.MovingShape:
            signal_shape_info_update.send(self.editing_shape_i)
            self.MovingShape = False
        if type(self.MovingCorner) == int:
            signal_shape_info_update.send(self.MovingCorner)
            self.MovingCorner = False
        if e.button() == Qt.LeftButton:
            self.LeftClick = False

        if not self.ShowOriImg:
            if QApplication.keyboardModifiers() == Qt.ControlModifier:
                if self.shape_type in INS_shape_type(['矩形', '椭圆形']):
                    point_br = e.position()
                    b_left, b_up, b_right, b_down = self.get_border_coor()
                    if b_left <= point_br.x() <= b_right and b_up <= point_br.y() <= b_down:
                        if len(self.widget_points):
                            self.__add_widget_img_pair(point_br)

                            if len(self.widget_points) in (0, 3):  # 一些误操作导致长度错误，直接清空重画
                                self.__clear_widget_img_points()
                            else:
                                self.__one_shape_drawed()
                    else:
                        self.__clear_widget_img_points()
                elif self.shape_type in INS_shape_type('像素'):
                    if len(self.widget_points):
                        self.__one_shape_drawed()
            elif QApplication.keyboardModifiers() == Qt.ShiftModifier and self.ShapeEditMode:
                self.__erase_paint_pixel(self.editing_shape_i)
                signal_shape_info_update.send(self.editing_shape_i)

    def paintEvent(self, e):  # 时刻都在绘制，关注绘制数量多时，是否会造成系统负担
        self.painter.begin(self)
        self.painter.drawPixmap(self.img_tl, self.scaled_img)

        if self.ShowOriImg:
            self.painter.end()
            return

        self.PolygonLastPointDone = False
        self.__draw_completed_shapes()
        # self.draw_temp_shape()

        if self.ShapeEditMode:
            self.corner_index = self.__cursor_close_to_corner()
            self.__draw_editing_polygon()

        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if not self.HideCross:  # 画十字线
                self.painter.setPen(QPen(self.cross_color, 1, Qt.DashLine))
                x, y = self.cursor_in_widget.toTuple()
                self.painter.drawLine(0, y, 5000, y)
                self.painter.drawLine(x, 0, x, 5000)

            if len(self.widget_points):
                self.painter.setPen(QPen(self.seg_pen_color, self.seg_pen_size))
                if self.shape_type in INS_shape_type(['矩形', '椭圆形']):
                    if len(self.widget_points) in (0, 3):  # 一些误操作导致长度错误，直接清空重画
                        self.__clear_widget_img_points()
                    else:
                        if len(self.widget_points) == 2:
                            x1, y1 = self.widget_points[0].toTuple()
                            x2, y2 = self.widget_points[1].toTuple()
                        elif len(self.widget_points) == 1:
                            x1, y1 = self.widget_points[0].toTuple()
                            x2, y2 = self.cursor_in_widget.toTuple()

                        if self.shape_type in INS_shape_type('矩形'):
                            self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                        elif self.shape_type in INS_shape_type('椭圆形'):
                            self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))

                elif self.shape_type in INS_shape_type('多边形'):
                    if not self.SelectingCateTag:
                        if len(self.widget_points) >= 2:  # 画已完成的完整线段
                            for i in range(len(self.widget_points) - 1):
                                self.painter.drawLine(self.widget_points[i], self.widget_points[i + 1])
                        if len(self.widget_points):  # 画最后一个点到鼠标的线段
                            self.painter.drawLine(self.widget_points[-1], self.cursor_in_widget)

                    if len(self.widget_points) >= 3:  # 至少3个点才能绘制出polygon
                        if self.__close_to_corner(self.widget_points[0]):  # 判定是否到了第一个点
                            self.PolygonLastPointDone = True

                elif self.shape_type in INS_shape_type('像素'):
                    self.__fill_img_pixel(self.img_points, self.seg_pen_color)

        self.painter.end()

    def __add_widget_img_pair(self, qpointf):
        if self.ShowOriImg:
            return

        if self.SelectingCateTag:
            get_HHL_parent(self).check_warnings('selecting_cate_tag')
            return

        img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(qpointf)

        if img_pixel_x is not None:
            img_p = [img_pixel_x, img_pixel_y]
            if self.shape_type in INS_shape_type(['多边形', '矩形', '椭圆形']):
                self.img_points.append(img_p)
                self.widget_points.append(qpointf)
            elif self.shape_type in INS_shape_type('像素'):
                if img_p not in self.img_points:
                    self.img_points.append(img_p)
                    self.widget_points.append(self.img_coor_to_widget_coor(img_p))  # 计算精确的像素的左上角的widget坐标
            elif self.shape_type in INS_shape_type(['组合']):
                pass

            self.update()

    def __ann_add_text(self, ori_position):  # 注释模式添加文字功能
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

    def __ann_draw(self):  # 注释模式涂鸦功能
        self.ann_point_cur = self.cursor_in_widget - self.img_tl  # 绘图的坐标系应为图片坐标系
        self.painter.begin(self.scaled_img)
        self.painter.setPen(QPen(self.ann_pen_color, self.ann_pen_size))
        self.painter.drawLine(self.ann_point_last, self.ann_point_cur)
        self.painter.end()
        self.update()
        self.ann_point_last = self.ann_point_cur
        self.scaled_img_painted = self.scaled_img.copy()  # 保存一个绘图的副本

    def __clear_editing_i_corner(self):
        self.editing_shape_i = None
        self.corner_index = None

    def __clear_widget_img_points(self):
        self.widget_points = []
        self.img_points = []

    def __close_to_corner(self, points, radius=3, is_ellipse=False):
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

    def __corner_point_move(self, corner_index):  # 标注角点的拖动功能
        offset = self.cursor_in_widget - self.start_pos
        if type(corner_index) == int:
            i = corner_index
        elif len(corner_index) == 2:
            i, j = corner_index
        elif len(corner_index) == 3:
            i, j, k = corner_index

        if self.PolygonLocked:
            if i != self.editing_shape_i:
                return

        b_left, b_up, b_right, b_down = self.get_border_coor()
        polygon = self.__all_shapes[i]

        if polygon['shape_type'] in INS_shape_type('像素'):  # 像素标注不具备这个功能
            return

        # 处理widget_points
        # if polygon['shape_type'] in INS_shape_type('组合'):
        #     new_x, new_y = (polygon['widget_points'][j][k] + offset).toTuple()
        #     new_x, new_y = min(max(new_x, b_left), b_right), min(max(new_y, b_up), b_down)
        #     polygon['widget_points'][j][k] = QPointF(new_x, new_y)
        # else:
        new_x, new_y = (polygon['widget_points'][j] + offset).toTuple()
        new_x, new_y = min(max(new_x, b_left), b_right), min(max(new_y, b_up), b_down)
        polygon['widget_points'][j] = QPointF(new_x, new_y)

        # 处理对应的img_points
        if polygon['shape_type'] in INS_shape_type('多边形'):
            x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][j])
            if x is not None:
                polygon['img_points'][j] = (x, y)
        elif polygon['shape_type'] in INS_shape_type(['矩形', '椭圆形']):
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
        # elif polygon['shape_type'] in INS_shape_type('组合'):
        #     x, y, _ = self.widget_coor_to_img_coor(polygon['widget_points'][j][k])
        #     if x is not None:
        #         polygon['img_points'][j][k] = (x, y)

        self.start_pos = self.cursor_in_widget
        self.update()
        self.MovingCorner = i

    def __cursor_close_to_corner(self):
        if self.MovingShape:
            return

        corner_index = None

        for i, polygon in enumerate(self.__all_shapes):
            if polygon['shape_type'] in INS_shape_type('组合'):
                pass
                # for j, huan in enumerate(polygon['widget_points']):
                #     for k, point in enumerate(huan):
                #         if self.close_to_corner(point):
                #             corner_index = (i, j, k)
                #             return corner_index
            elif polygon['shape_type'] in INS_shape_type('像素'):
                pass
            else:
                for j, point in enumerate(polygon['widget_points']):
                    if polygon['shape_type'] in INS_shape_type('椭圆形'):
                        p_i = self.__close_to_corner(polygon['widget_points'], is_ellipse=True)
                        if type(p_i) == int:
                            corner_index = (i, p_i)
                            return corner_index
                    else:
                        if self.__close_to_corner(point):
                            corner_index = (i, j)
                            return corner_index
        return corner_index

    def __draw_editing_polygon(self):  # 画正在编辑中的polygon
        if self.__all_shapes and self.corner_index is None and self.editing_shape_i is not None:
            self.painter.setPen(Qt.NoPen)
            self.painter.setBrush(QColor(0, 255, 0, 150))
            editing_poly = self.__all_shapes[self.editing_shape_i]

            st = editing_poly['shape_type']
            if st in INS_shape_type(['矩形', '椭圆形']):
                x1, y1 = editing_poly['widget_points'][0].toTuple()
                x2, y2 = editing_poly['widget_points'][1].toTuple()
                if st in INS_shape_type('矩形'):
                    self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                elif st in INS_shape_type('椭圆形'):
                    self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
            elif st in INS_shape_type('多边形'):
                self.painter.drawPolygon(editing_poly['widget_points'])
            elif st in INS_shape_type('像素'):
                self.__fill_img_pixel(editing_poly['img_points'], QColor(0, 255, 0, 150))
            # elif st in INS_shape_type('组合'):
            #     polygon1 = QPolygon([aa.toPoint() for aa in editing_poly['widget_points'][0]])
            #     polygon2 = QPolygon([aa.toPoint() for aa in editing_poly['widget_points'][1]])
            #     self.r1, self.r2 = QRegion(polygon1), QRegion(polygon2)
            #     self.painter.setClipRegion(self.r1 - self.r2)
            #     self.painter.fillRect(self.r1.boundingRect(), QColor(0, 255, 0, 150))

            signal_set_shape_list_selected.send(self.editing_shape_i)

    def __draw_one_shape(self, shape, qcolor):
        st = shape['shape_type']
        if st in INS_shape_type('多边形'):
            self.painter.drawPolygon(shape['widget_points'])
        elif st in INS_shape_type(['矩形', '椭圆形']):
            if len(shape['widget_points']):
                x1, y1 = shape['widget_points'][0].toTuple()
                x2, y2 = shape['widget_points'][1].toTuple()
                if st in INS_shape_type('矩形'):
                    self.painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                elif st in INS_shape_type('椭圆形'):
                    self.painter.drawEllipse(QRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
        elif st in INS_shape_type('像素'):
            self.__fill_img_pixel(shape['img_points'], qcolor)

    def __draw_completed_shapes(self):  # 在标注时画已完成和待完成的完整图形
        for one in self.__all_shapes:
            self.painter.setPen(QPen(QColor(one['qcolor']), self.seg_pen_size))
            self.__draw_one_shape(one, QColor(one['qcolor']))

        if self.SelectingCateTag:
            assert len(self.__shape_temp) > 0, 'Error, no shape in self.shape_temp.'

            for one in self.__shape_temp:
                self.painter.setPen(QPen(self.seg_pen_color, self.seg_pen_size))
                self.__draw_one_shape(one, self.seg_pen_color)

    def __draw_selected_shape(self, i):
        if self.ShapeEditMode:
            self.editing_shape_i = i
            self.update()

    def __erase_paint_pixel(self, fill_index):
        if fill_index is not None:
            x, y, _ = self.widget_coor_to_img_coor(self.cursor_in_widget)
            new_p = [x, y]
            img_points = self.__all_shapes[fill_index]['img_points']
            widget_points = self.__all_shapes[fill_index]['widget_points']

            if new_p in img_points:
                index = img_points.index(new_p)
                img_points.pop(index)
                widget_points.pop(index)
            else:
                img_points.append(new_p)
                widget_points.append(self.img_coor_to_widget_coor(new_p))

            self.update()

    def __fill_img_pixel(self, img_points, qcolor=None):
        if qcolor is not None:
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
            self.painter.drawRect(x1 + 2, y1 + 2, w - 2, h - 2)

        self.painter.setBrush(Qt.NoBrush)

    def __get_editing_polygon(self):
        editing_i = None

        for i, one in enumerate(self.__all_shapes):
            point = self.cursor_in_widget.toTuple()
            st = one['shape_type']

            if st in INS_shape_type('组合'):
                pass
                # wp1 = [aa.toTuple() for aa in one['widget_points'][0]]
                # wp2 = [aa.toTuple() for aa in one['widget_points'][1]]
                # shape_points = [wp1, wp2]
            elif st in INS_shape_type('像素'):
                img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(self.cursor_in_widget)
                point = (img_pixel_x, img_pixel_y)
                shape_points = one['img_points']
            else:
                shape_points = [aa.toTuple() for aa in one['widget_points']]

            if point_in_shape(point, shape_points, st):
                editing_i = i
                break

        return editing_i

    def __get_in_border_widget_coors(self, w_p: QPointF) -> QPointF:  # 防止widget_coors坐标越界
        b_left, b_up, b_right, b_down = self.get_border_coor()
        in_border_x = min(max(b_left, w_p.x()), b_right)
        in_border_y = min(max(b_up, w_p.y()), b_down)
        return QPointF(in_border_x, in_border_y)

    def __move_pix_img(self):  # 拖曳图片功能
        if self.LeftClick:
            old_img_tl = self.img_tl
            self.img_tl = self.img_tl + self.cursor_in_widget - self.start_pos
            self.start_pos = self.cursor_in_widget
            self.__shape_scale_move(old_img_tl)
            self.update()

    def __move_polygons(self, key=None):  # 标注整体移动功能
        editing_polygon = self.__all_shapes[self.editing_shape_i]
        widget_points, img_points = editing_polygon['widget_points'], editing_polygon['img_points']
        st = editing_polygon['shape_type']

        offset = None
        offset_screen_pixel = 1
        if self.LeftClick:
            offset = self.cursor_in_widget - self.start_pos
        else:
            if st in INS_shape_type('像素'):
                for i, one_point in enumerate(img_points):
                    if key == Qt.Key_A:
                        one_point[0] -= 1
                    elif key == Qt.Key_D:
                        one_point[0] += 1
                    elif key == Qt.Key_W:
                        one_point[1] -= 1
                    elif key == Qt.Key_S:
                        one_point[1] += 1

                    w_p = self.img_coor_to_widget_coor(one_point)
                    widget_points[i] = self.__get_in_border_widget_coors(w_p)
            else:
                if key == Qt.Key_A:
                    offset = QPointF(-offset_screen_pixel, 0)
                elif key == Qt.Key_D:
                    offset = QPointF(offset_screen_pixel, 0)
                elif key == Qt.Key_W:
                    offset = QPointF(0, -offset_screen_pixel)
                elif key == Qt.Key_S:
                    offset = QPointF(0, offset_screen_pixel)

        if offset is not None:
            if st in INS_shape_type('组合'):
                for i, one_wp in enumerate(widget_points):
                    for j, one_point in enumerate(one_wp):
                        one_point += offset
                        one_point = self.__get_in_border_widget_coors(one_point)
                        widget_points[i][j] = one_point
                        img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(one_point)
                        if img_pixel_x is not None:
                            img_points[i][j] = [img_pixel_x, img_pixel_y]
            else:
                for i, one_point in enumerate(widget_points):
                    one_point += offset
                    one_point = self.__get_in_border_widget_coors(one_point)
                    widget_points[i] = one_point
                    img_pixel_x, img_pixel_y, _ = self.widget_coor_to_img_coor(one_point)
                    if img_pixel_x is not None:
                        img_points[i] = [img_pixel_x, img_pixel_y]

            if self.LeftClick:
                self.start_pos = self.cursor_in_widget

        self.update()
        self.MovingShape = True

    def __move_to_new_folder(self):
        get_HHL_parent(self).move_to_new_folder()

    def __one_shape_drawed(self):
        self.__shape_temp.append({'name': '', 'shape_type': self.shape_type,
                                  'widget_points': self.widget_points.copy(), 'img_points': self.img_points.copy()})
        if stat_flags.ShapeCombo_IsOpened:
            pass
        else:
            get_HHL_parent(self).select_cate_tag_before()
            self.SelectingCateTag = True
            signal_draw_shape_done.send(True)

    def __ori_img_show(self):
        self.ShowOriImg = not self.ShowOriImg
        if self.ShowOriImg:
            self.button_show_ori.setIcon(QIcon('images/look/not_look2.png'))
            self.button_show_ori.setToolTip(self.tr('显示标注'))
        else:
            self.button_show_ori.setIcon(QIcon('images/look/look2.png'))
            self.button_show_ori.setToolTip(self.tr('屏蔽标注'))

        self.update()

    def __remove_widget_img_pair(self):
        if len(self.widget_points):
            self.widget_points.pop()
            self.img_points.pop()
            self.update()

    def __scale_img(self, mouse_event_pos, scale_ratio):
        if self.is_bg():
            return
        if self.editing_shape_i is not None:
            return

        ex, ey = mouse_event_pos.x(), mouse_event_pos.y()
        old_img_w, old_img_h = self.scaled_img.width(), self.scaled_img.height()
        old_x, old_y = self.img_tl.x(), self.img_tl.y()
        cur_center_x, cur_center_y = old_x + old_img_w / 2, old_y + old_img_h / 2
        offset_x, offset_y = (ex - cur_center_x) / old_img_w, (ey - cur_center_y) / old_img_h

        if self.AnnMode and self.scaled_img_painted is not None:
            action_img = self.scaled_img_painted
        else:
            action_img = self.img

        if scale_ratio == 1:
            self.scaled_img = action_img
        else:
            self.scaled_img = action_img.scaled(int(old_img_w * scale_ratio), int(old_img_h * scale_ratio),
                                                Qt.KeepAspectRatio, self.interpolation)

        new_img_w, new_img_h = self.scaled_img.width(), self.scaled_img.height()

        new_img_x = (1 / 2 + offset_x) * (old_img_w - new_img_w) + old_x
        new_img_y = (1 / 2 + offset_y) * (old_img_h - new_img_h) + old_y
        self.img_tl = QPointF(new_img_x, new_img_y)

        scale_factor = (new_img_w / old_img_w, new_img_h / old_img_h)
        self.__shape_scale_move(QPointF(old_x, old_y), scale_factor)
        self.signal_img_size2ui.send(self.scaled_img.size().toTuple())

        self.update()

    def __select_collection_ok(self, text):
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
            if st in INS_shape_type('组合'):
                pass
                # self.widget_points_huan, self.img_points_huan = [], []
                # widget_points_out, img_points_out = compute_new_points(polygon['widget_points'][0])
                # self.widget_points_huan.append(widget_points_out)
                # self.img_points_huan.append(img_points_out)
                #
                # add_offset = polygon['widget_points'][1][0] - polygon['widget_points'][0][0]
                # widget_points_in, img_points_in = compute_new_points(polygon['widget_points'][1], add_offset=add_offset)
                # self.widget_points_huan.append(widget_points_in)
                # self.img_points_huan.append(img_points_in)
            else:
                self.widget_points, self.img_points = compute_new_points(polygon['widget_points'])
            signal_one_collection_done.send(polygon['category'])
        else:  # 收藏标注
            if text in self.collected_shapes.keys():
                QMessageBox.warning(self, self.tr('名称重复'), self.tr('{}已存在。').format(text))
            else:
                self.collected_shapes[text] = self.__all_shapes[self.editing_shape_i]
                self.collection_window.ui.listWidget.addItem(QListWidgetItem(text))
                self.collection_window.ui.lineEdit.setText('')

        self.collection_window.close()

    def __set_cursor(self, press=False, moving=False, release=False, ctrl_press=False, ctrl_release=False, shift=False):
        if self.is_bg():
            return

        if 'null' not in str(self.action_pixel_cursor.icon()):
            self.setCursor(self.pixel_cursor)
        else:
            if self.sender() == self.action_pixel_cursor:
                self.setCursor(Qt.OpenHandCursor)

            if ctrl_press:
                if self.AnnMode:
                    self.setCursor(self.pencil_cursor)
                else:
                    if self.shape_type in INS_shape_type('像素'):
                        self.setCursor(self.pixel_cursor)
                    else:
                        self.setCursor(Qt.CrossCursor)
            elif ctrl_release:
                self.setCursor(Qt.OpenHandCursor)
            elif shift:
                if self.shape_type in INS_shape_type('像素') and self.editing_shape_i is not None:
                    self.setCursor(self.pixel_cursor)
            else:
                if (QApplication.keyboardModifiers() != Qt.ControlModifier and
                        QApplication.keyboardModifiers() != Qt.ShiftModifier):
                    if press:
                        if self.corner_index is None:
                            self.setCursor(Qt.ClosedHandCursor)
                    if moving:
                        if QApplication.mouseButtons() != Qt.LeftButton:
                            self.setCursor(Qt.OpenHandCursor)
                        if self.corner_index is not None:
                            self.unsetCursor()
                    if release:
                        if self.corner_index is None:
                            self.setCursor(Qt.OpenHandCursor)

    def __shape_scale_move(self, old_img_tl, scale_factor=(1., 1.)):  # 标注随图片缩放而缩放
        for one in self.__all_shapes:
            if one['shape_type'] in INS_shape_type('组合'):
                pass
            else:
                one['widget_points'] = self.shape_scale_convert(one['widget_points'], old_img_tl, scale_factor)

        for one in self.__shape_temp:
            if one['shape_type'] in INS_shape_type('组合'):
                pass
            else:
                one['widget_points'] = self.shape_scale_convert(one['widget_points'], old_img_tl, scale_factor)

        self.widget_points = self.shape_scale_convert(self.widget_points, old_img_tl, scale_factor)

        # for i, one in enumerate(self.widget_points_huan):
        #     moved = self.shape_scale_convert(one, old_img_tl, scale_factor)
        #     self.widget_points_huan[i] = moved

    def __show_collection_window(self, draw):
        if draw:
            self.FlagDrawCollection = True

        self.collection_window.show()

    def __show_menu(self):  # 在鼠标位置显示菜单
        if self.editing_shape_i is None:
            self.img_menu.exec(QCursor.pos())
        else:
            self.shape_menu.exec(QCursor.pos())

    def __undo(self):
        if self.AnnMode:
            self.undo_stack.undo()

    def change_pen(self, det_cross_color=None, seg_pen_size=None, seg_pen_color=None,
                   ann_pen_size=None, ann_pen_color=None):
        if det_cross_color is not None:
            self.cross_color = det_cross_color
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
        self.__clear_widget_img_points()

    def clear_all_polygons(self):
        self.__all_shapes = []
        self.__clear_widget_img_points()
        self.update()

    def clear_scaled_img(self, to_undo=True):
        if to_undo:
            command = AnnUndo(self, self.scaled_img.copy())
            self.undo_stack.push(command)

        self.scaled_img = self.img.scaled(self.scaled_img.size(), Qt.KeepAspectRatio, self.interpolation)
        self.update()
        self.scaled_img_painted = self.scaled_img.copy()

    def del_polygons(self):
        if self.ShapeEditMode and self.editing_shape_i is not None:
            self.__all_shapes.pop(self.editing_shape_i)
            get_HHL_parent(self).del_shape(self.editing_shape_i)
            self.editing_shape_i = None
        self.update()

    def focus_set_img_area(self, press=False, moving=False, release=False, ctrl_press=False, ctrl_release=False):
        if ctrl_press:
            self.setFocus()
        if moving:
            if self.corner_index is None and self.editing_shape_i is None:
                if QApplication.keyboardModifiers() != Qt.ControlModifier and not self.SelectingCateTag:
                    self.clearFocus()
            else:
                self.setFocus()

        self.__set_cursor(press, moving, release, ctrl_press, ctrl_release)

    def get_ann_img(self):
        return self.scaled_img_painted.scaled(self.img.size(), Qt.KeepAspectRatio, self.interpolation).toImage()

    def get_tuple_polygons(self):
        json_polygons = deepcopy(self.__all_shapes)

        if len(json_polygons):
            for one in json_polygons:
                if one['shape_type'] in INS_shape_type('组合'):
                    out_c, in_c = one['widget_points'][0], one['widget_points'][1]
                    widget_points = [[aa.toTuple() for aa in out_c], [aa.toTuple() for aa in in_c]]
                else:
                    widget_points = [aa.toTuple() for aa in one['widget_points']]

                one['widget_points'] = widget_points

        return json_polygons

    def modify_polygon_class(self, i, new_class, new_color):
        polygon = self.__all_shapes[i]
        polygon['category'] = new_class
        polygon['qcolor'] = new_color
        self.update()

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
                if one['shape_type'] in INS_shape_type('组合'):
                    p1 = self.img_coor_to_widget_coor(one['img_points'][0])
                    p2 = self.img_coor_to_widget_coor(one['img_points'][1])
                    ps = [p1, p2]
                elif one['shape_type'] in INS_shape_type(['多边形', '像素']):
                    ps = self.img_coor_to_widget_coor(one['img_points'])
                elif one['shape_type'] in INS_shape_type(['矩形', '椭圆形']):
                    p1 = [one['img_points'][0][0], one['img_points'][0][1]]
                    p2 = [one['img_points'][1][0], one['img_points'][1][1]]
                    ps = self.img_coor_to_widget_coor([p1, p2])

                one['widget_points'] = ps

            self.__all_shapes = polygons
            self.update()

    def reset_cursor(self):
        self.cursor_in_widget = QPointF(-10, -10)

    def save_one_shape(self, category: list[str], tags: list[str], qcolor: QColor):
        if self.FlagDrawCollection:
            st = self.FlagDrawCollection
            self.FlagDrawCollection = False
        else:
            st = self.shape_type

        self.__all_shapes.append({'category': category, 'tags': tags, 'qcolor': qcolor, 'shape_type': st,
                                  'widget_points': self.widget_points, 'img_points': self.img_points, 'combo': ''})
        self.__clear_widget_img_points()
        self.SelectingCateTag = False
        self.__shape_temp = []
        self.update()

    def set_ann_painted_img(self, path):
        if self.AnnMode:
            self.scaled_img_painted = QPixmap(path).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.scaled_img = self.scaled_img_painted
            self.update()

    def set_hide_cross(self, hide):
        self.HideCross = hide
        self.reset_cursor()
        self.update()

    def set_shape_locked(self, lock):
        self.PolygonLocked = lock

    def set_tool_mode(self, draw=True, shape_edit=False, ann=False):
        self.DrawMode, self.ShapeEditMode, self.AnnMode = draw, shape_edit, ann

        if draw:
            self.setMouseTracking(True)

        if not shape_edit:
            self.__clear_editing_i_corner()

        if ann:
            self.setMouseTracking(False)
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.clear_scaled_img(to_undo=False)

    # def redo(self):
    #     pass

    # def get_one_polygon(self, i):
    #     return deepcopy(self.__all_shapes[i])


class CenterImgView(QGraphicsView):  # 用于实现书签功能
    def __init__(self, parent=None):
        super().__init__(parent)
        self.img_area = CenterImg(self)
        self.img_area.setCursor(Qt.OpenHandCursor)
        self.img_area.paint_img('images/bg.png', img_path='images/bg.png')
        self.scene = QGraphicsScene(self)
        self.bookmark = QGraphicsPixmapItem()
        self.bookmark.setPixmap(QPixmap('images/bookmark/bookmark_red.png').scaled(40, 40))
        self.bookmark.setFlags(QGraphicsItem.ItemIsMovable)
        self.bookmark.setPos(0, -5)
        self.bookmark.setVisible(False)
        self.scene.addItem(self.bookmark)
        self.setScene(self.scene)

    def keyPressEvent(self, event):
        self.img_area.keyPressEvent(event)

    def resizeEvent(self, event):  # 窗口大小改变时，图片大小也随着改变
        super().resizeEvent(event)
        view_w, view_h = self.size().toTuple()
        self.scene.setSceneRect(0, 0, view_w, view_h)
        self.img_area.resize(view_w, view_h)
        self.img_area.mouseDoubleClickEvent(None)

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
