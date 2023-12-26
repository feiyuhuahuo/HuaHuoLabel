#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtCore import QPropertyAnimation, Qt, QRectF, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QStyleOptionButton, QStylePainter, QStyle

from need.custom_widgets import signal_draw_shape_done
from need.custom_signals import BoolSignal
from need.functions import get_HHL_parent
from need.SharedWidgetStatFlags import stat_flags

signal_button_selected_done = BoolSignal()


class PushButtonWaiting(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.fontSize = 12
        self.loading_text = "\uf110"
        self._rotateAnimationStarted = True
        self._rotateAnimation = QPropertyAnimation(self)
        self._rotateAnimation.setTargetObject(self)
        self._rotateAnimation.setStartValue(1)
        self._rotateAnimation.setEndValue(12)
        self._rotateAnimation.setDuration(1200)
        self._rotateAnimation.setLoopCount(-1)  # 无限循环
        self._rotateAnimation.valueChanged.connect(self.update)
        self.clicked.connect(self.__done)
        self.icon_ok = QIcon('images/icon_11.png')
        self.setVisible(False)
        self.__activated = False
        self.__confirmed = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.__change_bg_color)
        self.color_list = ['rgb(198, 221, 241)', 'rgb(189, 215, 238)', 'rgb(176, 208, 235)', 'rgb(156, 196, 230)',
                           'rgb(139, 186, 226)', 'rgb(112, 170, 219)', 'rgb(112, 170, 219)', 'rgb(139, 186, 226)',
                           'rgb(156, 196, 230)', 'rgb(176, 208, 235)', 'rgb(189, 215, 238)', 'rgb(198, 221, 241)']
        self.__color_i = 0
        self.base_ss = ('QPushButton {background-color: rgb(235, 235, 235); border: 1px solid gray; '
                        'border-radius: 4px; padding-left:4px; padding-right:4px;} '
                        'QPushButton:hover {background-color:  rgb(225, 225, 225);} '
                        'QPushButton:pressed {background-color: rgb(215, 215, 215);}')

        signal_draw_shape_done.signal.connect(self.show_button)

    def enterEvent(self, event):
        self._rotateAnimationStarted = False
        self.setIcon(self.icon_ok)
        self.update()

    def leaveEvent(self, event):
        self.setIcon(QIcon())
        self._rotateAnimationStarted = True
        self.update()

    def paintEvent(self, _):
        option = QStyleOptionButton()
        self.initStyleOption(option)
        painter = QStylePainter(self)
        if self._rotateAnimationStarted:
            option.text = ""
        painter.drawControl(QStyle.CE_PushButton, option)
        if not self._rotateAnimationStarted:
            return

        painter.save()
        font = self.font()
        font.setPointSize(self.fontSize)
        font.setFamily("FontAwesome")
        painter.setFont(font)
        # 变换坐标为正中间
        painter.translate(self.rect().center())
        # 旋转90度
        painter.rotate(self._rotateAnimation.currentValue() * 30)
        fm = self.fontMetrics()

        # 在变换坐标后的正中间画文字
        w = fm.size(0, self.loading_text).width()
        h = fm.size(0, self.loading_text).height()
        painter.drawText(QRectF(0 - w * 2 - 2, 0 - h - 2, w * 2 * 2, h * 2), Qt.AlignCenter, self.loading_text)
        painter.restore()

    def __change_bg_color(self):
        if self.__color_i >= len(self.color_list):
            self.timer.stop()

        if self.__color_i < len(self.color_list):
            self.setStyleSheet(self.base_ss.replace('rgb(235, 235, 235)', self.color_list[self.__color_i]))
            self.__color_i += 1

    def __done(self):
        if get_HHL_parent(self).check_warnings('cate_selected'):
            self._rotateAnimation.stop()
            self._rotateAnimationStarted = False
            self.__confirmed = True

            self.setVisible(False)
            if 'cate' in self.objectName():
                stat_flags.PushButtonWaitingCate_IsVisible = False
            elif 'tag' in self.objectName():
                stat_flags.PushButtonWaitingTag_IsVisible = False

            signal_button_selected_done.signal.emit(True)

    def has_confirmed(self):
        return self.__confirmed

    def set_activated(self, activate):
        self.__activated = activate

    def show_button(self):
        if self.__activated:
            self.__confirmed = False
            self._rotateAnimation.start()

            self.setVisible(True)
            if 'cate' in self.objectName():
                stat_flags.PushButtonWaitingCate_IsVisible = True
            elif 'tag' in self.objectName():
                stat_flags.PushButtonWaitingTag_IsVisible = True

            self.__color_i = 0
            self.timer.start(50)  # 背景色变换的时间

# if __name__ == "__main__":
#     from PySide6.QtWidgets import QApplication
#     from PySide6.QtGui import QFontDatabase
#     app = QApplication()
#     QFontDatabase.addApplicationFont('fonts/fontawesome-webfont.ttf')
#     w = PushButtonWaiting()
#     w.show()
#     app.exec()
