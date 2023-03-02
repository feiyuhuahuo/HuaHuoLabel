#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtGui import QColor, QIcon
from need.utils import AllClasses, palette
from need.custom_signals import IntSignal
from need.custom_widgets import signal_set_shape_list_selected, signal_draw_selected_shape

signal_update_num = IntSignal()


class ClassListWidget(QListWidget):
    def __init__(self, parent=None):  # parent=None 必须要实现
        super().__init__(parent)
        self.icon_look = QIcon('images/图片100.png')
        self.icon_look_key = self.icon_look.cacheKey()
        self.icon_unlook = QIcon('images/图片101.png')
        self.icon_unlook_key = self.icon_unlook.cacheKey()
        self.ClassRelated = True

    def add_item(self, item: QListWidgetItem):
        super().addItem(item)
        self.update_list_num()

        if self.ClassRelated:
            color_code = item.foreground().color().name()
            color_name = palette.color_codes[color_code]
            AllClasses.add(item.text(), color_name)

    def clear(self):
        super().clear()
        self.update_list_num()

        if self.ClassRelated:
            AllClasses.clear()

    def del_row(self, row: int):
        del_c = self.item(row).text()
        self.takeItem(row)
        self.update_list_num()

        if self.ClassRelated:
            AllClasses.delete(del_c)

    def modify_cur_c(self, new_c: str):
        item = self.currentItem()
        old_c = item.text()
        item.setText(new_c)

        if self.ClassRelated:
            AllClasses.change_c(old_c, new_c)

    @staticmethod
    def new_class_item(new_c: str, color: str = 'none'):
        item = QListWidgetItem(new_c)
        if color == 'none':
            color = palette.get_color()
        item.setForeground(QColor(color))
        return item, color

    def set_look(self, item: QListWidgetItem):
        item.setIcon(self.icon_look)

    def set_unlook(self, item: QListWidgetItem):
        item.setIcon(self.icon_unlook)

    def set_looking(self, double_click=False):
        item = self.currentItem()

        if double_click:
            item.setIcon(self.icon_look)
            row = self.currentRow()
            count = self.count()
            for i in range(count):
                if i != row:
                    self.item(i).setIcon(self.icon_unlook)
        else:
            if item.icon().cacheKey() == self.icon_look_key:
                item.setIcon(self.icon_unlook)
            elif item.icon().cacheKey() == self.icon_unlook_key:
                item.setIcon(self.icon_look)

    def looking_all(self):
        for i in range(self.count()):
            item = self.item(i)
            if item.icon().cacheKey() == self.icon_unlook_key:
                return False
        return True

    def looking_classes(self):
        classes = []
        for i in range(self.count()):
            item = self.item(i)
            if item.icon().cacheKey() == self.icon_look_key:
                classes.append(item.text())

        return classes

    def set_name(self, name):
        self.name = name

    def update_list_num(self):
        signal_update_num.set_name(self.name)
        signal_update_num.send(self.count())


class ShapeListWidget(ClassListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ClassRelated = False
        self.icon_shape_locked = QIcon('images/locked.png')
        signal_set_shape_list_selected.signal.connect(self.set_shape_selected)
        self.itemClicked.connect(lambda: self.draw_selected_shape(i=-1))

    def has_locked_shape(self):
        for i in range(self.count()):
            item = self.item(i)
            if item.icon().cacheKey() != 0:
                return item
        return False

    def set_shape_locked(self, item: QListWidgetItem):
        item.setIcon(self.icon_shape_locked)
        self.draw_selected_shape(self.row(item))

    def set_shape_unlocked(self, item: QListWidgetItem):
        item.setIcon(QIcon())

    def draw_selected_shape(self, i):  # 在标注列表选定当前项时，对应高亮显示图上的标注
        if i == -1:
            if not self.has_locked_shape():
                signal_draw_selected_shape.send(self.currentRow())
        else:
            signal_draw_selected_shape.send(i)

    def set_shape_selected(self, i):  # 在图上选定标注时，对应设置标注列表的当前项
        item = self.item(i)
        self.setCurrentItem(item)
        item.setSelected(True)
