#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QListWidgetItem
from PySide6.QtGui import QIcon, QColor
from PySide6.QtCore import Qt
from need.custom_signals import BoolSignal
from need.functions import get_HHL_parent

signal_select_window_close = BoolSignal()


class SelectItem(QMainWindow):
    def __init__(self, parent=None, title='窗口', button_signal=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.ui = loader.load('ui_files/label_window.ui')
        self.setCentralWidget(self.ui)
        self.resize(160, 320)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setWindowModality(Qt.ApplicationModal)
        self.button_signal = button_signal
        self.ui.lineEdit.setPlaceholderText(self.tr(f'请输入{title}名称'))
        self.ui.listWidget.itemClicked.connect(self.__set_selected_name)
        self.ui.pushButton.clicked.connect(self.__emit_text)
        self.item_names = []

    def closeEvent(self, event):
        signal_select_window_close.send(True)
        self.close()

    def __emit_text(self):
        text = self.ui.lineEdit.text().strip()
        if text:
            text = text.replace('，', ',')
            classes = [one.strip() for one in text.split(',')]
            self.button_signal.send(classes)
        else:
            self.button_signal.send([])

    def __set_selected_name(self):
        selected_items = self.ui.listWidget.selectedItems()
        text = [one.text() for one in selected_items]
        self.ui.lineEdit.setText(', '.join(text))

    def add_item(self, text, color):
        item = QListWidgetItem(text.strip())
        item.setForeground(QColor(color))
        self.ui.listWidget.addItem(item)
        self.item_names.append(text)

    def clear(self):
        self.ui.listWidget.clear()
        self.item_names = []

    def show_at(self, geometry):
        x, y, w, h = geometry.x(), geometry.y(), geometry.width(), geometry.height()
        new_x = x + int(w / 3)
        new_y = y + int(h / 3)
        self.move(new_x, new_y)
        self.show()


# class SelectObjCate(SelectItem): # 老的选择类别的弹出窗口
#     def __init__(self, parent=None, title='窗口', button_signal=None):
#         super().__init__(parent, title, button_signal)
#
#     def closeEvent(self, event):
#         self.parent().ui.graphicsView.img_area.focus_set_img_area(ctrl_release=True)
#         self.parent().ui.graphicsView.img_area.clear_widget_img_points()
#
#     def show_at(self, geometry):
#         all_c = get_HHL_parent(self).ui.obj_cate_buttons.names()
#         for one_c in all_c:
#             color = get_HHL_parent(self).ui.obj_cate_buttons.color(one_c)
#             if one_c in self.item_names:
#                 item = self.ui.listWidget.item(self.item_names.index(one_c))
#                 item.setForeground(QColor(color))
#                 item.setSelected(False)
#             else:
#                 self.add_item(one_c, color)
#
#         super().show_at(geometry)
