#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QMenu, QWidget, QApplication, QSizePolicy, \
    QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont, QAction, QCursor
from need.custom_widgets.widget_class_button2 import BaseButton


class ButtonGroup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addLayout(self.new_h_layout())
        self.resize(500, 50)

    def new_h_layout(self):
        # sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        spacer = QSpacerItem(100, 22, QSizePolicy.Policy.Expanding)

        h_layout = QHBoxLayout(self)
        h_layout.addItem(spacer)
        return h_layout

    def add_button(self):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            button = BaseButton()
            h_layout.insertWidget(h_layout.count()-1, button)


if __name__ == '__main__':
    app = QApplication()
    kk = ButtonGroup()
    kk.show()
    kk.add_button()
    kk.add_button()
    # img_edit = BaseButton()
    # img_edit.show()

    app.exec()
