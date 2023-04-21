#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QPushButton, QApplication


class SearchBox(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        self.setPlaceholderText(self.tr('搜索'))
        self.setFixedSize(180, 24)
        self.setStyleSheet(
            """
            QLineEdit {
            border: 1px solid lightgray;
            border-radius: 5px;
            padding-left: 5px;
            padding-right: 60px;}
            """)

        self.search_btn = QPushButton(self)
        self.search_btn.setIcon(QIcon('../../images/search.png'))
        self.search_btn.setFont(font)
        self.search_btn.setFixedSize(30, self.height())
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.move(self.width() - self.search_btn.width(), 0)
        self.search_btn.setStyleSheet(
            """
            QPushButton {
            background-color: rgb(235, 235, 235);
            color: white; 
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;}

            QPushButton:hover {background-color:rgb(225, 225, 225);}

            QPushButton:pressed {background-color:rgb(215, 215, 215);}
            """
        )


if __name__ == '__main__':
    app = QApplication()
    img_edit = SearchBox()
    img_edit.show()
    app.exec()
