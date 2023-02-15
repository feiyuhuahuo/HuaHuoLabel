#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import os
import glob
import copy
import datetime
import cv2
import numpy as np
import random

from os import path as osp
from datetime import datetime
from collections import OrderedDict
from PySide6.QtGui import QUndoCommand, QColor, QImage
from PySide6.QtWidgets import QMessageBox
from math import sqrt, pow
from need.custom_widgets import CustomMessageBox


class ClassStatistic_2:  # 只有读、写两种接口，避免混乱
    def __init__(self):
        self.stat_dict = OrderedDict()
        self.copy_dict = self.stat_dict.copy()

    def read(self, k='', keys=False, kv_pair=False, length=False):
        if k:
            return self.stat_dict[k]
        elif keys:
            return self.stat_dict.keys()
        elif kv_pair:
            return self.stat_dict.items()
        elif length:
            return len(self.stat_dict)

    def write(self, k_set='', k_plus='', k_minus='', k_del='', clear=False):
        if self.copy_dict != self.stat_dict:
            print(f'----------错误，ClassStat未通过write()接口进行修改----------')
            return

        if k_set:
            self.stat_dict.setdefault(k_set, 0)
        elif k_plus:
            self.stat_dict.setdefault(k_plus, 0)
            self.stat_dict[k_plus] += 1
        elif k_minus:
            if k_minus not in self.stat_dict.keys():
                print(f'----------错误，ClassStat未找到键：{k_minus}----------')
            else:
                self.stat_dict[k_minus] -= 1
        elif k_del:
            if k_del not in self.stat_dict.keys():
                print(f'----------错误，ClassStat未找到键：{k_del}----------')
            else:
                self.stat_dict.pop(k_del)
        elif clear:
            self.stat_dict.clear()

        self.copy_dict = self.stat_dict.copy()


class ClassStatistic:
    def __init__(self):
        self.__classes = []

    def add(self, category, color='none'):
        for one in self.__classes:
            if one[0] == category:
                return

        self.__classes.append([category, color])

    def change_c(self, old_c, new_c):
        for one in self.__classes:
            if one[0] == old_c:
                one[0] = new_c

    def delete(self, c):
        if type(c) == int:
            self.__classes.pop(c)
        elif type(c) == str:
            for i, one in enumerate(self.__classes):
                if one[0] == c:
                    self.__classes.pop(i)

    def classes(self):
        return [aa[0] for aa in self.__classes]

    def colors(self):
        return [aa[1] for aa in self.__classes]

    def clear(self):
        self.__classes = []


AllClasses = ClassStatistic()

# CSS 通用color
ColorNames = ['black', 'blue', 'blueviolet', 'brown', 'burlywood',
              'cadetblue', 'chocolate', 'coral', 'crimson', 'cyan',
              'darkblue', 'darkcyan', 'darkgoldenrod', 'darkgreen', 'darkkhaki', 'darkolivegreen',
              'darkorange', 'darksalmon', 'darkseagreen', 'darkslategray', 'darkturquoise',
              'darkviolet', 'deeppink', 'deepskyblue', 'dimgray',
              'fuchsia',
              'gold', 'goldenrod', 'gray', 'green',
              'hotpink',
              'indianred', 'indigo',
              'khaki',
              'lawngreen', 'lightblue', 'lightcoral', 'lightgreen', 'lightpink', 'lightsalmon', 'lightseagreen',
              'lightskyblue', 'lightslategray', 'lightsteelblue', 'lime', 'limegreen',
              'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid', 'mediumseagreen',
              'mediumslateblue', 'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 'midnightblue',
              'olive', 'orangered', 'orchid',
              'palevioletred', 'peachpuff', 'peru', 'pink', 'plum', 'purple',
              'red', 'rosybrown', 'royalblue',
              'saddlebrown', 'sienna', 'silver', 'steelblue',
              'tan', 'teal', 'thistle',
              'violet',
              'wheat',
              'yellowgreen']


class AnnUndo(QUndoCommand):
    def __init__(self, board, undo_img, parent=None):
        super().__init__(parent)
        self.board = board
        self.undo_img = undo_img
        self.setText('undo paint')

    def redo(self):
        pass

    def undo(self):
        self.board.scaled_img = self.undo_img
        self.board.scaled_img_painted = self.board.scaled_img.copy()
        self.board.update()


def douglas_peuker(point_list, threshold, lowerLimit=4, ceiling=40):
    """
    道格拉斯-普克抽稀算法
    :param point_list: like [[122.358638, 30.280378], [122.359314, 30.280649]]
    :param threshold: 0.003
    :param lowerLimit: 输出点个数必须大于lowerLimit， 如果没有， 不做设置 like: 4
    :param ceiling: 输出点个数必须小于ceiling， 如果没有，不做设置  like: 2500
    :return:
    """

    def diluting(point_list, threshold, qualify_list, disqualify_list):
        """
        抽稀
        """
        if len(point_list) < 3:
            qualify_list.extend(point_list[::-1])
        else:
            # 找到与首尾两点连线距离最大的点
            max_distance_index, max_distance = 0, 0
            for index, point in enumerate(point_list):
                if index in [0, len(point_list) - 1]:
                    continue
                distance = point_to_line_Distance(point, point_list[0], point_list[-1])
                if distance > max_distance:
                    max_distance_index = index
                    max_distance = distance

            # 若最大距离小于阈值，则去掉所有中间点。 反之，则将曲线按最大距离点分割
            if max_distance < threshold:
                qualify_list.append(point_list[-1])
                qualify_list.append(point_list[0])
            else:
                # 将曲线按最大距离的点分割成两段
                sequence_a = point_list[:max_distance_index]
                sequence_b = point_list[max_distance_index:]

                for sequence in [sequence_a, sequence_b]:
                    if len(sequence) < 3 and sequence == sequence_b:
                        qualify_list.extend(sequence[::-1])
                    else:
                        disqualify_list.append(sequence)
        return qualify_list, disqualify_list

    def get_qualify_list(point_list, threshold):
        qualify_list = list()
        disqualify_list = list()

        qualify_list, disqualify_list = diluting(point_list, threshold, qualify_list, disqualify_list)
        while len(disqualify_list) > 0:
            qualify_list, disqualify_list = diluting(disqualify_list.pop(), threshold, qualify_list, disqualify_list)

        return qualify_list

    # 当输入点数小于5，直接输出
    if len(point_list) < 5:
        return point_list

    result = get_qualify_list(point_list, threshold)

    # 当返回值长度小于lowerLimit时，减小 threshold的值
    if len(result) < lowerLimit:
        while len(result) < lowerLimit:
            threshold = threshold * 0.9
            result = get_qualify_list(point_list, threshold)

    # 当返回值长度大于ceiling时，增大 threshold的值
    if ceiling and len(result) > ceiling:
        while len(result) > ceiling:
            threshold = threshold * 1.1
            result = get_qualify_list(point_list, threshold)

    if len(result) > len(point_list):
        return point_list

    return result


def file_remove(path):
    if type(path) == list:
        for one in path:
            if os.path.exists(one):
                os.remove(one)
        return True
    elif type(path) == str:
        if os.path.exists(path):
            os.remove(path)
            return True
    return False


def get_datetime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_file_cmtime(path):
    c_time = str(datetime.fromtimestamp(int(osp.getctime(path))))
    m_time = str(datetime.fromtimestamp(int(osp.getmtime(path))))
    c_time, m_time = c_time.split(' '), m_time.split(' ')
    c_time = f'{c_time[0][2:]}-{c_time[1][:2]}'
    m_time = f'{m_time[0][2:]}-{m_time[1][:2]}'
    return c_time, m_time


def get_seg_mask(classes, polygons, img_h, img_w, value=0, ins_seg=False):
    all_masks = []
    for i, shape in enumerate(polygons):
        label = shape['category']
        if (not value) and (label not in classes):
            QMessageBox.critical(None, '类别不存在', f'类别"{label}"不存在。')
            return None

        if ins_seg:
            class_value = i + 1
        else:
            class_value = value if value else classes.index(label) + 1

        mask = np.zeros((img_h, img_w), dtype=np.uint8)

        if shape['shape_type'] in ('多边形', 'Polygon'):
            points = [np.array([list(point) for point in shape['img_points']])]
            cv2.fillPoly(mask, points, 1)
        elif shape['shape_type'] in ('矩形', 'Rectangle'):
            cv2.rectangle(mask, tuple(shape['img_points'][0]), tuple(shape['img_points'][1]), 1, -1)
        elif shape['shape_type'] in ('椭圆形', 'Ellipse'):
            tl, br = tuple(shape['img_points'][0]), tuple(shape['img_points'][1])
            cx, cy = int((tl[0] + br[0]) / 2), int((tl[1] + br[1]) / 2)
            half_l, half_s = int((br[0] - tl[0]) / 2), int((br[1] - tl[1]) / 2)
            cv2.ellipse(mask, (cx, cy), (half_l, half_s), 0, 0, 360, color=1, thickness=-1)
        elif shape['shape_type'] in ('环形', 'Ring'):
            mask1 = np.zeros((img_h, img_w), dtype=np.uint8)
            mask2 = np.zeros((img_h, img_w), dtype=np.uint8)
            points1 = [np.array([tuple(point) for point in shape['img_points'][0]])]
            points2 = [np.array([tuple(point) for point in shape['img_points'][1]])]
            cv2.fillPoly(mask1, points1, 1)
            cv2.fillPoly(mask2, points2, 1)
            mask1 = np.asfortranarray(mask1, dtype='uint8')
            mask2 = np.asfortranarray(mask2, dtype='uint8')
            mask2 = ~(mask2.astype('bool'))
            mask = mask1 * mask2
        elif shape['shape_type'] in ('像素', 'Pixel'):
            for point in shape['img_points']:
                mask[point[1], point[0]] = 1

        mask = np.asfortranarray(mask, dtype='uint8') * class_value
        all_masks.append(mask)

    # 若标注有重叠区域，需要合并
    all_masks_num = np.array([(aa > 0).sum() for aa in all_masks])  # 根据像素数量来降序排序
    indices = (-1 * all_masks_num).argsort()  # * -1 来实现降序排序
    seg_mask = np.zeros((img_h, img_w), dtype='int64')
    for ii in indices:
        mask = all_masks[ii]
        seg_mask *= (mask == 0)
        seg_mask += mask

    if not ins_seg and not (0 <= seg_mask.max() <= len(classes)):
        QMessageBox.critical(None, '标注错误', f'当前有{len(classes)}类，但mask最大值为{seg_mask.max()}。')
        return None

    return seg_mask


def glob_imgs(path, work_mode):
    if work_mode in ('单分类', 'Single Cls'):
        imgs = recursive_glob(path)
    else:
        imgs = glob.glob(f'{path}/*')
        imgs = [uniform_path(aa) for aa in imgs if aa[-3:] in ('bmp', 'jpg', 'png')]
        imgs.sort()
    return imgs


def glob_labels(path):
    labels = glob.glob(f'{path}/*')
    labels = [uniform_path(aa) for aa in labels if aa[-4:] in ('json', '.png', '.txt')]
    if f'{path}/labels.json' in labels:
        labels.remove(f'{path}/labels.json')
    labels.sort()
    return labels


def has_ch(text):
    for one in text:
        if u'\u4e00' <= one <= u'\u9fff':
            return True
    return False


def hhl_info(language):
    if language == 'CN':
        ui = CustomMessageBox('about', '关于花火标注')
        ui.hide_dont_show_again()
        ui.add_text('版本1.0.0。\n'
                    '\n'
                    '花火标注是一款使用PySide6开发的多功能标注工具，支持包括单类别分类、多类别分类、语义分割、目标检测和实例分割在内的5种计算'
                    '机视觉任务的数据标注。花火标注还支持自动标注、数据集管理、伪标注合成等多种功能，可以帮助您更加方便、高效得训练AI模型。\n'
                    '\n'
                    '花火标注采用GNU GPL许可证，您可以随意使用该工具。但在未取得作者许可的情况下，请勿使用该软件进行商业行为。\n')
    elif language == 'EN':
        ui = CustomMessageBox('about', 'About HuaHuoLabel', 'EN')
        ui.hide_dont_show_again()
        ui.add_text('Version 1.0.0.\n'
                    '\n'
                    'HuaHuoLabel is a multifunctional label tool developed with PySide6. It can help label data for '
                    'five computer vision tasks including single category classification, multiple category '
                    'classification, semantic segmentation, object detection and instance segmentation. HuaHuoLabel '
                    'also supports auto-labeling, dataset management and pseudo label generation. With the help of '
                    'HuaHuoLabel, you can train your AI model more conveniently and efficiently.\n'
                    '\n'
                    'HuaHuoLabel uses GNU GPL license. You can use this tool at will. However, do not use it for '
                    'commercial activities without the permission of the author.\n')
    return ui


def img_pure_name(path):
    path = uniform_path(path)

    if path[-3:] in ('png', 'bmp', 'jpg', 'txt'):
        return path.split('/')[-1][:-4]
    elif path.endswith('json'):
        return path.split('/')[-1][:-5]


class Palette:
    def __init__(self):
        self.color_names = ColorNames.copy()
        self.color_codes = {}
        for one in ColorNames:
            self.color_codes[QColor(one).name()] = one

    def get_color(self):
        random.shuffle(self.color_names)
        existed_colors = AllClasses.colors()
        color = self.color_names.pop()
        while color in existed_colors:
            if len(self.color_names) == 0:
                self.color_names = ColorNames.copy()
            color = self.color_names.pop()
        return color


palette = Palette()


def path_to(path, img2json=False, img2png=False, img2txt=False):
    if '/原图' in path:
        if img2json:
            return path.replace('/原图', '/标注')[:-3] + 'json'
        elif img2png:
            return path.replace('/原图', '/标注')[:-3] + 'png'
        elif img2txt:
            return path.replace('/原图', '/标注')[:-3] + 'txt'
    elif '/Original Images' in path:
        if img2json:
            return path.replace('/Original Images', '/Label Files')[:-3] + 'json'
        elif img2png:
            return path.replace('/Original Images', '/Label Files')[:-3] + 'png'
        elif img2txt:
            return path.replace('/Original Images', '/Label Files')[:-3] + 'txt'


def point_in_polygon(px, py, poly):
    flag = False
    i = 0
    l = len(poly)
    j = l - 1

    while i < l:
        sx = poly[i][0]
        sy = poly[i][1]
        tx = poly[j][0]
        ty = poly[j][1]

        if (sx == px and sy == py) or (tx == px and ty == py):  # 点与多边形顶点重合
            return px, py
        # 判断线段两端点是否在射线两侧
        if (sy < py <= ty) or (sy >= py > ty):
            x = sx + (py - sy) * (tx - sx) / (ty - sy)  # 线段上与射线 Y 坐标相同的点的 X 坐标
            if x == px:  # 点在多边形的边上
                return px, py
            if x > px:  # 射线穿过多边形的边界
                flag = not flag
        j = i
        i += 1

    # 射线穿过多边形边界的次数为奇数时点在多边形内
    return flag


def point_in_shape(p: tuple, poly: list, shape_type='多边形') -> bool:  # 判断点是否在某个形状内部
    px, py = p[0], p[1]
    if shape_type in ('多边形', 'Polygon'):
        return point_in_polygon(px, py, poly)
    elif shape_type in ('矩形', 'Rectangle'):
        if poly[0][0] <= px <= poly[1][0] and poly[0][1] <= py <= poly[1][1]:
            return True
    elif shape_type in ('椭圆形', 'Ellipse'):
        cx, cy = (poly[0][0] + poly[1][0]) / 2, (poly[0][1] + poly[1][1]) / 2
        px, py = px - cx, cy - py
        a, b = (poly[1][0] - poly[0][0]) / 2, (poly[1][1] - poly[0][1]) / 2
        if px ** 2 / a ** 2 + py ** 2 / b ** 2 <= 1:
            return True
    elif shape_type in ('环形', 'Ring'):
        if point_in_polygon(px, py, poly[0]) and (not point_in_polygon(px, py, poly[1])):
            return True
    elif shape_type in ('像素', 'Pixel'):
        if list(p) in poly:
            return True

    return False


def point_to_line_Distance(point_a, point_b, point_c):  # 计算点a到点b c所在直线的距离
    # 首先计算b c 所在直线的斜率和截距
    if point_b[0] == point_c[0]:
        return 999999
    slope = (point_b[1] - point_c[1]) / (point_b[0] - point_c[0])
    intercept = point_b[1] - slope * point_b[0]

    # 计算点a到b c所在直线的距离
    distance = abs(slope * point_a[0] - point_a[1] + intercept) / sqrt(1 + pow(slope, 2))
    return distance


def qimage_to_array(img, share_memory=False):
    """ Creates a numpy array from a QImage.

        If share_memory is True, the numpy array and the QImage is shared.
        Be careful: make sure the numpy array is destroyed before the image,
        otherwise the array will point to unreserved memory!!
    """
    assert isinstance(img, QImage), "img must be a QtGui.QImage object"
    assert img.format() == QImage.Format.Format_RGB32, \
        "img format must be QImage.Format.Format_RGB32, got: {}".format(img.format())

    img_size = img.size()
    buffer = img.constBits()

    # Sanity check
    n_bits_buffer = len(buffer) * 8
    n_bits_image = img_size.width() * img_size.height() * img.depth()
    assert n_bits_buffer == n_bits_image, \
        "size mismatch: {} != {}".format(n_bits_buffer, n_bits_image)

    assert img.depth() == 32, "unexpected image depth: {}".format(img.depth())

    # Note the different width height parameter order!
    arr = np.ndarray(shape=(img_size.height(), img_size.width(), img.depth() // 8),
                     buffer=buffer, dtype=np.uint8)

    if share_memory:
        return arr
    else:
        return copy.deepcopy(arr)


def recursive_glob(path):  # 仅把path目录下的文件夹里的图片集合起来
    all_imgs = []
    files = glob.glob(f'{path}/*')
    files = [uniform_path(aa) for aa in files]

    folders = [aa for aa in files if osp.isdir(aa)]
    folders.sort()
    if f'{path}/imgs' in folders:
        folders.remove(f'{path}/imgs')

    for one in folders:
        imgs = glob.glob(f'{one}/*')
        imgs = [aa for aa in imgs if aa[-3:] in ('bmp', 'jpg', 'png')]
        imgs.sort()
        all_imgs += imgs

    all_imgs = [uniform_path(aa) for aa in all_imgs]
    return all_imgs


class ShapeType:
    def __init__(self):
        self.shape_type = {'多边形': 'Polygon', '矩形': 'Rectangle', '椭圆形': 'Ellipse', '环形': 'Ring',
                           '像素': 'Pixel'}

    def __call__(self, name):
        if type(name) == str:
            name = [name]

        result = []
        for one in name:
            result.append(one)
            result.append(self.shape_type[one])

        return result


shape_type = ShapeType()


def two_way_check(files_1: list, files_2: list, one_way=False):
    names_1 = [img_pure_name(aa) for aa in files_1]
    names_2 = [img_pure_name(aa) for aa in files_2]
    not_in_2, not_in_1 = [], []

    for i, one in enumerate(names_1):
        if one not in names_2:
            not_in_2.append(files_1[i])

    if not one_way:
        for i, one in enumerate(names_2):
            if one not in names_1:
                not_in_1.append(files_2[i])

    return not_in_2, not_in_1


def uniform_path(path):
    return path.replace('\\', '/').replace('\\\\', '/')
