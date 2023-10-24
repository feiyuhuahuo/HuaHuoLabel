#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import numpy as np

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtCore import Qt, QTimer


class BaseSelectList(QDialog):  # 可多选列表窗口
    def __init__(self, parent=None, title='窗口', label='label'):
        super().__init__(parent)
        self.ui = QUiLoader().load('ui_files/select_list.ui')
        self.setLayout(self.ui.layout())
        self.resize(180, 260)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon('images/icon.png'))

        self.ui.label.setText(label)

        icon_selected = QPixmap('images/icon_11.png')
        w, h = icon_selected.size().toTuple()
        self.icon_selected = QIcon(icon_selected)

        icon_not_selected = np.zeros((h, w, 4), dtype='uint8')
        icon_not_selected = QPixmap(QImage(icon_not_selected.data, w, h, w * 4, QImage.Format_RGBA8888))
        self.icon_not_selected = QIcon(icon_not_selected)

        self.ui.listWidget.itemClicked.connect(self.set_current_select)
        self.ui.pushButton_ok.clicked.connect(self.select_done)
        self.ui.pushButton_cancel.clicked.connect(self.custom_close)

        self.select_stat = {}
        self.CloseByOK = False

    def custom_close(self, from_ok=False):
        if from_ok:
            self.CloseByOK = True
        else:
            self.CloseByOK = False

        self.close()

    def select_done(self):
        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            text, icon = item.text(), item.icon()
            if icon.cacheKey() == self.icon_selected.cacheKey():
                self.select_stat[text] = True
            else:
                self.select_stat[text] = False

        QTimer.singleShot(50, lambda: self.custom_close(True))

    def set_current_select(self):
        item = self.ui.listWidget.currentItem()
        if item.icon().cacheKey() == self.icon_selected.cacheKey():
            item.setIcon(QIcon(self.icon_not_selected))
        else:
            item.setIcon(QIcon(self.icon_selected))

    def show_with(self, item_text: dict):
        while self.ui.listWidget.count() > 0:
            self.ui.listWidget.takeItem(0)

        self.select_stat = {}

        for text, selected in item_text.items():
            new_item = QListWidgetItem(self.icon_selected if selected else self.icon_not_selected, text)
            self.ui.listWidget.addItem(new_item)

        super().exec()


class SingleSelectList(BaseSelectList):  # 仅单选列表窗口
    def __init__(self, parent=None, title='窗口', label='label'):
        super().__init__(parent, title, label)

    def set_current_select(self):
        row = self.ui.listWidget.currentRow()
        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            if i == row:
                item.setIcon(QIcon(self.icon_selected))
            else:
                item.setIcon(QIcon(self.icon_not_selected))


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = BaseSelectList(title='你好')
    ui.show_with({'而无法': True, '无法胜多负少收到v高峰时段VS的v宝宝': False, 'sdw': True, '而无法3g': True,
                  '而无法1': True,
                  '而无法2': True,
                  '而无法3': True,
                  '而无法4': True, '而无法55': True, '而无法t': True, '而无法er': True,
                  '而无法5': True, '而无法555': True,
                  })
    app.exec()
