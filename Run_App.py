#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from need.main import ImgCls
from PySide6.QtWidgets import QApplication


if __name__ == '__main__':
    app = QApplication()
    ui = ImgCls()
    app.exec()
