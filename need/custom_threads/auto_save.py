#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import time
from PySide6.QtCore import QThread
from need.custom_signals import BoolSignal

signal_auto_save = BoolSignal()


class AutoSave(QThread):
    def __init__(self, interval):
        super().__init__()
        self.save_interval = interval

    def run(self):
        while True:
            time.sleep(self.save_interval)
            signal_auto_save.send(True)
