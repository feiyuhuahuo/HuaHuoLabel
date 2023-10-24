#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

import numpy as np
import cv2

from PIL import Image, ImageOps
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QApplication, QDialog
from PySide6.QtWidgets import QMessageBox as QMB
from need.functions import glob_imgs


class ImgEdit(QDialog):
    def __init__(self, parent=None):
        assert parent.__class__.__name__ == 'HHL_MainWindow', 'parent is not right!'
        super().__init__(parent)
        self.ui = QUiLoader().load('ui_files/img_edit.ui')
        self.setLayout(self.ui.layout())
        self.setFixedSize(540, 340)  # 与ui文件保持一致
        self.setWindowTitle('图片编辑')
        self.setWindowIcon(QIcon('images/icon.png'))

        self.imgs = []
        self.save_path = ''
        self.support_mode = ('P', 'RGB', 'RGBA')
        self.file_select_dlg = QFileDialog(self)

        self.ui.radioButton_jpg.setChecked(True)  # ui文件明明设置好了，就是没效果，离谱。
        self.ui.radioButton_png.toggled.connect(self.set_depth4_enable)
        self.ui.pushButton_open.clicked.connect(self.load_imgs)
        self.ui.pushButton_save_path.clicked.connect(self.set_save_path)
        self.ui.pushButton_save_all.clicked.connect(self.save_edited_img)
        self.ui.checkBox_scale.toggled.connect(self.set_img_edit_scale)

    def load_imgs(self):
        imgs = self.file_select_dlg.getOpenFileNames(self, self.tr('选择图片'),
                                                     filter=self.tr('图片类型 (*.png *.jpg *.bmp)'))[0]

        if len(imgs) == 0:
            QMB.warning(self, self.tr('未找到图片'), self.tr('未找到图片!'))
        else:
            self.ui.lineEdit.setText(self.tr(f'共导入{len(imgs)}张图片。'))
            self.imgs = imgs

    def save_edited_img(self):
        if not len(self.imgs):
            QMB.warning(self, self.tr('未找到图片'), self.tr('图片数量为0!'))
            return

        if not self.save_path:
            QMB.warning(self, self.tr('请先设置保存路径。'), self.tr('请先设置保存路径。'))
            return

        if self.ui.radioButton_jpg.isChecked():
            suffix = '.jpg'
        elif self.ui.radioButton_png.isChecked():
            suffix = '.png'
        elif self.ui.radioButton_bmp.isChecked():
            suffix = '.bmp'

        imgs = glob_imgs(self.save_path)
        save_path_names = [one.split('/')[-1] for one in imgs]

        imgs_path = [aa for aa in self.imgs if aa != 'images/图片已删除.png']

        if len(save_path_names):
            same_name_num = 0
            for one in imgs_path:
                if one.split('/')[-1][:-4] + suffix in save_path_names:
                    same_name_num += 1

            if same_name_num:
                re = QMB.question(self, self.tr('存在同名的图片'),
                                  self.tr('"{}"下{}张同名的图片将被覆盖保存，继续吗？').
                                  format(self.save_path, same_name_num))

                if re != QMB.Yes:
                    return

        for one in imgs_path:
            img = Image.open(one)
            if img.mode not in self.support_mode:
                continue

            if (img.getexif()).get(274):  # 处理exif旋转信息
                img = ImageOps.exif_transpose(img)

            if img.mode == 'P':
                img = img.convert('RGBA')

            cv2_img = np.array(img, dtype='uint8')

            ori_c = 0
            if cv2_img.ndim == 2:
                ori_h, ori_w = cv2_img.shape
            else:
                ori_h, ori_w, ori_c = cv2_img.shape
                if ori_c == 3:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_RGB2BGR)
                elif ori_c == 4:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_RGBA2BGRA)

            rotate_a = self.ui.spinBox_rotate.value()

            if rotate_a == 90:
                cv2_img = cv2.rotate(cv2_img, cv2.ROTATE_90_CLOCKWISE)
            elif rotate_a == 180:
                cv2_img = cv2.rotate(cv2_img, cv2.ROTATE_180)
            elif rotate_a == 270:
                cv2_img = cv2.rotate(cv2_img, cv2.ROTATE_90_COUNTERCLOCKWISE)

            if self.ui.checkBox_h_flip.isChecked():
                cv2_img = cv2.flip(cv2_img, 1)
            if self.ui.checkBox_v_flip.isChecked():
                cv2_img = cv2.flip(cv2_img, 0)

            if self.ui.checkBox_scale.isChecked():
                resize_w, resize_h = self.ui.spinBox_width.value(), self.ui.spinBox_height.value()
                if ori_w != resize_w or ori_h != resize_h:
                    if self.ui.radioButton_nearest.isChecked():
                        scale_alg = cv2.INTER_NEAREST
                    elif self.ui.radioButton_bilinear.isChecked():
                        scale_alg = cv2.INTER_LINEAR
                    cv2_img = cv2.resize(cv2_img, (resize_w, resize_h), scale_alg)

            if self.ui.radioButton_d1.isChecked():
                if ori_c == 3:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
                elif ori_c == 4:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGRA2GRAY)
            elif self.ui.radioButton_d3.isChecked():
                if ori_c == 1:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_GRAY2BGR)
                elif ori_c == 4:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGRA2BGR)
            elif self.ui.radioButton_d4.isChecked():
                if ori_c == 1:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_GRAY2BGRA)
                elif ori_c == 3:
                    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2BGRA)

            save_name = one.split('/')[-1][:-4] + suffix
            cv2.imencode(suffix, cv2_img.astype('uint8'))[1].tofile(f'{self.save_path}/{save_name}')

        QMB.information(self, self.tr('保存完成'), self.tr('保存完成，共{}张图片。').format(len(imgs_path)))

    def set_depth4_enable(self):
        enable = self.ui.radioButton_png.isChecked()
        self.ui.radioButton_d4.setDisabled(not enable)
        if not enable and self.ui.radioButton_d4.isChecked():
            self.ui.radioButton_d3.setChecked(True)

    def set_img_edit_scale(self):
        enabled = self.ui.checkBox_scale.isChecked()
        self.ui.spinBox_width.setDisabled(not enabled)
        self.ui.spinBox_height.setDisabled(not enabled)
        self.ui.label_46.setDisabled(not enabled)
        self.ui.label_44.setDisabled(not enabled)
        self.ui.radioButton_nearest.setDisabled(not enabled)
        self.ui.radioButton_bilinear.setDisabled(not enabled)

    def set_save_path(self):
        folder = self.file_select_dlg.getExistingDirectory(self, self.tr('选择文件夹'))
        if folder:
            self.save_path = folder
            self.ui.lineEdit_2.setText(folder)


if __name__ == '__main__':
    app = QApplication()
    img_edit = ImgEdit()
    img_edit.show()
    app.exec()
