#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QApplication, QListWidgetItem, QMenu
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QIcon, QCursor

from need.SharedWidgetStatFlags import stat_flags
from need.custom_signals import ListSignal, BoolSignal, StrSignal

signal_draw_sub_shape = StrSignal()
signal_shape_combo_reset = BoolSignal()
signal_rename_sub_shape = ListSignal()


class ShapeCombo(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load('../../ui_files/shape_combo.ui')
        self.setCentralWidget(self.ui)
        self.setWindowTitle(self.tr('组合形状'))
        self.resize(220, 400)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_menu)
        self.menu = QMenu(self)
        self.action_delete_shape = QAction(QIcon('images/icon_43.png'), self.tr('删除形状'), self)
        self.action_delete_shape.triggered.connect(self.__del_shape)
        self.action_rename_shape = QAction(QIcon('images/note.png'), self.tr('修改名称'), self)
        self.action_rename_shape.triggered.connect(self.__rename_shape)
        self.menu.addAction(self.action_delete_shape)
        self.menu.addAction(self.action_rename_shape)

        self.ui.pushButton_union.clicked.connect(self.__add_combo_diff)
        self.ui.pushButton_diff.clicked.connect(self.__add_combo_union)
        self.ui.pushButton_new.clicked.connect(self.__clear_all_shapes)
        self.ui.listWidget.itemChanged.connect(self.__shape_name_changed)
        signal_draw_sub_shape.signal.connect(self.__add_base_shape)

    def closeEvent(self, event):
        self.__clear_all_shapes()
        stat_flags.ShapeCombo_IsOpened = False
        self.parent().shape_type_reset()

    def __add_base_shape(self, shape_type: str):
        name = shape_type + str(self.ui.listWidget.count() + 1)
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.ui.listWidget.addItem(item)

    def __add_combo_diff(self):
        pass

    def __add_combo_union(self):
        pass

    def __clear_all_shapes(self):
        self.ui.listWidget.clear()
        self.ui.listWidget_2.clear()
        signal_shape_combo_reset.send(True)

    def __del_shape(self):
        pass

    def __rename_shape(self):
        pass

    def __shape_name_changed(self):
        i, name = self.ui.listWidget.currentRow(), self.ui.listWidget.currentItem().text()
        signal_rename_sub_shape.send([i, name])

    def move_to(self, pos: QPoint):
        self.move(pos)

    def show_at(self, pos: QPoint):
        self.move(pos)
        stat_flags.ShapeCombo_IsOpened = True
        self.show()

    def show_menu(self):  # 在鼠标位置显示菜单
        self.menu.exec(QCursor.pos())
        print(QCursor.pos())


if __name__ == '__main__':
    app = QApplication()
    pp = ShapeCombo()
    pp.show()
    app.exec()
