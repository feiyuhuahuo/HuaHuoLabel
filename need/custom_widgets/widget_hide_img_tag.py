#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtGui import QAction, QIcon, QCursor
from PySide6.QtWidgets import QWidget, QGroupBox, QMenu, QListWidget, QSpacerItem


class ImgTagList(QListWidget):
    def __init__(self, parent):
        super().__init__(parent=None)
        self.spacer = QSpacerItem(20, 200)

    def set_visible(self, main_win):
        self.setVisible(not self.isVisible())

        if self.isVisible():
            for i in range(main_win.ui.verticalLayout_13.count()):
                item = main_win.ui.verticalLayout_13.itemAt(i)
                if type(item) == QSpacerItem:
                    main_win.ui.verticalLayout_13.takeAt(i)
        else:
            aa = QSpacerItem(20, 200)
            main_win.ui.verticalLayout_13.addSpacerItem(aa)
            main_win.ui.verticalLayout_13.setStretch(0, 0)
            main_win.ui.verticalLayout_13.setStretch(1, 0)
            main_win.ui.verticalLayout_13.setStretch(2, 0)
            main_win.ui.verticalLayout_13.setStretch(3, 10)
