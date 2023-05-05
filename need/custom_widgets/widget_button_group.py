#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QMenu, QWidget, QApplication, QSizePolicy, \
    QHBoxLayout, QVBoxLayout, QSpacerItem, QLineEdit
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QFont, QAction, QCursor
from need.custom_widgets.widget_cate_button import BaseButton


class ImgCateButtons(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addLayout(self.new_h_layout())
        self.setFixedWidth(350)
        self.name_list = []

    def add_button(self):
        added = False
        fake_parent = self.get_fake_prent()
        cate, is_ok = QInputDialog().getText(fake_parent, self.tr('名称'), self.tr('请输入名称。'), QLineEdit.Normal)
        cate = cate.strip()
        if is_ok and cate:
            if self.check_name_list(cate):
                button = BaseButton(self, cate)
                for i in range(self.v_layout.count()):
                    h_layout = self.v_layout.itemAt(i)
                    cur_width = 0
                    for j in range(h_layout.count() - 1):
                        cur_width += (h_layout.itemAt(j).widget().width() + h_layout.spacing())

                    if cur_width + button.width() < self.width():
                        h_layout.insertWidget(h_layout.count() - 1, button)
                        self.add_name(cate)
                        added = True
                        break

                if not added:
                    new_line = self.new_h_layout()
                    new_line.insertWidget(0, button)
                    self.v_layout.addLayout(new_line)
                    self.add_name(cate)

    def add_name(self, name):
        self.name_list.append(name)

    def check_name_list(self, name):
        if name in self.name_list:
            QMessageBox.critical(self.get_fake_prent(), self.tr('名称重复'), self.tr('"{}"已存在！').format(name))
            return False
        return True

    def del_button(self, name):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.button_name() == name:
                    h_layout.takeAt(j)
                    button.deleteLater()
                    self.del_name(name)
                    return

    def del_name(self, name):
        self.name_list.remove(name)

    def get_fake_prent(self):  # 用于设置QInputDialog().getText()等窗口的位置
        fake_parent = QWidget()
        fake_parent.setWindowIcon(self.windowIcon())
        fake_parent.move(self.parent().mapToGlobal(self.parent().pos()) + QPoint(-1350, -100))
        return fake_parent

    def new_h_layout(self):
        h_layout = QHBoxLayout(self)
        h_layout.setSpacing(6)
        h_layout.addItem(QSpacerItem(100, 22, QSizePolicy.Policy.Expanding))
        return h_layout


if __name__ == '__main__':
    app = QApplication()
    kk = ImgCateButtons()
    kk.add_button('asdfsgd')
    kk.add_button('fsf')
    kk.add_button('的士大')
    kk.add_button('大师傅但是')
    kk.add_button()
    kk.show()
    app.exec()
