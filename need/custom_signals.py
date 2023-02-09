#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb

from PySide6.QtCore import QObject, Signal


class BoolSignal(QObject):
    signal = Signal(bool)

    def __init__(self):
        super().__init__()

    def send(self, info):
        self.signal.emit(info)


class IntSignal(QObject):
    signal = Signal(int)

    def __init__(self):
        super().__init__()

    def send(self, info):
        self.signal.emit(info)

    def set_name(self, name):
        self.name = name


class StrSignal(QObject):
    signal = Signal(str)

    def __init__(self, name=None):
        super().__init__()
        self.name = name

    def send(self, info):
        self.signal.emit(info)


class ListSignal(QObject):
    signal = Signal(list)

    def __init__(self, name=None):
        super().__init__()
        self.name = name

    def send(self, info):
        self.signal.emit(info)


class ErrorSignal(QObject):
    signal = Signal(str)

    def write(self, text):
        self.signal.emit(str(text))