#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
from collections import OrderedDict
from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget, QApplication, QSizePolicy, QHBoxLayout, \
    QVBoxLayout, QSpacerItem, QLineEdit, QMenu
from PySide6.QtCore import QPoint
from PySide6.QtGui import QIcon, QAction, QCursor
from need.custom_widgets.widget_cate_button import ImgCateButton, ImgTagButton, ObjCateButton, ObjTagButton
from need.custom_signals import ListSignal
from need.functions import get_HHL_parent

signal_update_button_num = ListSignal()


class BaseButtonGroup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addLayout(self.new_h_layout())
        self.setFixedWidth(350)
        self.default_attrs = OrderedDict({'looking': True, 'is_default': False, 'ex_group': []})
        self.button_stat = OrderedDict()

    def add_button(self, cate='', looking=None, is_default=None, by_click=True):
        added = False
        fake_parent = self.get_fake_prent()

        is_ok = True
        if not cate:
            assert looking is None and is_default is None and by_click, 'Value error when adding button.'

            cate, is_ok = QInputDialog().getText(fake_parent, self.tr('名称'), self.tr('请输入名称。'), QLineEdit.Normal)
            cate = cate.strip()
            if cate == 'as_sem_bg':
                QMessageBox.warning(fake_parent, self.tr('内建标签'), self.tr('"as_sem_bg"是内建标签，请更换名称。'))
                return

        if is_ok and cate:
            if self.check_name_list(cate):
                if self.objectName() == 'img_cate_buttons':
                    button = ImgCateButton(self, cate, looking, is_default)
                elif self.objectName() == 'img_tag_buttons':
                    button = ImgTagButton(self, cate, looking, is_default)
                elif self.objectName() == 'obj_cate_buttons':
                    button = ObjCateButton(self, cate, looking, is_default)
                elif self.objectName() == 'obj_tag_buttons':
                    button = ObjTagButton(self, cate, looking, is_default)

                for i in range(self.v_layout.count()):
                    h_layout = self.v_layout.itemAt(i)
                    cur_width = 0
                    for j in range(h_layout.count() - 1):
                        cur_width += (h_layout.itemAt(j).widget().width() + h_layout.spacing())

                    if cur_width + button.width() < self.width():
                        h_layout.insertWidget(h_layout.count() - 1, button)
                        self.add_name(cate, looking, is_default)
                        added = True
                        break

                if not added:
                    new_line = self.new_h_layout()
                    new_line.insertWidget(0, button)
                    self.v_layout.addLayout(new_line)
                    self.add_name(cate, looking, is_default)

                signal_update_button_num.send([self.objectName(), self.button_num()])

                if by_click:
                    get_HHL_parent(self).cate_button_update(self.objectName())

    def add_name(self, name, looking=None, is_default=None):
        self.button_stat[name] = self.default_attrs.copy()
        if looking is not None:
            self.button_stat[name]['looking'] = looking
        if is_default is not None:
            self.button_stat[name]['is_default'] = is_default

    def button_num(self):
        num = 0
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button is not None:
                    num += 1
        return num

    def check_name_list(self, name):
        if name in self.button_stat.keys():
            QMessageBox.critical(self.get_fake_prent(), self.tr('名称重复'), self.tr('"{}"已存在！').format(name))
            return False
        return True

    def clear_all_buttons(self):
        while self.v_layout.count() > 0:
            layout = self.v_layout.takeAt(0)
            while layout.count() > 0:
                widget = layout.takeAt(0).widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()

            layout.deleteLater()

        self.button_stat = OrderedDict()
        signal_update_button_num.send([self.objectName(), 0])

    def del_button(self, name):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.button_name() == name:
                    h_layout.takeAt(j)
                    button.deleteLater()
                    self.del_name(name)
                    signal_update_button_num.send([self.objectName(), self.button_num()])
                    get_HHL_parent(self).cate_button_update(self.objectName())
                    return

    def del_name(self, name):
        self.button_stat.pop(name)

    def edit_name(self, old_name, new_name):
        new_stat = OrderedDict()  # 新建一个字典来保证键的顺序

        for name, stat in self.button_stat.items():
            if name == old_name:
                new_stat[new_name] = stat
            else:
                new_stat[name] = stat

        self.button_stat = new_stat

    def get_fake_prent(self):  # 用于设置QInputDialog().getText()等窗口的位置
        fake_parent = QWidget()
        fake_parent.setWindowIcon(self.windowIcon())
        fake_parent.move(self.parent().mapToGlobal(QPoint(0, 0)) + QPoint(-450, 0))
        return fake_parent

    def get_button(self, name):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.button_name() == name:
                    return button
        return None

    def has_button(self, name):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.button_name() == name:
                    return True
        return False

    def init_buttons(self, button_stat):
        self.clear_all_buttons()
        for name, stat in button_stat.items():
            self.add_button(name, bool(stat['looking']), bool(stat['is_default']), by_click=False)

    def new_h_layout(self):
        h_layout = QHBoxLayout(self)
        h_layout.setSpacing(6)
        h_layout.addItem(QSpacerItem(100, 22, QSizePolicy.Policy.Expanding))
        return h_layout

    def set_button_looking(self, name, looking):
        self.button_stat[name]['looking'] = looking

    def set_button_default(self, name, is_default):
        self.button_stat[name]['is_default'] = is_default

    def set_button_ex_group(self, name, ex_group):
        pass


if __name__ == '__main__':
    app = QApplication()
    kk = BaseButtonGroup()
    kk.add_button('asdfsgd')
    kk.add_button('fsf')
    kk.add_button('的士大')
    kk.add_button('大师傅但是')
    kk.add_button()
    kk.show()
    app.exec()
