#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import os
import pdb

from os import path as osp
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFileDialog, QMainWindow
from PySide6.QtWidgets import QMessageBox as QMB
from need.utils import uniform_path
from need.custom_threads import CopyImgs, signal_copy_imgs_done
from need.custom_signals import ListSignal
from need.custom_widgets import WaitingLabel

signal_send_imgs = ListSignal()


class BuildTask(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.btw = loader.load('build_task.ui')
        self.file_select_dlg = QFileDialog(self.btw)
        self.imgs = None
        self.work_mode = None
        self.img_folder = None
        self.root_path = None
        self.save_path = None
        self.version = None
        self.btw.pushButton_img.clicked.connect(lambda: self.set_page(0))
        self.btw.pushButton_video.clicked.connect(lambda: self.set_page(1))
        self.btw.pushButton_import_imgs.clicked.connect(self.import_imgs)
        self.btw.pushButton_task_name.clicked.connect(self.get_task_name)
        self.btw.pushButton_save_path.clicked.connect(self.get_save_path)
        self.btw.pushButton_build.clicked.connect(self.build_task_begin)
        signal_copy_imgs_done.signal.connect(self.build_task_end)

    def build_task_begin(self):
        task_name = self.btw.lineEdit_task_name.text().strip()
        self.version = self.btw.lineEdit_version.text().strip()
        if not task_name:
            QMB.critical(self.btw, self.tr('未输入任务名称'), self.tr('请输入任务名称。'))
            return
        if self.version is None:
            QMB.critical(self.btw, self.tr('未输入版本名称'), self.tr('请输入版本名称。'))
            return
        if self.save_path is None:
            QMB.critical(self.btw, self.tr('未选择保存路径'), self.tr('请选择任务保存路径。'))
            return
        if self.imgs is None:
            QMB.critical(self.btw, self.tr('无图片'), self.tr('未找到图片。'))
            return

        self.root_path = f'{self.save_path}/{task_name}'
        dst_path = f'{self.root_path}/{self.work_mode}/{self.img_folder}'
        if osp.exists(dst_path):
            QMB.critical(self.btw, self.tr('路径已存在'),
                         self.tr('"{}"已存在，请选择其它保存路径或任务类型。').format(dst_path))
        else:
            os.makedirs(dst_path, exist_ok=False)
            method = 'cut' if self.btw.radioButton_cut.isChecked() else 'copy'
            self.thread_copy_imgs = CopyImgs(self.imgs, dst_path, method)
            self.thread_copy_imgs.start()

            self.waiting_label = WaitingLabel(self.btw, self.tr('准备图片中'))
            self.waiting_label.show_at(self.btw.frameGeometry())

    def build_task_end(self):
        self.waiting_label.stop()
        self.waiting_label.close()
        self.btw.close()
        des_text = self.btw.textBrowser_des.toPlainText()
        signal_send_imgs.send([self.root_path, self.version, des_text])

    def get_save_path(self):
        path = self.file_select_dlg.getExistingDirectory(self.btw, self.tr('选择文件夹'))
        if osp.isdir(path):
            self.btw.lineEdit_6.setText(path)
            self.save_path = path

    def get_task_name(self):
        path = self.file_select_dlg.getExistingDirectory(self.btw, self.tr('选择文件夹'))
        if osp.isdir(path):
            task_name = path.split('/')[-1]
            self.btw.lineEdit_task_name.setText(task_name)
            save_path = path.removesuffix(f'/{task_name}')
            self.btw.lineEdit_6.setText(save_path)
            self.save_path = save_path

    def import_imgs(self):
        img_type = ''
        if self.btw.checkBox_jpg.isChecked():
            img_type += '*.jpg '
        if self.btw.checkBox_png.isChecked():
            img_type += '*.png '
        if self.btw.checkBox_bmp.isChecked():
            img_type += '*.bmp '

        if img_type:
            paths = self.file_select_dlg.getOpenFileNames(self.btw, self.tr('选择图片'),
                                                          filter=self.tr('图片类型 ({})').format(img_type))[0]

            if paths:
                self.btw.textBrowser_3.clear()
                self.imgs = paths

                jpg_num, png_num, bmp_num = 0, 0, 0
                for one in self.imgs:
                    suffix = one[-3:]
                    if suffix == 'jpg':
                        jpg_num += 1
                    if suffix == 'png':
                        png_num += 1
                    if suffix == 'bmp':
                        bmp_num += 1

                if jpg_num + png_num + bmp_num != 0:
                    if jpg_num != 0:
                        self.btw.textBrowser_3.append(self.tr('已导入{}张jpg图片。').format(jpg_num))
                    if png_num != 0:
                        self.btw.textBrowser_3.append(self.tr('已导入{}张png图片。').format(png_num))
                    if bmp_num != 0:
                        self.btw.textBrowser_3.append(self.tr('已导入{}张bmp图片。').format(bmp_num))
                else:
                    self.btw.textBrowser_3.append(self.tr('未找到图片。'))
        else:
            QMB.warning(self.btw, self.tr('未选择图片类型'), self.tr('请选择至少一种图片类型。'))

    def set_page(self, index):
        self.btw.stackedWidget.setCurrentIndex(index)

    def set_work_mode_img_folder(self, work_mode, img_folder):
        self.work_mode = work_mode
        self.img_folder = img_folder

    def show(self):
        self.btw.textBrowser_3.clear()
        self.btw.show()
