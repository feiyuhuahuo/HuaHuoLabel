#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QMenu, QWidget, QApplication, \
    QMainWindow, QHBoxLayout, QLineEdit
from PySide6.QtCore import Qt
# from need.utils import AllClasses
from PySide6.QtGui import QIcon, QFont, QAction, QCursor


class BaseButton(QWidget):
    def __init__(self, parent=None):  # parent=None 必须要实现
        super().__init__(parent)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu(self)
        self.menu.setFixedWidth(90)

        self.action_edit = QAction(QIcon('images/图片14.png'), self.tr('编辑'), self)
        self.action_edit.triggered.connect(self.edit_class)
        self.action_default = QAction(QIcon('images/favorite2.ico'), self.tr('设为默认'), self)
        self.action_default.triggered.connect(self.set_as_default)

        self.action_delete = QAction(QIcon('images/icon_43.png'), self.tr('删除'), self)
        # self.action_delete.triggered.connect(lambda: self.set_interpolation(Qt.FastTransformation))
        self.menu.addAction(self.action_edit)
        self.menu.addAction(self.action_default)
        self.menu.addAction(self.action_delete)

        self.customContextMenuRequested.connect(self.show_menu)

        self.pushButton_look = QPushButton(self)
        self.pushButton_look.setFixedSize(25, 22)
        self.pushButton_look.setIcon(QIcon('images/look/look2.png'))
        self.pushButton_look.setAccessibleName('looking')
        self.pushButton_look.setStyleSheet(
            """
            QPushButton{background-color: rgb(235, 235, 235);
                        border: 1px solid gray;
                        border-top-left-radius: 4px;
                        border-bottom-left-radius: 4px;}
            QPushButton:hover {background-color:  rgb(225, 225, 225);}
            QPushButton:pressed {background-color:  rgb(215, 215, 215);}        
            """
        )
        self.pushButton_look.clicked.connect(self.set_look)

        self.class_button = QPushButton(self)
        self.class_button.setStyleSheet(
            """
            QPushButton {background-color: rgb(235, 235, 235);
                        border: 1px solid gray;
                        border-top-right-radius: 4px;
                        border-bottom-right-radius: 4px;
                        padding-left:5px;
                        padding-right:5px;}
            QPushButton:hover {background-color:rgb(225, 225, 225);}
            QPushButton:pressed {background-color:rgb(215, 215, 215);}
            """
        )

        self.class_button.move(23, 0)
        self.class_button.setMinimumHeight(22)
        self.adjust_size()

    def adjust_size(self):
        self.class_button.setFixedWidth(self.class_button.sizeHint().width())
        self.setFixedWidth(self.class_button.width() + 24)

    def delete(self):
        pass

    def edit_class(self):
        text, is_ok = QInputDialog().getText(self, self.tr('类别名称'), self.tr('请输入类别名称，输入"-"删除当前类别。'),
                                             QLineEdit.Normal)
        if is_ok and text:
            self.class_button.setText(text)
            self.adjust_size()

    def set_as_default(self):
        ss = self.class_button.styleSheet()
        if '3px solid green' in ss:
            self.class_button.setStyleSheet("""
                QPushButton {background-color: rgb(235, 235, 235);
                            border: 1px solid gray;
                            border-top-right-radius: 4px;
                            border-bottom-right-radius: 4px;
                            padding-left:5px;
                            padding-right:5px;}
                QPushButton:hover {background-color:rgb(225, 225, 225);}
                QPushButton:pressed {background-color:rgb(215, 215, 215);}
                """)
            self.action_default.setText(self.tr('设为默认'))
        else:
            self.class_button.setStyleSheet("""
            QPushButton {background-color: rgb(235, 235, 235);
                        border: 1px solid gray;
                        border-top-right-radius: 4px;
                        border-bottom-right-radius: 4px;
                        border-bottom: 3px solid green;
                        padding-left:5px;
                        padding-right:5px;}
                QPushButton:hover {background-color:rgb(225, 225, 225);}
                QPushButton:pressed {background-color:rgb(215, 215, 215);}
                """)
            self.action_default.setText(self.tr('取消默认'))

    def set_look(self):
        if self.pushButton_look.accessibleName() == 'looking':
            self.pushButton_look.setAccessibleName('not_looking')
            self.pushButton_look.setIcon(QIcon('images/look/not_look2.png'))
        else:
            self.pushButton_look.setAccessibleName('looking')
            self.pushButton_look.setIcon(QIcon('images/look/look2.png'))

    def show_menu(self):  # 在鼠标位置显示菜单
        self.menu.exec(QCursor.pos())

    # def show(self):
    #     super().show()
    #     self.setFixedWidth(self.pushButton_look.width() + self.class_button.width() - 2)

    # def mousePressEvent(self, e):
    #     super().mousePressEvent(e)
    #     if e.button() == Qt.RightButton:
    #         ori_text = self.text()
    #         # 如果这里getText()和warning()的parent为self，则会继承这个类的styleSheet
    #         text, is_ok = QInputDialog().getText(self, self.tr('类别名称'),
    #                                              self.tr('请输入类别名称，输入"-"删除当前类别。'),
    #                                              QLineEdit.Normal)
    #         text = text.strip()
    #         if is_ok and text:
    #             if text in AllClasses.classes():
    #                 QMessageBox.warning(self, self.tr('类别重复'), self.tr('类别"{}"已存在。').format(text))
    #
    #             else:
    #                 if ori_text == '-':
    #                     if text != '-':
    #                         self.setText(text)
    #                 else:
    #                     AllClasses.delete(ori_text)
    #                     self.setText(text)
    #
    # def setText(self, text: str):
    #     super().setText(text)
    #     if text != '-':
    #         AllClasses.add(text)


class test_w(QMainWindow):
    def __init__(self):
        super().__init__(parent=None)
        c_w = QWidget(self)
        self.layout = QHBoxLayout()
        pb = QPushButton()
        pb.clicked.connect(self.addd)
        self.layout.addWidget(pb)
        self.layout.addWidget(BaseButton())
        c_w.setLayout(self.layout)
        self.setCentralWidget(c_w)

    def addd(self):
        self.layout.addWidget(BaseButton())


if __name__ == '__main__':
    app = QApplication()
    kk = test_w()
    kk.show()
    # img_edit = BaseButton()
    # img_edit.show()

    app.exec()
