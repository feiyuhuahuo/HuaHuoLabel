#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
from PySide6.QtGui import QAction, QIcon, QCursor
from PySide6.QtWidgets import QWidget, QGroupBox, QMenu


class ImgEditor(QGroupBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.menu_img_edit = QMenu(self)
        self.menu_img_edit.setFixedWidth(110)
        self.action_open_folder = QAction(self.tr('打开文件夹'), self)
        self.action_open_folder.setIcon(QIcon('images/open_folder.png'))
        self.menu_img_edit.addAction(self.action_open_folder)
        self.customContextMenuRequested.connect(lambda: self.show_menu(self.menu_img_edit))

    # todo: keep update
    def prepare_editing(self, main_win):
        main_win.ui.tabWidget.setDisabled(True)
        main_win.ui.groupBox.setDisabled(True)
        main_win.ui.groupBox_6.setDisabled(True)
        main_win.ui.groupBox_7.setDisabled(True)
        main_win.ui.label_train.setDisabled(True)
        main_win.ui.label_val.setDisabled(True)
        main_win.ui.toolBox.setDisabled(True)
        main_win.ui.pushButton_pin.setDisabled(True)
        main_win.ui.label_train_val.setDisabled(True)

        self.set_disabled(False)

    def set_disabled(self, disabled=False):
        for one in self.findChildren(QWidget):
            if type(one) != QMenu and type(one) != QAction:
                one.setDisabled(disabled)

    @staticmethod
    def show_menu(menu):  # 在鼠标位置显示菜单
        menu.exec(QCursor.pos())
