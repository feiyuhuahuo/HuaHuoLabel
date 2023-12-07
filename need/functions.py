#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import os
import glob
import copy
import datetime
import pdb

import numpy as np

from typing import Union, List
from PIL import Image, ImageOps, ExifTags
from os import path as osp
from datetime import datetime
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget
from need.custom_widgets import CustomMessageBox

Image.MAX_IMAGE_PIXELS = None


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

    # 不指定bytesPerLine，图片打开容易错乱、程序崩溃，原因未知
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
    c_time = c_time.replace('-', '.')
    m_time = m_time.replace('-', '.')
    return c_time, m_time


def get_HHL_parent(widget: QWidget):  # 返回后，只允许调用HHL_MainWindow的方法，不允许调用其子控件，否则用信号
    assert widget.parent() is not None, f'"{widget}" has no parent.'

    while 'HHL_MainWindow' not in str(widget.parent()):
        widget = widget.parent()
        assert widget.parent() is not None, f'Strange! "{widget}" can not find HHL MainWindow.'

    return widget.parent()


def get_rotated_img_array(img_path: str, size: tuple = ()):
    limit_area = 100000000

    def limit_warn():
        size_info = CustomMessageBox('question', QObject.tr('图片尺寸过大'), hide_dsa=False)
        size_info.show(QObject.tr(f'图片尺寸过大(总面积需<{limit_area}像素），程序将占用较多内存，'
                                  f'图片的显示也会较为耗时，请留意。要解除尺寸限制请点击"确定"。'))
        return size_info.question_result

    img = Image.open(img_path)  # 不会加载相机旋转信息
    img = img.convert('RGB')  # 始终以RGB模式显示
    if size:
        r_w, r_h = size
        if r_w * r_h <= limit_area:
            img = img_exif_orientation(img)
            img = img.resize(size, Image.BILINEAR)
        else:
            if limit_warn():
                img = img_exif_orientation(img)
                img = img.resize(size, Image.BILINEAR)
            else:
                img = None
    else:
        w, h = img.size
        if w * h > limit_area:
            if limit_warn():
                img = img_exif_orientation(img)
            else:
                img = None
        else:
            img = img_exif_orientation(img)

    if img is not None:
        return np.array(img)
    else:
        return None


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


def img_exif_orientation(img):
    exif = img.getexif()
    if exif is None:
        return img

    exif = {ExifTags.TAGS[k]: v for k, v in exif.items() if k in ExifTags.TAGS}
    orientation = exif.get('Orientation', None)

    if orientation == 1:
        return img
    elif orientation == 2:
        return ImageOps.mirror(img)
    elif orientation == 3:
        return img.transpose(Image.ROTATE_180)
    elif orientation == 4:
        return ImageOps.flip(img)
    elif orientation == 5:
        return ImageOps.mirror(img.transpose(Image.ROTATE_270))
    elif orientation == 6:
        return img.transpose(Image.ROTATE_270)
    elif orientation == 7:
        return ImageOps.mirror(img.transpose(Image.ROTATE_90))
    elif orientation == 8:
        return img.transpose(Image.ROTATE_90)
    else:
        return img


def img_path2_qpixmap(img_path):
    if (img_array := get_rotated_img_array(img_path)) is None:
        return None
    else:
        return QPixmap(array_to_qimg(img_array))


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
