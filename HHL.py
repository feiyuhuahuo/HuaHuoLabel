#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import json

from need.main import HHL_MainWindow, signal_init_message, signal_init_done
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QFontDatabase, QMovie
from PySide6.QtCore import QProcess, QTranslator, Qt, QSize


# QProcess 用py文件调试时无法实现重启，用这个方法代替调试
# import os
# import sys
# def restart():
#     os.execl(sys.executable, 'fake', *[sys.argv[0]])

class Gif_Splash(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.movie = QMovie('images/splash.gif')
        self.movie.frameChanged.connect(self.onFrameChanged)
        self.movie.start()
        signal_init_message.signal.connect(self.show_message)
        signal_init_done.signal.connect(self.finish)

    def onFrameChanged(self):
        self.setPixmap(self.movie.currentPixmap().scaled(QSize(833, 400), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def show_message(self, message):
        self.showMessage(message, Qt.AlignHCenter | Qt.AlignBottom, Qt.black)

    def finish(self, widget):
        self.movie.stop()
        super().finish(widget)


if __name__ == '__main__':
    app = QApplication()

    splash_screen = Gif_Splash()
    splash_screen.show()

    QFontDatabase.addApplicationFont('fonts/fontawesome-webfont.ttf')

    with open('project.json', 'r') as f:
        language = json.load(f)['language']
        if language == 'CN':
            app.setStyleSheet(
                'QMessageBox QPushButton[text="&Yes"] {qproperty-text: "确定"}'
                'QMessageBox QPushButton[text="&No"] {qproperty-text: "取消"}'
                'QMessageBox QPushButton[text="OK"] {qproperty-text: "确定"}'
                'QFileDialog QPushButton[text="OK"] {qproperty-text: "确定"}'
                'QFileDialog QPushButton[text="Cancel"] {qproperty-text: "取消"}'
                'QInputDialog QPushButton[text="OK"] {qproperty-text: "确定"}'
                'QInputDialog QPushButton[text="Cancel"] {qproperty-text: "取消"}'
            )
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
    # ui.close()  # todo:  为什么需要这句？？, 因为重启功能吗
    if exit_code == 99:  # set restart()
        pro = QProcess()
        pro.startDetached(app.applicationFilePath())
