#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtGui import QIcon, QColor, QCursor, QAction
from PySide6.QtWidgets import QPushButton, QApplication, QWidget, QListWidget, QListWidgetItem, QSizePolicy, \
    QVBoxLayout, QSpacerItem, QCheckBox, QMenu
from need.custom_signals import IntSignal, BoolSignal
from need.custom_widgets import signal_set_shape_list_selected, signal_draw_selected_shape

signal_update_num = IntSignal()
signal_obj_list_folded = BoolSignal()


class ObjList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(118)
        font = self.font()
        font.setPointSize(10)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding))
        self.title_button = QPushButton(self.tr('   标注列表') + f'(0)', self)
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
        self.edit_button.move(80, -5)
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

        self.menu = QMenu(title='label_list_menu', parent=self)
        self.customContextMenuRequested.connect(self.show_menu)
        self.action_modify_cate = QAction(QIcon('images/note.png'), self.tr('修改类别'), self)

        # self.action_modify_cate.triggered.connect(self.modify_obj_list_start)
        self.action_shape = QAction(QIcon('images/icon_43.png'), self.tr('删除标注'), self)
        # self.action_delete_one_shape.triggered.connect(lambda: self.del_all_shapes(False))
        self.action_delete_all = QAction(QIcon('images/no_no.png'), self.tr('全部删除'), self)
        # self.action_delete_all.triggered.connect(lambda: self.del_all_shapes(True))
        self.action_lock_shape = QAction(QIcon('images/locked.png'), self.tr('锁定标注'), self)
        # self.action_lock_shape.triggered.connect(self.lock_shape)

        self.menu.addAction(self.action_modify_cate)
        self.menu.addAction(self.action_shape)
        self.menu.addAction(self.action_delete_all)
        self.menu.addAction(self.action_lock_shape)
        self.menu.setDisabled(True)

    def wheelEvent(self, event):
        if self.edit_button.isEnabled():
            self.edit_button.setChecked(event.angleDelta().y() < 0)

    def __fold_list(self):
        self.obj_list.setVisible(not self.obj_list.isVisible())
        self.resize(self.sizeHint())
        if self.obj_list.isVisible():
            self.parent().layout().setStretch(1, 20)
            self.parent().layout().setStretch(2, 1)
        else:
            self.parent().layout().setStretch(1, 1)
            self.parent().layout().setStretch(2, 20)

    def __update_list_num(self):
        count = self.obj_list.count()
        self.title_button.setText(self.tr('   标注列表') + f'({count})')

    def add_item(self, text, color):
        item = QListWidgetItem(text)
        item.setForeground(QColor(color))
        self.obj_list.addItem(item)
        self.__update_list_num()

    def clear(self):
        self.obj_list.clear()
        self.__update_list_num()

    def del_row(self, row: int):
        self.obj_list.takeItem(row)
        self.__update_list_num()

    def draw_selected_shape(self, i):  # 在标注列表选定当前项时，对应高亮显示图上的标注
        if i == -1:
            if not self.has_locked_shape():
                signal_draw_selected_shape.send(self.obj_list.currentRow())
        else:
            signal_draw_selected_shape.send(i)

    def modify_cur_c(self, new_c: str):
        item = self.obj_list.currentItem()
        item.setText(new_c)

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

    def set_shape_selected(self, i):  # 在图上选定标注时，对应设置标注列表的当前项
        item = self.obj_list.item(i)
        self.obj_list.setCurrentItem(item)
        item.setSelected(True)

    def show_menu(self):  # 在鼠标位置显示菜单
        if not self.edit_button.isChecked():
            self.menu.setDisabled(True)
        else:
            self.menu.setDisabled(False)

        self.menu.exec(QCursor.pos())


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
