#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtWidgets import QInputDialog, QPushButton, QMessageBox, QMenu, QWidget, QApplication, QSizePolicy
from PySide6.QtCore import Qt
# from need.utils import AllClasses
from PySide6.QtGui import QIcon, QFont, QAction


class BaseButton(QWidget):
    def __init__(self, parent=None):  # parent=None 必须要实现
        super().__init__(parent)
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)
        self.setFixedHeight(24)
        self.pushButton_look = QPushButton(self)
        self.pushButton_look.setFixedSize(25, 24)
        self.pushButton_look.setIcon(QIcon('../../images/look2.png'))
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
        self.class_button.setMinimumHeight(24)

        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.class_button.setSizePolicy(sizePolicy)
        # self.menu_task = QMenu(self)
        # self.action_load_cls_classes = QAction(main_win.tr('加载类别'), main_win)
        # main_win.action_load_cls_classes.triggered.connect(main_win.load_classes)
        # main_win.menu_task.addAction(main_win.action_load_cls_classes)
        # main_win.action_export_cls_classes = QAction(main_win.tr('导出类别'), main_win)
        # main_win.action_export_cls_classes.triggered.connect(main_win.export_classes)
        # main_win.menu_task.addAction(main_win.action_export_cls_classes)

    def set_look(self):
        if self.pushButton_look.accessibleName() == 'looking':
            self.pushButton_look.setAccessibleName('not_looking')
            self.pushButton_look.setIcon(QIcon('../../images/not_look2.png'))
        else:
            self.pushButton_look.setAccessibleName('looking')
            self.pushButton_look.setIcon(QIcon('../../images/look2.png'))

    def show(self):
        super().show()
        self.setFixedWidth(self.pushButton_look.width() + self.class_button.width() - 2)

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



if __name__ == '__main__':
    app = QApplication()
    img_edit = BaseButton()
    img_edit.show()
    app.exec()
