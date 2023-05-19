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
from PySide6.QtGui import QUndoCommand, QColor, QImage
from PySide6.QtWidgets import QMessageBox
from math import sqrt, pow
from need.custom_widgets import CustomMessageBox

ColorMs = [['青绿', (33, 90, 89), '凌霄橙', (237, 114, 63)], ['松绿', (61, 96, 54), '草黄', (177, 129, 81)],
           ['石榴红', (219, 8, 53), '桂黄', (237, 160, 31)], ['淡紫2', (165, 154, 202), '紫罗兰', (95, 71, 154)],
           ['绥蓝', (111, 155, 198), '雄黄', (243, 153, 58)], ['太师青', (85, 118, 123), '黄白', (233, 209, 181)],
           ['萼绿', (1, 73, 70), '缙红', (143, 52, 48)], ['青雀戴', (21, 60, 70), '琥珀黄', (249, 180, 0)],
           ['淡紫', (161, 114, 208), '锦粉', (248, 198, 181)], ['朱颜红', (239, 133, 109), '浅白', (223, 215, 194)],
           ['法蓝', (41, 175, 212), '皮肤粉', (231, 194, 202)], ['蓝绿', (135, 192, 202), '红白', (240, 207, 227)],
           ['酒蓝', (30, 59, 122), '珊瑚红', (202, 70, 47)], ['淡竹绿', (108, 169, 132), '秋波蓝', (138, 188, 209)],
           ['青雀戴', (21, 60, 70), '金红', (238, 120, 31)], ['海棠红', (219, 91, 108), '粉红', (255, 179, 167)],
           ['抹茶绿', (113, 152, 71), '玉白', (248, 247, 240)], ['浅松绿', (132, 192, 190), '竹绿', (27, 167, 132)],
           ['锦粉', (248, 198, 181), '深咖', (86, 66, 50)], ['风信紫', (195, 166, 203), '粉白', (255, 200, 222)],
           ['珠红', (210, 57, 24), '水碧', (128, 164, 146)], ['甘石粉', (234, 220, 214), '落霞红', (207, 72, 19)],
           ['中国红', (195, 39, 43), '黛绿', (66, 102, 102)], ['珍珠白', (229, 223, 213), '藤萝紫', (124, 115, 159)],
           ['鸭绿', (20, 102, 84), '赤橘', (240, 85, 16)], ['银白', (237, 237, 237), '瓦松绿', (107, 135, 112)],
           ['桃夭', (247, 189, 203), '桔梗蓝', (84, 86, 162)], ['银白', (237, 237, 237), '荷叶绿', (140, 184, 131)],
           ['淡黄白', (224, 223, 198), '朱柿', (237, 109, 70)], ['欧碧', (192, 214, 149), '黑朱', (112, 105, 93)],
           ['盈粉', (249, 211, 227), '玄红', (107, 84, 88)], ['凝脂白', (245, 242, 233), '灰绿', (134, 144, 138)],
           ['法翠', (16, 139, 150), '奶油黄', (234, 216, 154)], ['鹤顶红', (210, 71, 53), '女贞黄', (247, 238, 173)],
           ['金黄', (250, 192, 61), '黑蓝', (44, 47, 59)], ['朱颜红2', (242, 154, 118), '奶油黄2', (237, 241, 187)],
           ['凝脂白', (245, 242, 233), '天水碧', (90, 164, 174)], ['墙红', (207, 146, 158), '黄绿', (227, 235, 152)],
           ['浅黑', (48, 48, 48), '金橘', (253, 110, 0)], ['紫禁红', (164, 47, 31), '黄琉璃', (232, 168, 75)],
           ['墙蓝', (0, 88, 173), '白垩', (223, 224, 219)], ['深巧', (76, 33, 27), '嫣红', (255, 113, 127)],
           ['朱颜红3', (252, 148, 108), '灰青', (169, 211, 206)], ['千山翠', (102, 126, 113), '米白', (239, 234, 215)],
           ['抹茶绿', (107, 140, 51), '落叶黄', (254, 190, 0)], ['紫薇粉', (231, 192, 190), '青瓷绿', (127, 192, 161)],
           ['朱阳', (195, 0, 46), '浅黑2', (39, 41, 43)], ['黛紫', (84, 63, 99), '紫薯紫', (180, 162, 232)],
           ['蜜桃粉', (239, 148, 146), '苹果绿', (151, 195, 61)], [(228, 71, 87), (91, 55, 139), (56, 31, 73)],
           [(160, 36, 103), (239, 193, 182), (53, 49, 102)], [(210, 105, 142), (114, 131, 190), (255, 202, 186)],
           [(230, 20, 55), (255, 112, 66), (255, 200, 140)], [(254, 168, 44), (244, 195, 23), (77, 59, 45)],
           [(25, 28, 37), (195, 61, 26), (253, 219, 198)], [(43, 71, 113), (248, 95, 89), (247, 183, 151)],
           [(67, 48, 41), (254, 203, 64), (185, 144, 123)], [(24, 29, 47), (253, 205, 145), (222, 164, 81)],
           [(13, 103, 161), (114, 148, 194), (190, 199, 217)], [(23, 46, 89), (60, 75, 108), (184, 168, 159)],
           [(62, 49, 74), (254, 51, 54), (255, 157, 82)], [(62, 94, 132), (212, 198, 166), (234, 221, 208)],
           [(49, 87, 123), (253, 239, 208), (255, 243, 187)], [(48, 59, 84), (253, 243, 217), (159, 143, 144)],
           [(129, 112, 164), (232, 145, 159), (255, 198, 97)], [(217, 177, 175), (150, 161, 176), (226, 221, 224)],
           [(42, 119, 170), (245, 92, 151), (43, 97, 140)],
           ]

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


def rgb_to_hex(r, g, b):
    return ('{:02X}' * 3).format(r, g, b)


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

    def class_at(self, i):
        return self.__classes[i][0]

    def color_at(self, i):
        return self.__classes[i][1]

    def clear(self):
        self.__classes = []

    def __len__(self):
        return len(self.__classes)


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


AllClasses = ClassStatistic()
palette = Palette()


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
    c_time = f'{c_time[0][2:]} {c_time[1][:2]}h'
    m_time = f'{m_time[0][2:]} {m_time[1][:2]}h'
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


def glob_imgs(path, recursive=False):
    if recursive:
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
        ui = CustomMessageBox('about', '关于花火标注', hide_dsa=True)
        ui.add_text('版本1.0.0。\n'
                    '\n'
                    '花火标注是一款使用PySide6开发的多功能标注工具，支持包括单类别分类、多类别分类、语义分割、目标检测和实例分割在内的5种计算'
                    '机视觉任务的数据标注。花火标注还支持自动标注、数据集管理、伪标注合成等多种功能，可以帮助您更加方便、高效得训练AI模型。\n'
                    '\n'
                    '花火标注采用GNU GPL许可证，您可以随意使用该工具。但在未取得作者许可的情况下，请勿使用该软件进行商业行为。\n')
    elif language == 'EN':
        ui = CustomMessageBox('about', 'About HuaHuoLabel', hide_dsa=True)
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
