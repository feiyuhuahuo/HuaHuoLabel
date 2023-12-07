#!/usr/bin/env python 
# -*- coding:utf-8 -*-

# 用一些标志变量记录控件的一些状态，避免self.parent().xxx这种调用，需单独起一个文件统一管理，避免循环引用。
class WidgetStatFlags:
    def __init__(self):
        self.ShapeCombo_IsOpened = False
        self.PushButtonWaitingCate_IsVisible = False
        self.PushButtonWaitingTag_IsVisible = False


stat_flags = WidgetStatFlags()
