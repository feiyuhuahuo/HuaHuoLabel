#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QLabel, QGroupBox, QMenu, QApplication
from PySide6.QtGui import QPixmap, QAction, QCursor, QIcon
from PySide6.QtCore import Qt


class VersionTrack(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.TrackImg = False
        self.menu = QMenu(self)
        self.menu.setFixedWidth(100)
        self.action = QAction(self.tr('记录图片'), self)
        self.menu.addAction(self.action)
        self.action.triggered.connect(self.track_imgs)
        self.customContextMenuRequested.connect(self.show_menu)

    def track_imgs(self):
        if self.TrackImg:
            self.action.setIcon(QIcon(''))
            self.TrackImg = False
        else:
            self.action.setIcon(QPixmap('images/icon_11.png'))
            self.TrackImg = True

    def show_menu(self):
        self.menu.exec(QCursor.pos())


if __name__ == '__main__':
    app = QApplication()
    img_edit = VersionTrack()
    img_edit.show()
    app.exec()
