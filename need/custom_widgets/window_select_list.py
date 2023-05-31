#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import numpy as np

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QListWidgetItem
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtCore import Qt, QTimer


class BaseSelectList(QMainWindow):
    def __init__(self, parent=None, title='窗口', label='label'):
        super().__init__(parent)
        loader = QUiLoader()
        self.ui = loader.load('ui_files/select_list.ui')
        self.setCentralWidget(self.ui)
        self.resize(180, 260)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setWindowModality(Qt.ApplicationModal)
        self.ui.label.setText(label)

        icon_selected = QPixmap('images/icon_11.png')
        w, h = icon_selected.size().toTuple()
        self.icon_selected = QIcon(icon_selected)

        icon_not_selected = np.zeros((h, w, 4), dtype='uint8')
        icon_not_selected = QPixmap(QImage(icon_not_selected.data, w, h, w * 4, QImage.Format_RGBA8888))
        self.icon_not_selected = QIcon(icon_not_selected)

        self.ui.listWidget.itemClicked.connect(self.set_current_select)
        self.ui.pushButton_ok.clicked.connect(self.select_done)
        self.ui.pushButton_cancel.clicked.connect(self.close)

        self.select_stat = {}

    def select_done(self):
        for i in range(self.ui.listWidget.count()):
            item = self.ui.listWidget.item(i)
            text, icon = item.text(), item.icon()
            if icon.cacheKey() == self.icon_selected.cacheKey():
                self.select_stat[text] = True
            else:
                self.select_stat[text] = False

        QTimer.singleShot(50, self.close)

    def set_current_select(self):
        item = self.ui.listWidget.currentItem()
        if item.icon().cacheKey() == self.icon_selected.cacheKey():
            item.setIcon(QIcon(self.icon_not_selected))
        else:
            item.setIcon(QIcon(self.icon_selected))

    def show(self, item_text: dict):
        for text, selected in item_text.items():
            if text in self.select_stat.keys():
                items = self.ui.listWidget.findItems(text, Qt.MatchExactly)
                assert len(items) == 1, 'Error, "BaseSelectList": items count is not 1.'

                if self.select_stat[text]:
                    items[0].setIcon(QIcon(self.icon_selected))
                else:
                    items[0].setIcon(QIcon(self.icon_not_selected))

            else:
                new_item = QListWidgetItem(self.icon_selected if selected else self.icon_not_selected, text)
                self.ui.listWidget.addItem(new_item)

        super().show()


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    ui = BaseSelectList(title='你好')
    ui.show('asd', [('而无法', True), ('无法', False), ('sdw', True)])
    app.exec()
    print(ui.result())
