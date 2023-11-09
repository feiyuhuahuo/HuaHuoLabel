#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
from need.functions import get_HHL_parent
from PySide6.QtWidgets import QInputDialog, QPushButton, QMenu, QWidget, QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QCursor


class BaseButton(QWidget):
    ss_dict = {'base': 'QPushButton {border: 1px solid gray; border-top-right-radius: 4px; '
                       'border-bottom-right-radius: 4px;padding-left:5px; padding-right:5px;}',
               'selected': 'QPushButton {background-color: rgb(154, 202, 144);}'
                           'QPushButton:hover {background-color:rgb(140, 184, 131);}'
                           'QPushButton:pressed {background-color:rgb(126, 165, 118);}',
               'not_selected': 'QPushButton {background-color: rgb(235, 235, 235);}'
                               'QPushButton:hover {background-color:rgb(225, 225, 225);}'
                               'QPushButton:pressed {background-color:rgb(215, 215, 215);}',
               'default': 'QPushButton {border-bottom: 3px solid rgb(195, 39, 43);}'}

    def __init__(self, parent=None, cate='', looking=None, is_default=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu(self)
        self.menu.setFixedWidth(110)

        self.action_edit = QAction(QIcon('images/图片14.png'), self.tr('编辑'), self)
        self.action_edit.triggered.connect(self.edit_class)
        self.action_default = QAction(QIcon('images/favorite2.ico'), self.tr('设为默认'), self)
        self.action_default.triggered.connect(lambda: self.set_as_default(None))
        self.action_ex_group = QAction(QIcon('images/only_one.png'), self.tr('设置独占组'), self)
        self.action_ex_group.triggered.connect(self.set_exclusive_group)
        self.action_delete = QAction(QIcon('images/icon_43.png'), self.tr('删除'), self)
        self.action_delete.triggered.connect(self.delete)
        self.menu.addAction(self.action_edit)
        self.menu.addAction(self.action_default)
        self.menu.addAction(self.action_ex_group)
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
        self.pushButton_look.clicked.connect(lambda: self.set_looking(None))

        self.class_button = QPushButton(self)
        self.class_button.move(23, 0)
        self.class_button.setMinimumHeight(22)
        self.class_button.setStyleSheet(self.get_ss(['base', 'not_selected']))
        font = self.font()
        font.setPointSize(10)
        self.class_button.setFont(font)
        self.class_button.clicked.connect(self.set_selected)
        self.set_cate(cate)

        if cate != 'as_sem_bg':
            self.customContextMenuRequested.connect(self.show_menu)
        else:
            self.class_button.setDisabled(True)

        if looking is not None:
            self.set_looking(assigned_looking=looking)
        if is_default is not None:
            self.set_as_default(assigned_default=is_default)

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
                self.parent().edit_name(self.class_button.text(), text.strip())
                self.set_cate(text)
                get_HHL_parent(self).cate_button_update(from_where=self.__class__.__name__)

    def get_ss(self, ss_names: list):
        ss = [self.ss_dict[one] for one in ss_names]
        return ''.join(ss)

    def is_default(self):
        return self.ss_dict['default'] in self.class_button.styleSheet()

    def is_looking(self):
        return self.pushButton_look.accessibleName() == 'looking'

    def is_selected(self):
        return self.get_ss(['selected']) in self.class_button.styleSheet()

    def set_as_default(self, assigned_default=None):
        ori_ss = self.class_button.styleSheet()
        if assigned_default is None:
            ss_default = '' if self.get_ss(['default']) in ori_ss else self.get_ss(['default'])
        else:
            if assigned_default:
                ss_default = self.get_ss(['default'])
            else:
                ss_default = ''

        if ss_default:
            self.action_default.setText('取消默认')
            ss_selected = self.get_ss(['selected'])
            self.set_button_connect(False)
        else:
            self.action_default.setText('设为默认')
            ss_selected = self.get_ss(['not_selected'])
            self.set_button_connect(True)

        self.class_button.setStyleSheet(self.get_ss(['base']) + ss_default + ss_selected)

        if assigned_default is None:  # 由click触发才会去更新并保存按钮组信息
            self.parent().set_button_default(self.class_button.text(), True if ss_default else False)
            get_HHL_parent(self).cate_button_update(from_where=self.__class__.__name__)

    def set_button_connect(self, connect: bool):
        clicked_signal = self.class_button.metaObject().method(37)  # 37为信号clicked的索引
        if connect:
            if not self.class_button.isSignalConnected(clicked_signal):
                self.class_button.clicked.connect(self.set_selected)
        else:
            if self.class_button.isSignalConnected(clicked_signal):
                self.class_button.clicked.disconnect()

    def set_cate(self, cate: str):
        self.class_button.setText(cate.strip())
        self.adjust_size()

    def set_exclusive_group(self):  # todo
        pass

    def set_selected(self):
        ori_ss = self.class_button.styleSheet()
        ss_default = self.get_ss(['default']) if self.get_ss(['default']) in ori_ss else ''
        ss_selected = self.get_ss(['not_selected']) if self.get_ss(['selected']) in ori_ss else self.get_ss(
            ['selected'])
        self.class_button.setStyleSheet(self.get_ss(['base']) + ss_default + ss_selected)

    def set_looking(self, assigned_looking=None):
        set_looking = True
        if assigned_looking is None:
            if self.pushButton_look.accessibleName() == 'looking':
                set_looking = False
        else:
            set_looking = assigned_looking

        if not set_looking:
            self.pushButton_look.setAccessibleName('not_looking')
            self.pushButton_look.setIcon(QIcon('images/look/not_look2.png'))
        else:
            self.pushButton_look.setAccessibleName('looking')
            self.pushButton_look.setIcon(QIcon('images/look/look2.png'))

        if assigned_looking is None:  # 由click触发才会去更新并保存按钮组信息
            self.parent().set_button_looking(self.class_button.text(), set_looking)
            get_HHL_parent(self).cate_button_update(from_where=self.__class__.__name__)

    def show_menu(self):  # 在鼠标位置显示菜单
        self.menu.exec(QCursor.pos())


class ImgCateButton(BaseButton):
    def __init__(self, parent=None, cate='', looking=None, is_default=None):
        super().__init__(parent, cate, looking, is_default)


class ImgTagButton(BaseButton):
    def __init__(self, parent=None, cate='', looking=None, is_default=None):
        super().__init__(parent, cate, looking, is_default)


class ObjCateButton(BaseButton):
    def __init__(self, parent=None, cate='', looking=None, is_default=None):
        self.ss_dict = {'base': 'QPushButton {border: 1px solid gray; border-top-right-radius: 4px; '
                                'border-bottom-right-radius: 4px;padding-left:5px; padding-right:5px;}',
                        'selected': 'QPushButton {background-color: rgb(154, 202, 144);}',
                        'not_selected': 'QPushButton {background-color: rgb(235, 235, 235);}',
                        'default': 'QPushButton {border-bottom: 3px solid rgb(195, 39, 43);}'}
        super().__init__(parent, cate, looking, is_default)
        self.set_button_connect(False)


class ObjTagButton(BaseButton):
    def __init__(self, parent=None, cate='', looking=None, is_default=None):
        super().__init__(parent, cate, looking, is_default)