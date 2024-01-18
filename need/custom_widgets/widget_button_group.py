#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import random

from collections import OrderedDict
from PySide6.QtWidgets import (QInputDialog, QMessageBox, QWidget, QApplication, QSizePolicy, QHBoxLayout,
                               QVBoxLayout, QSpacerItem, QLineEdit)
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor
from need.custom_widgets import (ImgCateButton, ImgTagButton, ObjCateButton, ObjTagButton, signal_show_obj_cate_tag,
                                 signal_del_shape)
from need.custom_signals import ListSignal
from need.functions import get_HHL_instance
from need.utils import COlOR_NAMEs
from need.SharedWidgetStatVars import stat_vars

signal_update_button_num = ListSignal()


class BaseButtonGroup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addLayout(self.__new_h_layout())
        self.setFixedWidth(350)
        self.default_attrs = OrderedDict({'looking': True, 'is_default': False, 'ex_group': [], 'color': ''})
        self.button_stat = OrderedDict()
        self.color_names = COlOR_NAMEs.copy()

        self.color_codes = {}
        for one in COlOR_NAMEs:
            self.color_codes[QColor(one).name()] = one

        # 这些信号同时连接了多个slot，要注意slot的执行顺序和信号的连接顺序是一致的。在__init__中连接，有几个实例初始化就会连接几次
        signal_show_obj_cate_tag.signal.connect(self.__set_selecting_buttons)
        signal_del_shape.signal.connect(self.clear_buttons_wrt_obj)

    def __add_name(self, name, color='', looking=None, is_default=None):
        self.button_stat[name] = self.default_attrs.copy()
        if looking is not None:
            self.button_stat[name]['looking'] = looking
        if is_default is not None:
            self.button_stat[name]['is_default'] = is_default

        if color:
            self.button_stat[name]['color'] = color
        else:
            self.button_stat[name]['color'] = self.__new_color()

    def __button_num(self):
        num = 0
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button is not None:
                    num += 1
        return num

    def __clear_all_buttons(self):
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

    def __del_name(self, name):
        self.button_stat.pop(name)

    def __get_fake_prent(self):  # 用于设置QInputDialog().getText()等窗口的位置
        fake_parent = QWidget()
        fake_parent.setWindowIcon(self.windowIcon())
        fake_parent.move(self.parent().mapToGlobal(QPoint(0, 0)) + QPoint(-450, 0))
        return fake_parent

    def __new_color(self):
        random.shuffle(self.color_names)
        existed_colors = list(self.button_stat.values())
        color = self.color_names.pop()
        while color in existed_colors:
            if len(self.color_names) == 0:
                self.color_names = COlOR_NAMEs.copy()
            color = self.color_names.pop()
        return color

    def __new_h_layout(self):
        h_layout = QHBoxLayout(self)
        h_layout.setSpacing(6)
        h_layout.addItem(QSpacerItem(100, 22, QSizePolicy.Policy.Expanding))
        return h_layout

    def __set_selecting_buttons(self):  # 按钮的选中状态随选中目标的变化而变化
        if self.objectName() == 'img_cate_buttons':
            return
        elif self.objectName() == 'img_tag_buttons':
            return
        elif self.objectName() == 'obj_cate_buttons':
            name = stat_vars.CenterImg_CurrentObj['category']
        elif self.objectName() == 'obj_tag_buttons':
            name = stat_vars.CenterImg_CurrentObj['tags']

        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.button_name() in name:
                    if not button.is_selected():
                        button.set_selected_or_not()
                else:
                    if button.is_selected():
                        button.set_selected_or_not()

    def add_button(self, cate='', color='', looking=None, is_default=None, is_enable=False, by_click=True):
        added = False
        fake_parent = self.__get_fake_prent()

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
                    button = ImgCateButton(self, cate, looking, is_default, is_enable)
                elif self.objectName() == 'img_tag_buttons':
                    button = ImgTagButton(self, cate, looking, is_default, is_enable)
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
                        self.__add_name(cate, color, looking, is_default)
                        added = True
                        break

                if not added:
                    new_line = self.__new_h_layout()
                    new_line.insertWidget(0, button)
                    self.v_layout.addLayout(new_line)
                    self.__add_name(cate, color, looking, is_default)

                signal_update_button_num.send([self.objectName(), self.__button_num()])

                if by_click:
                    get_HHL_instance().cate_button_update(self.objectName())

    def check_name_list(self, name):
        if name in self.button_stat.keys():
            QMessageBox.critical(self.__get_fake_prent(), self.tr('名称重复'), self.tr('"{}"已存在！').format(name))
            return False
        return True

    def clear_buttons_wrt_obj(self, del_all):  # 清空目标类别、目标标签按钮组的选中状态
        if del_all == -1:
            if self.objectName() in ('obj_cate_buttons', 'obj_tag_buttons'):
                self.reset_button_select_stat()

    def color(self, name):
        return self.button_stat[name]['color']

    def del_button(self, name):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.button_name() == name:
                    h_layout.takeAt(j)
                    button.deleteLater()
                    self.__del_name(name)
                    signal_update_button_num.send([self.objectName(), self.__button_num()])
                    get_HHL_instance().cate_button_update(self.objectName())
                    return

    def edit_name(self, old_name, new_name):
        new_stat = OrderedDict()  # 新建一个字典来保证键的顺序

        for name, stat in self.button_stat.items():
            if name == old_name:
                new_stat[new_name] = stat
            else:
                new_stat[name] = stat

        self.button_stat = new_stat

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
        self.__clear_all_buttons()
        for name, stat in button_stat.items():
            self.add_button(name, stat['color'], bool(stat['looking']), bool(stat['is_default']), by_click=False)

    def names(self):
        return list(self.button_stat.keys())

    def need_waiting_button(self):
        return self.isVisible() and self.__button_num() > 0

    def reset_img_select_enable(self, enable: bool):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if not button.is_default():
                    button.set_click_valid(enable)

    def reset_button_select_stat(self):  # 将所有非默认的按钮设为非选中状态
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.is_selected():
                    if not button.is_default():
                        button.set_selected_or_not()

    def selected_buttons(self) -> list[str]:
        names = []
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()
                if button.is_selected():
                    names.append(button.button_name())

        return names

    def set_button_ex_group(self, name, ex_group):
        pass

    def set_obj_select_stat(self, before_select: bool):
        for i in range(self.v_layout.count()):
            h_layout = self.v_layout.itemAt(i)
            for j in range(h_layout.count() - 1):
                button = h_layout.itemAt(j).widget()

                if before_select:
                    if not button.is_default():
                        button.set_click_valid(True)
                    if button.is_selected():
                        if not button.is_default():
                            button.set_selected_or_not()
                else:
                    if not button.is_default():
                        button.set_click_valid(False)

    def track_is_looking(self, name, looking):
        self.button_stat[name]['looking'] = looking

    def track_is_default(self, name, is_default):
        self.button_stat[name]['is_default'] = is_default


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
