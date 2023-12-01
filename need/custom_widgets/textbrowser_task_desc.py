#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from need.functions import get_HHL_parent
from PySide6.QtWidgets import QTextBrowser


class TaskDescBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)

    def focusOutEvent(self, ev):
        super().focusOutEvent(ev)
        get_HHL_parent(self).task_desc_edit(self.toPlainText())
