#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QMenu, QFileDialog, QInputDialog, QMessageBox, QLineEdit, QWidget, \
    QHBoxLayout, QColorDialog, QListWidgetItem, QApplication, QGroupBox
from PySide6.QtCore import Qt, QTranslator

class AutoInference(QMainWindow):
    def __init__(self, work_mode):
        super().__init__()
