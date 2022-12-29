#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from need.main import ImgCls
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QProcess


# QProcess 用py文件调试时无法实现重启，用这个方法代替调试
# import os
# import sys
# def restart():
#     os.execl(sys.executable, 'fake', *[sys.argv[0]])


if __name__ == '__main__':
    app = QApplication()
    ui = ImgCls()
    ui.show()
    exit_code = app.exec()
    ui.close()
    if exit_code == 99:
        # restart()
        pro = QProcess()
        pro.startDetached(app.applicationFilePath())
