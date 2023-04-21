#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import os
import pdb
import numpy as np
import cv2
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QCursor, QPixmap, QImage, QColor, QFontMetrics, QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow, QApplication
from PySide6.QtWidgets import QMessageBox as QMB

from need.utils import glob_imgs


class ImgEdit(QMainWindow):
    def __init__(self, parent=None):
        assert parent.__class__.__name__ == 'HHL_MainWindow', 'parent is not right!'
        super().__init__(parent)
        loader = QUiLoader()
        self.ui = loader.load('ui_files/img_edit.ui')
        self.setCentralWidget(self.ui)
        self.setFixedSize(530, 240)
        self.setWindowTitle('图片编辑')
        self.setWindowIcon(QIcon('images/icon.png'))

        self.imgs = []
        self.save_path = ''
        self.file_select_dlg = QFileDialog(self)

        self.ui.pushButton_open.clicked.connect(self.load_imgs)
        self.ui.pushButton_save_path.clicked.connect(self.set_save_path)
        self.ui.pushButton_save_cur.clicked.connect(self.save_edited_img)
        self.ui.pushButton_save_all.clicked.connect(lambda: self.save_edited_img(save_all=True))
        self.ui.checkBox_scale.toggled.connect(self.set_img_edit_scale)

    def closeEvent(self, event):
        self.disbale_widgets(False)

    @staticmethod
    def check_save_name_img(imgs1: list, imgs2: list):
        same_name_num = 0
        for one in imgs1:
            img_name = one.split('/')[-1]
            for one_2 in imgs2:
                if img_name in one_2:
                    same_name_num += 1

        return same_name_num

    def disbale_widgets(self, disable):  # keep update
        main_ui = self.parent().ui
        main_ui.tabWidget.setDisabled(disable)
        main_ui.groupBox_1.setDisabled(disable)
        main_ui.groupBox_2.setDisabled(disable)
        main_ui.groupBox_3.setDisabled(disable)
        main_ui.label_version.setDisabled(disable)
        main_ui.lineEdit_version.setDisabled(disable)
        main_ui.toolBox.setDisabled(disable)

    def load_imgs(self):
        folder = self.file_select_dlg.getExistingDirectory(self, self.tr('选择文件夹'))
        if folder:
            imgs = glob_imgs(folder)
            if len(imgs) == 0:
                QMB.warning(self, self.tr('未找到图片'), self.tr('"{}"下图片数量为0!').format(folder))
            else:
                self.ui.lineEdit.setText(folder)
                self.imgs = imgs
                self.parent().set_imgs(self.imgs)

    def save_edited_img(self, save_all=False):
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
            
        if save_all:
            imgs_path = [aa for aa in self.imgs if aa != 'images/图片已删除.png']

            if len(save_path_names):
                same_name_num = 0
                for one in imgs_path:
                    if one.split('/')[-1][:-4] + suffix in save_path_names:
                        same_name_num += 1

                if same_name_num:
                    re = QMB.question(self, self.tr('存在同名的图片'), self.tr('"{}"下{}张同名的图片将被覆盖保存，继续吗？').
                                      format(self.save_path, same_name_num))

                    if re != QMB.Yes:
                        return
        else:
            path = self.imgs[self.parent().cur_i]
            save_name = path.split('/')[-1][:-4] + suffix
            if save_name in save_path_names:
                re = QMB.question(self, self.tr('同名图片'), self.tr('"{}"同名并将被覆盖，继续吗？').format(save_name))
                if re != QMB.Yes:
                    return

            imgs_path = [path]

        for one in imgs_path:
            cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_UNCHANGED)
            ori_h, ori_w = cv2_img.shape[:2]
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

            save_name = one.split('/')[-1][:-4] + suffix
            cv2.imencode(suffix, cv2_img.astype('uint8'))[1].tofile(f'{self.save_path}/{save_name}')

        QMB.information(self, self.tr('保存完成'), self.tr('保存完成，共{}张图片。').format(len(imgs_path)))

    def set_img_edit_scale(self):
        enabled = self.ui.checkBox_scale.isChecked()
        self.ui.spinBox_width.setDisabled(not enabled)
        self.ui.spinBox_height.setDisabled(not enabled)
        self.ui.label_46.setDisabled(not enabled)
        self.ui.label_44.setDisabled(not enabled)
        self.ui.radioButton_nearest.setDisabled(not enabled)
        self.ui.radioButton_bilinear.setDisabled(not enabled)

    def set_img_removed(self, i):
        self.imgs[i] = 'images/图片已删除.png'

    def set_save_path(self):
        folder = self.file_select_dlg.getExistingDirectory(self, self.tr('选择文件夹'))
        if folder:
            self.save_path = folder
            self.ui.lineEdit_2.setText(folder)

    def show(self):
        self.disbale_widgets(True)
        super().show()


if __name__ == '__main__':
    app = QApplication()
    img_edit = ImgEdit()
    img_edit.show()
    app.exec()
