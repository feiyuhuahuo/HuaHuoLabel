#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QApplication, QListWidgetItem, QMenu, QMessageBox
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QIcon, QCursor

from need.SharedWidgetStatFlags import stat_flags
from need.custom_signals import ListSignal, BoolSignal, StrSignal
from need.functions import get_HHL_parent

signal_draw_sub_shape = StrSignal()
signal_shape_combo_reset = BoolSignal()
signal_rename_sub_shape = ListSignal()


# python  求字符串运算式， 类似eval(), https://blog.csdn.net/lishuaigell/article/details/122114239
class ShapeCombo(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load('ui_files/shape_combo.ui')
        self.setCentralWidget(self.ui)
        self.setWindowTitle(self.tr('组合形状'))
        self.resize(300, 400)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.listWidget.customContextMenuRequested.connect(self.__show_menu)
        self.ui.listWidget_2.customContextMenuRequested.connect(self.__show_menu)
        self.menu = QMenu(self)
        self.action_rename_shape = QAction(QIcon('images/note.png'), self.tr('修改名称'), self)
        self.action_rename_shape.triggered.connect(self.__rename_shape)
        self.action_delete_shape = QAction(QIcon('images/icon_43.png'), self.tr('删除形状'), self)
        self.action_delete_shape.triggered.connect(self.__del_shape)
        self.menu.addAction(self.action_rename_shape)
        self.menu.addAction(self.action_delete_shape)

        self.__shape_stack = []
        self.cursor = QCursor()
        self.__base_text_temp, self.__combo_text_temp = '', ''  # 用于重命名操作取消时，恢复原来的名称
        self.__combo_text = ''

        self.ui.listWidget.itemClicked.connect(self.__shape_select_stack)
        self.ui.listWidget_2.itemClicked.connect(self.__shape_select_stack)
        self.ui.listWidget.itemDoubleClicked.connect(self.__rename_shape)
        self.ui.listWidget_2.itemDoubleClicked.connect(self.__rename_shape)
        self.ui.listWidget.itemChanged.connect(self.__check_shape_name)
        self.ui.listWidget_2.itemChanged.connect(self.__check_shape_name)
        self.ui.pushButton_union.clicked.connect(self.__add_combo_union)
        self.ui.pushButton_diff.clicked.connect(self.__add_combo_diff)
        self.ui.pushButton_new.clicked.connect(self.__clear_all_shapes)
        self.ui.pushButton_add.clicked.connect(self.__complete_combo_shape)
        signal_draw_sub_shape.signal.connect(self.__add_base_shape)

    def closeEvent(self, event):
        self.__clear_all_shapes()
        stat_flags.ShapeCombo_IsOpened = False
        self.parent().shape_type_reset()

    def __add_base_shape(self, shape_type: str):
        name = shape_type + str(self.ui.listWidget.count() + 1)
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.ui.listWidget.addItem(item)

    def __add_combo_shape(self, combo_str):
        for i in range(self.ui.listWidget_2.count()):
            text = self.ui.listWidget_2.item(i).text().split(': ')[-1]
            if text == combo_str:
                QMessageBox.warning(self, self.tr('重复的名称'), self.tr('"{}"已存在。').format(text))
                return

        name = self.tr('组合') + str(self.ui.listWidget_2.count() + 1) + ': ' + combo_str
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.ui.listWidget_2.addItem(item)

    def __add_combo_diff(self):
        if len(self.__shape_stack) != 2:
            QMessageBox.warning(self, self.tr('数量错误'), self.tr('请选择两个形状。'))
            return

        text1, text2 = self.__shape_stack
        final_text = '(' + text1 + ' - ' + text2 + ')'
        self.__add_combo_shape(final_text)
        self.__set_all_items_not_selected()

    def __add_combo_union(self):
        base_selected = self.ui.listWidget.selectedItems()
        combo_selectd = self.ui.listWidget_2.selectedItems()
        if len(base_selected) + len(combo_selectd) <= 1:
            QMessageBox.warning(self, self.tr('数量错误'), self.tr('请至少选择两个形状。'))
            return

        combo_list = []
        for one_shape in base_selected:
            combo_list.append(f'{one_shape.text().strip()}')
        combo_str = ' + '.join(combo_list)

        ori_list = []
        for one_shape in combo_selectd:
            ori_list.append(one_shape.text().split(': ')[-1])
        ori_str = ' + '.join(ori_list)

        if ori_str and combo_str:
            final_str = '(' + ori_str + ' + ' + combo_str + ')'
        else:
            final_str = '(' + ori_str + combo_str + ')'

        self.__add_combo_shape(final_str)
        self.__set_all_items_not_selected()

    def __check_redu_name(self, list_i, row_i, name):
        for i in range(self.ui.listWidget.count()):
            if list_i == 0 and i == row_i:
                continue

            if name == self.ui.listWidget.item(i).text():
                QMessageBox.warning(self, self.tr('重复的名称'), self.tr('"{}"已存在。').format(name))
                return False

        for i in range(self.ui.listWidget_2.count()):
            if list_i == 1 and i == row_i:
                continue

            if name == self.ui.listWidget_2.item(i).text().split(': ')[0]:
                QMessageBox.warning(self, self.tr('重复的名称'), self.tr('"{}"已存在。').format(name))
                return False

        return True

    def __check_shape_name(self):
        if self.sender() == self.ui.listWidget:
            text = self.ui.listWidget.currentItem().text().strip()
            if self.__check_redu_name(0, self.ui.listWidget.currentRow(), text):
                self.ui.listWidget.blockSignals(True)  # 暂时屏蔽信号，避免setText触发itemChanged信号
                self.ui.listWidget.currentItem().setText(text)
                self.__replace_existed_shape_name(self.__base_text_temp, text)
                self.ui.listWidget.blockSignals(False)
                i, name = self.ui.listWidget.currentRow(), self.ui.listWidget.currentItem().text()
                signal_rename_sub_shape.send([i, name])
            else:
                self.ui.listWidget.blockSignals(True)
                self.ui.listWidget.currentItem().setText(self.__base_text_temp)
                self.ui.listWidget.blockSignals(False)
        elif self.sender() == self.ui.listWidget_2:
            text = self.ui.listWidget_2.currentItem().text().strip()
            if ': ' not in text:
                if self.__check_redu_name(1, self.ui.listWidget_2.currentRow(), text):
                    self.ui.listWidget_2.blockSignals(True)
                    self.ui.listWidget_2.currentItem().setText(text + ': ' + self.__combo_text_temp.split(': ')[-1])
                    self.ui.listWidget_2.blockSignals(False)
                else:
                    self.ui.listWidget_2.blockSignals(True)
                    self.ui.listWidget_2.currentItem().setText(self.__combo_text_temp)
                    self.ui.listWidget_2.blockSignals(False)

    def __clear_all_shapes(self):
        self.ui.listWidget.clear()
        self.ui.listWidget_2.clear()
        self.__shape_stack = []
        signal_shape_combo_reset.send(True)

    def __complete_combo_shape(self):
        combo_selectd = self.ui.listWidget_2.selectedItems()
        if len(combo_selectd) > 1:
            QMessageBox.warning(self, self.tr('组合数量错误'), self.tr('请逐个添加组合形状。'))
            return

        if len(combo_selectd) == 1:
            self.__combo_text = combo_selectd[0].text()
            get_HHL_parent(self).select_cate_tag_before()

    def __cursor_in_base_list(self):
        rect = self.ui.listWidget.rect()
        cursor_rel_pos = self.ui.listWidget.mapFromGlobal(self.cursor.pos())
        return rect.contains(cursor_rel_pos)

    def __cursor_in_combo_list(self):
        rect = self.ui.listWidget_2.rect()
        cursor_rel_pos = self.ui.listWidget_2.mapFromGlobal(self.cursor.pos())
        return rect.contains(cursor_rel_pos)

    def __del_shape(self):
        if self.__cursor_in_base_list():
            cur_text = self.ui.listWidget.currentItem().text()

            choice = QMessageBox.question(self.ui, self.tr('删除组合形状'),
                                          self.tr('所有包含"{}"的组合形状也将被删除，继续吗？').format(cur_text))
            if choice == QMessageBox.Yes:
                self.ui.listWidget.takeItem(self.ui.listWidget.currentRow())
                if cur_text in self.__shape_stack:
                    self.__shape_stack.remove(cur_text)

                for one in self.ui.listWidget_2.findItems(cur_text, Qt.MatchContains):
                    combo_text = one.text()
                    self.ui.listWidget_2.takeItem(self.ui.listWidget_2.row(one))
                    if combo_text in self.__shape_stack:
                        self.__shape_stack.remove(combo_text)

        elif self.__cursor_in_combo_list():
            cur_text = self.ui.listWidget_2.currentItem().text()
            self.ui.listWidget_2.takeItem(self.ui.listWidget_2.currentRow())

            if cur_text in self.__shape_stack:
                self.__shape_stack.remove(cur_text)

    def __replace_existed_shape_name(self, old_name, new_name):
        self.ui.listWidget_2.blockSignals(True)
        for i in range(self.ui.listWidget_2.count()):
            item = self.ui.listWidget_2.item(i)
            if old_name in item.text():
                item.setText(item.text().replace(old_name, new_name))
        self.ui.listWidget_2.blockSignals(False)

        for i, one in enumerate(self.__shape_stack):
            if old_name in one:
                self.__shape_stack[i] = one.replace(old_name, new_name)

        self.__combo_text_temp = self.__combo_text_temp.replace(old_name, new_name)

    def __rename_shape(self):
        if self.sender() == self.ui.listWidget:
            self.__base_text_temp = self.ui.listWidget.currentItem().text()
            self.ui.listWidget.editItem(self.ui.listWidget.currentItem())
        elif self.sender() == self.ui.listWidget_2:
            self.__combo_text_temp = self.ui.listWidget_2.currentItem().text()
            self.ui.listWidget_2.editItem(self.ui.listWidget_2.currentItem())
        elif self.sender() == self.action_rename_shape:
            if self.__cursor_in_base_list():
                self.__base_text_temp = self.ui.listWidget.currentItem().text()
                self.ui.listWidget.editItem(self.ui.listWidget.currentItem())
            elif self.__cursor_in_combo_list():
                self.__combo_text_temp = self.ui.listWidget_2.currentItem().text()
                self.ui.listWidget_2.editItem(self.ui.listWidget_2.currentItem())

        self.__set_all_items_not_selected()

    def __set_all_items_not_selected(self):
        for i in range(self.ui.listWidget.count()):
            self.ui.listWidget.item(i).setSelected(False)

        for i in range(self.ui.listWidget_2.count()):
            self.ui.listWidget_2.item(i).setSelected(False)

        self.__shape_stack = []

    def __shape_select_stack(self):
        if self.sender() == self.ui.listWidget:
            current_text = self.ui.listWidget.currentItem().text()
        else:
            current_text = self.ui.listWidget_2.currentItem().text().split(': ')[-1]

        if current_text in self.__shape_stack:
            self.__shape_stack.remove(current_text)
        else:
            self.__shape_stack.append(current_text)

    def __show_menu(self):  # 在鼠标位置显示菜单, 超出item区域不显示
        show = False

        if self.__cursor_in_base_list():
            if self.ui.listWidget.count() > 0:
                final_item = self.ui.listWidget.item(self.ui.listWidget.count() - 1)
                item_rect = self.ui.listWidget.visualItemRect(final_item)
                cursor_bottom = self.ui.listWidget.mapFromGlobal(self.cursor.pos()).toTuple()[1]
                if cursor_bottom < item_rect.y() + item_rect.height():
                    show = True

        if self.__cursor_in_combo_list():
            if self.ui.listWidget_2.count() > 0:
                final_item = self.ui.listWidget_2.item(self.ui.listWidget_2.count() - 1)
                item_rect = self.ui.listWidget_2.visualItemRect(final_item)
                cursor_bottom = self.ui.listWidget_2.mapFromGlobal(self.cursor.pos()).toTuple()[1]
                if cursor_bottom < item_rect.y() + item_rect.height():
                    show = True

        if show:
            self.menu.exec(self.cursor.pos())

    def combo_text(self):
        return self.__combo_text

    def move_to(self, pos: QPoint):
        self.move(pos)

    def show_at(self, pos: QPoint):
        self.move(pos)
        stat_flags.ShapeCombo_IsOpened = True
        self.show()


if __name__ == '__main__':
    app = QApplication()
    pp = ShapeCombo()
    pp.show()
    app.exec()

# todo: 1.del shape 和rename shape 同步修改已添加的图形
#  2.添加功能
#  3. sub shape的高亮显示，角点移动，整体移动 如何和 基础形状标注、组合标注兼容
