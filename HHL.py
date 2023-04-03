#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json
from need.main import HHL_MainWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QProcess, QTranslator


# QProcess 用py文件调试时无法实现重启，用这个方法代替调试
# import os
# import sys
# def restart():
#     os.execl(sys.executable, 'fake', *[sys.argv[0]])


if __name__ == '__main__':
    app = QApplication()

    with open('project.json', 'r') as f:
        language = json.load(f)['language']

    if language == 'CN':
        app.setStyleSheet('QMessageBox QPushButton[text="&Yes"] {qproperty-text: "确定"}'
                          'QMessageBox QPushButton[text="&No"] {qproperty-text: "取消"}'
                          'QMessageBox QPushButton[text="OK"] {qproperty-text: "确定"}'
                          'QFileDialog QPushButton[text="OK"] {qproperty-text: "确定"}'
                          'QFileDialog QPushButton[text="Cancel"] {qproperty-text: "取消"}'
                          'QInputDialog QPushButton[text="OK"] {qproperty-text: "确定"}'
                          'QInputDialog QPushButton[text="Cancel"] {qproperty-text: "取消"}')
    elif language == 'EN':
        trans_main_window = QTranslator()
        trans_main = QTranslator()
        trans_img_show = QTranslator()
        trans_class_button = QTranslator()

        trans_main_window.load('ts_files/main_window.qm')
        trans_main.load('ts_files/main.qm')
        trans_img_show.load('ts_files/img_show_widget.qm')
        trans_class_button.load('ts_files/class_button.qm')

        app.installTranslator(trans_main_window)
        app.installTranslator(trans_main)
        app.installTranslator(trans_img_show)
        app.installTranslator(trans_class_button)

    ui = HHL_MainWindow()
    ui.show()
    exit_code = app.exec()
    ui.close()
    if exit_code == 99:  # set restart()
        pro = QProcess()
        pro.startDetached(app.applicationFilePath())
