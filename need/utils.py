#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import copy
import cv2
import numpy as np
from collections import OrderedDict
from PySide6.QtGui import QUndoCommand, QColor, QImage
from math import sqrt, pow

ClassStatDict = OrderedDict()  # 用于记录分类和分割类别的数量

# CSS 通用color
ColorNames = ['black', 'blue', 'blueviolet', 'brown', 'burlywood',
              'cadetblue', 'chocolate', 'coral', 'crimson', 'cyan',
              'darkblue', 'darkcyan', 'darkgoldenrod', 'darkgreen', 'darkkhaki', 'darkolivegreen',
              'darkorange', 'darksalmon', 'darkseagreen', 'darkslateblue', 'darkslategray', 'darkturquoise',
              'darkviolet', 'deeppink', 'deepskyblue', 'dimgray', 'dodgerblue',
              'firebrick', 'fuchsia',
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
              'tan', 'teal', 'thistle', 'tomato',
              'violet',
              'wheat',
              'yellowgreen']

ColorCode = {}
for one in ColorNames:
    ColorCode[QColor(one).name()] = one


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


def get_seg_mask(classes, polygons, img_h, img_w, from_sub=False):
    all_masks = []
    for shape in polygons:
        label = shape['category']
        if label not in classes:
            if not from_sub:
                return label

        class_value = classes.index(label) + 1
        mask = np.zeros((img_h, img_w), dtype=np.uint8)

        if shape['shape_type'] == "多边形":
            points = [np.array([list(point) for point in shape['img_points']])]
            cv2.fillPoly(mask, points, 1)
        elif shape['shape_type'] == "矩形":
            cv2.rectangle(mask, tuple(shape['img_points'][0]), tuple(shape['img_points'][1]), 1, -1)
        elif shape['shape_type'] == "椭圆形":
            tl, br = tuple(shape['img_points'][0]), tuple(shape['img_points'][1])
            cx, cy = int((tl[0] + br[0]) / 2), int((tl[1] + br[1]) / 2)
            half_l, half_s = int((br[0] - tl[0]) / 2), int((br[1] - tl[1]) / 2)
            cv2.ellipse(mask, (cx, cy), (half_l, half_s), 0, 0, 360, color=1, thickness=-1)
        elif shape['shape_type'] == "环形":
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
        elif shape['shape_type'] == "填充":
            for point in shape['img_points']:
                mask[point[1], point[0]] = 1

        mask = np.asfortranarray(mask, dtype='uint8')[:, :, None] * class_value
        all_masks.append(mask)

    # 若标注有重叠区域，需要合并
    all_masks_num = np.array([(aa > 0).sum() for aa in all_masks])  # 根据像素数量来降序排序
    indices = (-1 * all_masks_num).argsort()  # * -1 来实现降序排序
    seg_mask = np.zeros((img_h, img_w, 1), dtype='int64')

    for ii in indices:
        mask = all_masks[ii]
        seg_mask *= (mask == 0)
        seg_mask += mask

    return seg_mask


def path_to(path, img2json=False, img2png=False, img2txt=False):
    if img2json:
        return path.replace('分割/原图', '分割/标注')[:-3] + 'json'
    elif img2png:
        return path.replace('分割/原图', '分割/标注')[:-3] + 'png'
    elif img2txt:
        return path.replace('原图', '标注')[:-3] + 'txt'


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
    return poly if flag else None


def point_in_shape(p, poly, shape_type='多边形'):  # 判断点是否在多边形内部
    px, py = p[0], p[1]
    if shape_type == '多边形':
        return point_in_polygon(px, py, poly)
    elif shape_type == '矩形':
        if poly[0][0] <= px <= poly[1][0] and poly[0][1] <= py <= poly[1][1]:
            return poly
        return None
    elif shape_type == '椭圆形':
        cx, cy = (poly[0][0] + poly[1][0]) / 2, (poly[0][1] + poly[1][1]) / 2
        px, py = px - cx, cy - py
        a, b = (poly[1][0] - poly[0][0]) / 2, (poly[1][1] - poly[0][1]) / 2

        if px ** 2 / a ** 2 + py ** 2 / b ** 2 <= 1:
            return poly
        return None
    elif shape_type == '环形':
        if point_in_polygon(px, py, poly[0]) is not None and point_in_polygon(px, py, poly[1]) is None:
            return poly
        return None


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


def uniform_path(path):
    return path.replace('\\', '/').replace('\\\\', '/')
