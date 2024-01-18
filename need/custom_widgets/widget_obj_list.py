#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtGui import QIcon, QColor, QCursor, QAction
from PySide6.QtWidgets import QPushButton, QApplication, QWidget, QListWidget, QListWidgetItem, QSizePolicy, \
    QVBoxLayout, QSpacerItem, QCheckBox, QMenu, QAbstractItemView
from need.custom_signals import IntSignal
from need.SharedWidgetStatVars import stat_vars
from need.functions import get_HHL_instance

signal_del_shape = IntSignal()
signal_del_shape_from_img = IntSignal()
signal_draw_selected_shape = IntSignal()
signal_set_obj_selected = IntSignal()
signal_show_obj_cate_tag = IntSignal()


class ObjList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(118)
        font = self.font()
        font.setPointSize(10)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.title_button = QPushButton(self.tr('   标注列表') + f'(0)', self)
        self.title_button.setFont(font)
        self.title_button.setFixedWidth(118)
        self.title_button.setStyleSheet('QPushButton '
                                        '{background-color: rgb(210, 230, 245);'
                                        'text-align: left;'
                                        'border-top: 1px solid gray;'
                                        'border-left: 1px solid gray;'
                                        'border-right: 1px solid gray;'
                                        'border-bottom: none;'
                                        'border-top-left-radius: 8px;'
                                        'border-top-right-radius: 8px;'
                                        'padding: 1px;}'
                                        'QPushButton:hover {background-color:  rgb(190, 210, 225);}'
                                        'QPushButton:pressed { background-color:  rgb(180, 200, 210);}')
        self.title_button.clicked.connect(self.__fold_list)

        self.edit_button = QCheckBox(self)
        self.edit_button.move(80, -5)
        self.edit_button.setStyleSheet('QCheckBox::indicator {padding-top: 1px; width: 40px; height: 26px;}'
                                       'QCheckBox::indicator:unchecked {image: url(images/switch_off.png);}'
                                       'QCheckBox::indicator:checked {image: url(images/switch_on.png);}')
        self.edit_button.setToolTip(self.tr('修改标注'))
        self.edit_button.setDisabled(True)

        self.obj_list = QListWidget(self)
        self.obj_list.setFixedWidth(118)
        self.obj_list.setFont(font)
        self.obj_list.setStyleSheet(
            """
                QListWidget {
                    background-color: rgb(255, 255, 255);
                    alternate-background-color: rgb(242, 242, 242);
                    border: 1px solid rgb(180, 180, 180);
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                    outline: none;
                }
                
                QListWidget::item:selected {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                
                QListWidget::item:hover {
                    background-color: rgba(0, 0, 0, 10%);
                    color: rgb(0, 0, 0);
                }
                
                QListWidget::item:disabled {
                    color: rgb(170, 170, 170);
                }
                
                QListWidget::item:selected:!active {
                    background-color: rgb(0, 99, 177);
                    color: rgb(255, 255, 255);
                }
                
                QListWidget::item:selected:active {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                
                QListWidget::item:selected:disabled {
                    background-color: rgba(0, 0, 0, 10%);
                    color: rgb(170, 170, 170);
                }
            """)

        self.icon_look = QIcon('images/look/look2.png')
        self.icon_look_key = self.icon_look.cacheKey()
        self.icon_unlook = QIcon('images/look/not_look2.png')
        self.icon_unlook_key = self.icon_unlook.cacheKey()
        self.icon_shape_locked = QIcon('images/locked.png')
        self.obj_list.itemClicked.connect(self.__draw_selected_shape)
        self.obj_list.itemSelectionChanged.connect(self.__show_obj_cate_tag)
        signal_set_obj_selected.signal.connect(self.__set_shape_selected)
        signal_del_shape_from_img.signal.connect(self.__del_shape_from_img)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_button)
        layout.addWidget(self.obj_list)
        self.setLayout(layout)

        self.menu = QMenu(title='label_list_menu', parent=self)
        self.menu.setFixedWidth(120)
        self.customContextMenuRequested.connect(self.__show_menu)
        self.action_modify = QAction(QIcon('images/note.png'), self.tr('修改类别/标签'), self)
        self.action_modify.triggered.connect(self.__modify_cate_tag)
        self.action_delete_one = QAction(QIcon('images/icon_43.png'), self.tr('删除标注'), self)
        self.action_delete_one.triggered.connect(lambda: self.__del_shape(False))
        self.action_delete_all = QAction(QIcon('images/no_no.png'), self.tr('全部删除'), self)
        self.action_delete_all.triggered.connect(lambda: self.__del_shape(True))
        self.action_lock_shape = QAction(QIcon('images/locked.png'), self.tr('锁定标注'), self)
        self.action_lock_shape.triggered.connect(self.lock_shape)

        self.menu.addAction(self.action_modify)
        self.menu.addAction(self.action_delete_one)
        self.menu.addAction(self.action_delete_all)
        self.menu.addAction(self.action_lock_shape)
        self.menu.setDisabled(True)

    def wheelEvent(self, event):
        if self.edit_button.isEnabled():
            self.edit_button.setChecked(event.angleDelta().y() < 0)

        if not self.edit_button.isChecked():
            if self.action_lock_shape.text() == self.tr('取消锁定'):
                self.lock_shape()

    def __del_shape(self, del_all=False):
        if del_all:
            self.obj_list.clear()
            signal_del_shape.send(-1)
        else:
            row_i = self.obj_list.currentRow()
            self.obj_list.takeItem(row_i)
            signal_del_shape.send(row_i)

        self.__update_list_num()

    def __del_shape_from_img(self, shape_i):
        if shape_i == -1:
            self.obj_list.clear()
        else:
            self.obj_list.takeItem(shape_i)

        signal_del_shape.send(shape_i)
        self.__update_list_num()

    def __draw_selected_shape(self):  # 在标注列表选定当前项时，对应高亮显示图上的标注
        signal_draw_selected_shape.send(self.obj_list.currentRow())

    def __fold_list(self):
        self.obj_list.setVisible(not self.obj_list.isVisible())
        self.resize(self.sizeHint())
        if self.obj_list.isVisible():
            self.parent().layout().setStretch(1, 20)
            self.parent().layout().setStretch(2, 1)
        else:
            self.parent().layout().setStretch(1, 1)
            self.parent().layout().setStretch(2, 20)

    def __modify_cate_tag(self):
        stat_vars.ObjList_Modifying_I = self.obj_list.currentRow()
        get_HHL_instance().select_cate_tag_before()

    def __set_shape_selected(self, i):  # 在图上选定标注时，对应设置标注列表的当前项
        item = self.obj_list.item(i)
        self.obj_list.setCurrentItem(item)
        item.setSelected(True)

    def __show_menu(self):  # 在鼠标位置显示菜单
        if not self.edit_button.isChecked():
            self.menu.setDisabled(True)
        else:
            self.menu.setDisabled(False)

        show = False
        rect1 = self.obj_list.rect()
        cursor_rel_pos = self.obj_list.mapFromGlobal(QCursor.pos())
        if rect1.contains(cursor_rel_pos):
            if self.obj_list.count() > 0:
                final_item = self.obj_list.item(self.obj_list.count() - 1)
                item_rect = self.obj_list.visualItemRect(final_item)
                if cursor_rel_pos.toTuple()[1] < item_rect.y() + item_rect.height():
                    show = True
        if show:
            self.menu.exec(QCursor.pos())

    def __show_obj_cate_tag(self):
        signal_show_obj_cate_tag.send(self.obj_list.currentRow())

    def __update_list_num(self):
        count = self.obj_list.count()
        self.title_button.setText(self.tr('   标注列表') + f'({count})')

    def add_item(self, text, color):
        item = QListWidgetItem(text)
        item.setForeground(QColor(color))
        self.obj_list.addItem(item)
        self.__update_list_num()

    def lock_shape(self):
        cur_item = self.obj_list.currentItem()
        if self.action_lock_shape.text() == self.tr('锁定标注'):
            self.obj_list.setSelectionMode(QAbstractItemView.NoSelection)  # 禁用item选择功能
            self.obj_list.itemClicked.disconnect()
            self.__draw_selected_shape()
            get_HHL_instance().wfm.center_img_set_shape_locked(True)
            self.action_modify.setDisabled(True)
            self.action_delete_one.setDisabled(True)
            self.action_delete_all.setDisabled(True)
            cur_item.setIcon(self.icon_shape_locked)
            self.action_lock_shape.setText(self.tr('取消锁定'))
        else:
            get_HHL_instance().wfm.center_img_set_shape_locked(False)
            self.action_modify.setDisabled(False)
            self.action_delete_one.setDisabled(False)
            self.action_delete_all.setDisabled(False)
            self.obj_list.setSelectionMode(QAbstractItemView.SingleSelection)
            self.obj_list.itemClicked.connect(self.__draw_selected_shape)
            cur_item.setIcon(QIcon())
            self.action_lock_shape.setText(self.tr('锁定标注'))

    def set_current_text(self, text, color):
        self.obj_list.currentItem().setText(text)
        self.obj_list.currentItem().setForeground(QColor(color))
