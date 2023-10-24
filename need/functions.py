#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import os
import glob
import copy
import datetime
import numpy as np

from typing import Union, List
from PIL import Image, ImageOps
from os import path as osp
from datetime import datetime
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget
from need.custom_widgets import CustomMessageBox


def array_to_qimg(array: np.ndarray):
    depth = 1
    if array.ndim == 2:
        height, width = array.shape
    else:
        height, width, depth = array.shape

    if depth == 1:
        format = QImage.Format_Grayscale8
    elif depth == 3:
        format = QImage.Format_RGB888
    elif depth == 4:
        format = QImage.Format_RGBA8888
    else:
        raise ValueError(f'Unsupport array depth: "{depth}"!')

    return QImage(array.astype('uint8').data, width, height, width * depth, format)


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


def get_HHL_parent(widget: QWidget):
    assert widget.parent() is not None, f'"{widget}" has no parent.'

    while 'HHL_MainWindow' not in str(widget.parent()):
        widget = widget.parent()
        assert widget.parent() is not None, f'Strange! "{widget}" can not find HHL MainWindow.'

    return widget.parent()


def get_rotated_qpixmap(img_path):
    img = ImageOps.exif_transpose(Image.open(img_path))
    return QPixmap(array_to_qimg(np.array(img)))


def glob_imgs(path, recursive=False):
    if recursive:
        imgs = recursive_glob(path)
    else:
        imgs = glob.glob(f'{path}/*')
        imgs = [one for one in imgs if one[-3:] in ('bmp', 'jpg', 'png')]
        imgs = uniform_path(imgs)
        imgs.sort()
    return imgs


def glob_labels(path):
    labels = glob.glob(f'{path}/*')
    labels = [aa for aa in labels if aa[-4:] in ('json', '.png', '.txt')]
    labels = uniform_path(labels)
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
    else:
        raise ValueError(f'Unsupport language: "{language}"!')

    return ui


def img_pure_name(path):  # todo: 接受一个路径list统一处理，减少函数调用开销
    path = uniform_path(path)

    if path[-3:] in ('png', 'bmp', 'jpg', 'txt'):
        return path.split('/')[-1][:-4]
    elif path.endswith('json'):
        return path.split('/')[-1][:-5]


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
    files = uniform_path(glob.glob(f'{path}/*'))

    folders = [aa for aa in files if osp.isdir(aa)]
    folders.sort()
    if f'{path}/imgs' in folders:
        folders.remove(f'{path}/imgs')

    for one in folders:
        imgs = glob.glob(f'{one}/*')
        imgs = [aa for aa in imgs if aa[-3:] in ('bmp', 'jpg', 'png')]
        imgs.sort()
        all_imgs += imgs

    return uniform_path(all_imgs)


def rgb_to_hex(r, g, b):
    return ('{:02X}' * 3).format(r, g, b)


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


def uniform_path(path: Union[List[str], str]):
    if isinstance(path, list):
        return [one.replace('\\', '/').replace('\\\\', '/') for one in path]
    elif isinstance(path, str):
        return path.replace('\\', '/').replace('\\\\', '/')
    else:
        raise TypeError(f'TypeError for "{path}", should be str or [str, str, ...].')
