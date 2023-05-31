#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import pdb

from PySide6.QtWidgets import QGroupBox, QMenu, QApplication
from PySide6.QtGui import QAction, QCursor, QIcon
from need.custom_widgets.window_select_list import BaseSelectList


class VersionTrack(QGroupBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.TrackImg = False
        self.menu = QMenu(self)
        self.menu.setFixedWidth(115)
        self.window_track_files = BaseSelectList(self, self.tr('配置记录文件'), self.tr('请选择需要记录的文件'))

        self.action = QAction(QIcon('images/setting.png'), self.tr('配置记录文件'), self)
        self.menu.addAction(self.action)
        self.action.triggered.connect(self.get_tracked_files)
        self.customContextMenuRequested.connect(self.show_menu)

    def get_tracked_files(self):
        files_stat = self.parent().parent().parent().get_track_files()
        self.window_track_files.show(files_stat)

        self.parent().parent().parent().update_tracked_files(self.window_track_files.select_stat)

    def track_stat(self):
        return self.window_track_files.select_stat

    def show_menu(self):
        self.menu.exec(QCursor.pos())


if __name__ == '__main__':
    app = QApplication()
    img_edit = VersionTrack()
    img_edit.show()
    app.exec()
