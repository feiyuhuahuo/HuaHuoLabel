#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QMenu, QWidget, QApplication, \
    QMainWindow, QHBoxLayout, QLineEdit
from PySide6.QtCore import Qt
# from need.utils import AllClasses
from PySide6.QtGui import QIcon, QFont, QAction, QCursor


class BaseButton(QWidget):
    def __init__(self, parent=None, cate=''):  # parent=None 必须要实现
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu(self)
        self.menu.setFixedWidth(90)
        self.customContextMenuRequested.connect(self.show_menu)

        self.action_edit = QAction(QIcon('images/图片14.png'), self.tr('编辑'), self)
        self.action_edit.triggered.connect(self.edit_class)
        self.action_default = QAction(QIcon('images/favorite2.ico'), self.tr('设为默认'), self)
        self.action_default.triggered.connect(self.set_as_default)
        self.action_delete = QAction(QIcon('images/icon_43.png'), self.tr('删除'), self)
        self.action_delete.triggered.connect(self.delete)
        self.menu.addAction(self.action_edit)
        self.menu.addAction(self.action_default)
        self.menu.addAction(self.action_delete)

        self.pushButton_look = QPushButton(self)
        self.pushButton_look.setFixedSize(25, 22)
        self.pushButton_look.setIcon(QIcon('images/look/look2.png'))
        self.pushButton_look.setAccessibleName('looking')
        self.pushButton_look.setStyleSheet(
            """
            QPushButton{background-color: rgb(235, 235, 235);
                        border: 1px solid gray;
                        border-top-left-radius: 4px;
                        border-bottom-left-radius: 4px;}
            QPushButton:hover {background-color:  rgb(225, 225, 225);}
            QPushButton:pressed {background-color:  rgb(215, 215, 215);}        
            """
        )
        self.pushButton_look.clicked.connect(self.set_look)

        self.ss_dict = {'base': 'QPushButton {border: 1px solid gray; border-top-right-radius: 4px; '
                                'border-bottom-right-radius: 4px;padding-left:5px; padding-right:5px;}',
                        'selected': 'QPushButton {background-color: rgb(154, 202, 144);}'
                                    'QPushButton:hover {background-color:rgb(140, 184, 131);}'
                                    'QPushButton:pressed {background-color:rgb(126, 165, 118);}',
                        'not_selected': 'QPushButton {background-color: rgb(235, 235, 235);}'
                                        'QPushButton:hover {background-color:rgb(225, 225, 225);}'
                                        'QPushButton:pressed {background-color:rgb(215, 215, 215);}',
                        'default': 'QPushButton {border-bottom: 3px solid rgb(195, 39, 43);}'}
        self.class_button = QPushButton(self)
        self.class_button.move(23, 0)
        self.class_button.setMinimumHeight(22)
        self.class_button.setStyleSheet(self.get_ss(['base', 'not_selected']))
        font = self.font()
        font.setPointSize(10)
        self.class_button.setFont(font)
        self.class_button.clicked.connect(self.set_selected)
        self.set_cate(cate)

    def adjust_size(self):
        self.class_button.setFixedWidth(max(26, self.class_button.sizeHint().width()))
        self.setFixedWidth(self.class_button.width() + 24)

    def button_name(self):
        return self.class_button.text()

    def delete(self):
        self.parent().del_button(self.class_button.text())

    def edit_class(self):
        text, is_ok = QInputDialog().getText(self, self.tr('名称'), self.tr('请输入名称。'), QLineEdit.Normal)
        if is_ok and text:
            if self.parent().check_name_list(text):
                self.parent().del_name(self.class_button.text())
                self.set_cate(text)
                self.parent().add_name(text)

    def get_ss(self, ss_names: list):
        ss = [self.ss_dict[one] for one in ss_names]
        return ''.join(ss)

    def set_as_default(self):
        ori_ss = self.class_button.styleSheet()
        ss_default = '' if self.get_ss(['default']) in ori_ss else self.get_ss(['default'])
        ss_selected = self.get_ss(['not_selected']) if self.get_ss(['not_selected']) in ori_ss else self.get_ss(
            ['selected'])
        self.class_button.setStyleSheet(self.get_ss(['base']) + ss_default + ss_selected)
        self.action_default.setText('取消默认' if ss_default else '设为默认')

    def set_cate(self, cate: str):
        self.class_button.setText(cate.strip())
        self.adjust_size()

    def set_selected(self):
        ori_ss = self.class_button.styleSheet()
        ss_default = self.get_ss(['default']) if self.get_ss(['default']) in ori_ss else ''
        ss_selected = self.get_ss(['not_selected']) if self.get_ss(['selected']) in ori_ss else self.get_ss(
            ['selected'])
        self.class_button.setStyleSheet(self.get_ss(['base']) + ss_default + ss_selected)

    def set_look(self):
        if self.pushButton_look.accessibleName() == 'looking':
            self.pushButton_look.setAccessibleName('not_looking')
            self.pushButton_look.setIcon(QIcon('images/look/not_look2.png'))
        else:
            self.pushButton_look.setAccessibleName('looking')
            self.pushButton_look.setIcon(QIcon('images/look/look2.png'))

    def show_menu(self):  # 在鼠标位置显示菜单
        self.menu.exec(QCursor.pos())


class test_w(QMainWindow):
    def __init__(self):
        super().__init__(parent=None)
        c_w = QWidget(self)
        self.layout = QHBoxLayout()
        pb = QPushButton()
        pb.clicked.connect(self.addd)
        self.layout.addWidget(pb)
        self.layout.addWidget(BaseButton())
        c_w.setLayout(self.layout)
        self.setCentralWidget(c_w)

    def addd(self):
        self.layout.addWidget(BaseButton())


if __name__ == '__main__':
    app = QApplication()
    kk = test_w()
    kk.show()
    # img_edit = BaseButton()
    # img_edit.show()

    app.exec()
