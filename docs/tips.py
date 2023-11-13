#!/usr/bin/env python 
# -*- coding:utf-8 -*-

# 判断某个信号是否已链接
clicked_signal = button.metaObject().method(37)  # 37为信号clicked的索引
if not button.isSignalConnected(clicked_signal):  # 避免信号重复连接
    button.clicked.connect(self.button_action)


def isSignalConnected(obj, name):
    """判断信号是否连接
    :param obj:        对象
    :param name:       信号名，如 clicked()
    """
    index = obj.metaObject().indexOfMethod(name)
    if index > -1:
        method = obj.metaObject().method(index)
        if method:
            return obj.isSignalConnected(method)
    return False
