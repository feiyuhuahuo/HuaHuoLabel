# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'base_img_window.ui'
##
## Created by: Qt User Interface Compiler version 6.5.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from need.custom_widgets import BaseImgFrame


# ui_files/base_img_window.ui
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(573, 584)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.img_area = BaseImgFrame(self.centralwidget)
        self.img_area.setObjectName(u"img_area")

        self.verticalLayout.addWidget(self.img_area)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setSpacing(40)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(6, -1, 6, -1)
        self.verticalLayout_12 = QVBoxLayout()
        self.verticalLayout_12.setSpacing(0)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.verticalLayout_12.setContentsMargins(0, -1, 0, -1)
        self.label_size_info = QLabel(self.centralwidget)
        self.label_size_info.setObjectName(u"label_size_info")
        self.label_size_info.setMaximumSize(QSize(16777215, 32))
        font = QFont()
        font.setPointSize(10)
        self.label_size_info.setFont(font)

        self.verticalLayout_12.addWidget(self.label_size_info, 0, Qt.AlignBottom)

        self.label_time_info = QLabel(self.centralwidget)
        self.label_time_info.setObjectName(u"label_time_info")
        self.label_time_info.setMaximumSize(QSize(16777215, 32))

        self.verticalLayout_12.addWidget(self.label_time_info, 0, Qt.AlignTop)

        self.horizontalLayout_8.addLayout(self.verticalLayout_12)

        self.label_xyrgb = QLabel(self.centralwidget)
        self.label_xyrgb.setObjectName(u"label_xyrgb")
        self.label_xyrgb.setMinimumSize(QSize(135, 0))
        self.label_xyrgb.setFont(font)

        self.horizontalLayout_8.addWidget(self.label_xyrgb)

        self.horizontalLayout_8.setStretch(0, 10)
        self.horizontalLayout_8.setStretch(1, 2)

        self.verticalLayout.addLayout(self.horizontalLayout_8)

        self.verticalLayout.setStretch(0, 20)
        self.verticalLayout.setStretch(1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.img_area.setText("")
        self.label_size_info.setText(QCoreApplication.translate("MainWindow", u"H: , W: ", None))
        self.label_time_info.setText(QCoreApplication.translate("MainWindow", u"\u521b\u5efa\uff1a", None))
        self.label_xyrgb.setText(QCoreApplication.translate("MainWindow", u"X: , Y:     \n"
                                                                          "R: 100, G: 100, B: 100", None))
    # retranslateUi
