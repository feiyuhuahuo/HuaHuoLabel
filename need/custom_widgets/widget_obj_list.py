#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import QPushButton, QApplication, QWidget, QListWidget, QListWidgetItem, QSizePolicy, \
    QVBoxLayout, QSpacerItem, QCheckBox
from need.custom_signals import IntSignal, BoolSignal
from need.custom_widgets import signal_set_shape_list_selected, signal_draw_selected_shape
from need.functions import get_HHL_parent

signal_update_num = IntSignal()
signal_obj_list_folded = BoolSignal()


class ObjList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(118)
        font = self.font()
        font.setPointSize(10)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.title_button = QPushButton(self.tr('     标注列表'), self)
        self.title_button.setFont(font)
        self.title_button.setFixedWidth(118)
        self.title_button.setStyleSheet('QPushButton '
                                        '{background-color: rgb(210, 230, 245);'
                                        'text-align: left;'
                                        'border-top: 1px solid gray;'
                                        'border-left: 1px solid gray;'
                                        'border-right: 1px solid gray;'
                                        'border-bottom: none;'
                                        'border-top-left-radius: 8px;'
                                        'border-top-right-radius: 8px;'
                                        'padding: 1px;}'
                                        'QPushButton:hover {background-color:  rgb(190, 210, 225);}'
                                        'QPushButton:pressed { background-color:  rgb(180, 200, 210);}')
        self.title_button.clicked.connect(self.__fold_list)

        self.edit_button = QCheckBox(self)
        self.edit_button.move(78, -5)
        self.edit_button.setStyleSheet('QCheckBox::indicator {padding-top: 1px; width: 40px; height: 26px;}'
                                       'QCheckBox::indicator:unchecked {image: url(images/switch_off.png);}'
                                       'QCheckBox::indicator:checked {image: url(images/switch_on.png);}')
        self.edit_button.setToolTip(self.tr('修改标注'))
        self.edit_button.setDisabled(True)

        self.obj_list = QListWidget(self)
        self.obj_list.setFixedWidth(118)
        self.obj_list.setFont(font)
        self.obj_list.setStyleSheet(
            """
                QListWidget {
                    background-color: rgb(255, 255, 255);
                    alternate-background-color: rgb(242, 242, 242);
                    border: 1px solid rgb(180, 180, 180);
                    border-bottom-left-radius: 8px;
                    border-bottom-right-radius: 8px;
                    outline: none;
                }
                
                QListWidget::item:selected {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                
                QListWidget::item:hover {
                    background-color: rgba(0, 0, 0, 10%);
                    color: rgb(0, 0, 0);
                }
                
                QListWidget::item:disabled {
                    color: rgb(170, 170, 170);
                }
                
                QListWidget::item:selected:!active {
                    background-color: rgb(0, 99, 177);
                    color: rgb(255, 255, 255);
                }
                
                QListWidget::item:selected:active {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                
                QListWidget::item:selected:disabled {
                    background-color: rgba(0, 0, 0, 10%);
                    color: rgb(170, 170, 170);
                }
            """)

        self.icon_look = QIcon('images/look/look2.png')
        self.icon_look_key = self.icon_look.cacheKey()
        self.icon_unlook = QIcon('images/look/not_look2.png')
        self.icon_unlook_key = self.icon_unlook.cacheKey()
        self.icon_shape_locked = QIcon('images/locked.png')
        self.obj_list.itemClicked.connect(lambda: self.draw_selected_shape(i=-1))
        signal_set_shape_list_selected.signal.connect(self.set_shape_selected)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_button)
        layout.addWidget(self.obj_list)
        self.setLayout(layout)

    def wheelEvent(self, event):
        if self.edit_button.isEnabled():
            self.edit_button.setChecked(event.angleDelta().y() < 0)

    def add_item(self, text, color):
        item = QListWidgetItem(text)
        item.setForeground(QColor(color))
        self.obj_list.addItem(item)
        self.update_list_num()

    def clear(self):
        self.obj_list.clear()
        self.update_list_num()

    def del_row(self, row: int):
        self.obj_list.takeItem(row)
        self.update_list_num()

    def __fold_list(self):
        self.obj_list.setVisible(not self.obj_list.isVisible())
        self.resize(self.sizeHint())
        if self.obj_list.isVisible():
            self.parent().layout().setStretch(1, 20)
            self.parent().layout().setStretch(2, 1)
        else:
            self.parent().layout().setStretch(1, 1)
            self.parent().layout().setStretch(2, 20)

    def modify_cur_c(self, new_c: str):
        item = self.obj_list.currentItem()
        item.setText(new_c)

    def set_look(self, item: QListWidgetItem):
        item.setIcon(self.icon_look)

    def set_unlook(self, item: QListWidgetItem):
        item.setIcon(self.icon_unlook)

    def set_looking(self, double_click=False):
        item = self.obj_list.currentItem()

        if double_click:
            item.setIcon(self.icon_look)
            row = self.obj_list.currentRow()
            count = self.obj_list.count()
            for i in range(count):
                if i != row:
                    self.obj_list.item(i).setIcon(self.icon_unlook)
        else:
            if item.icon().cacheKey() == self.icon_look_key:
                item.setIcon(self.icon_unlook)
            elif item.icon().cacheKey() == self.icon_unlook_key:
                item.setIcon(self.icon_look)

    def looking_all(self):
        for i in range(self.obj_list.count()):
            item = self.obj_list.item(i)
            if item.icon().cacheKey() == self.icon_unlook_key:
                return False
        return True

    def looking_classes(self):
        classes = []
        for i in range(self.obj_list.count()):
            item = self.obj_list.item(i)
            if item.icon().cacheKey() == self.icon_look_key:
                classes.append(item.text())

        return classes

    def set_name(self, name):
        self.name = name

    def update_list_num(self):
        pass
        # signal_update_num.set_name(self.name)
        # signal_update_num.send(self.obj_list.count())

    def has_locked_shape(self):
        for i in range(self.obj_list.count()):
            item = self.obj_list.item(i)
            if item.icon().cacheKey() != 0:
                return item
        return False

    def set_shape_locked(self, item: QListWidgetItem):
        item.setIcon(self.icon_shape_locked)
        self.draw_selected_shape(self.obj_list.row(item))

    def set_shape_unlocked(self, item: QListWidgetItem):
        item.setIcon(QIcon())

    def draw_selected_shape(self, i):  # 在标注列表选定当前项时，对应高亮显示图上的标注
        if i == -1:
            if not self.has_locked_shape():
                signal_draw_selected_shape.send(self.obj_list.currentRow())
        else:
            signal_draw_selected_shape.send(i)

    def set_shape_selected(self, i):  # 在图上选定标注时，对应设置标注列表的当前项
        item = self.obj_list.item(i)
        self.obj_list.setCurrentItem(item)
        item.setSelected(True)


if __name__ == '__main__':
    app = QApplication()
    bb = QWidget()
    ly = QVBoxLayout()

    img_edit = ObjList()
    ly.addWidget(QPushButton())
    ly.addWidget(img_edit)
    ly.addItem(QSpacerItem(0, 0))
    ly.setStretch(0, 1)
    ly.setStretch(1, 1)
    ly.setStretch(2, 10)
    # ly.addItem(QSpacerItem(0, 30))
    bb.setLayout(ly)
    bb.show()

    app.exec()
