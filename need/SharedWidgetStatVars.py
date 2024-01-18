#!/usr/bin/env python 
# -*- coding:utf-8 -*-

# 用一些标志变量记录控件的一些状态，避免self.parent().xxx这种调用，需单独起一个文件统一管理，避免循环引用。
class WidgetStatVars:
    def __init__(self):
        self.CenterImg_CurrentObj = {}  # 用于目标列表的选中状态发生变化时，按钮组同步显示对应的类别/标签
        self.HHL_Edit_Mode = False
        self.PushButtonWaitingCate_IsVisible = False
        self.PushButtonWaitingTag_IsVisible = False
        self.ShapeCombo_NameRepeated = False
        self.ShapeCombo_IsOpened = False
        self.ShapeCombo_ComboName = ''
        self.ObjList_Modifying_I = -1  # 用于类别列表修改目标类别


stat_vars = WidgetStatVars()
