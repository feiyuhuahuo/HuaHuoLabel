#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QApplication


class SelectWindow(QWidget):
    # parent=None必须要实现，否则由其它界面呼起时，好像只能看，其它功能会失灵
    def __init__(self, parent=None, title='窗口', button_signal=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.ui = loader.load('label_window.ui')
        self.ui.setWindowTitle(title)

        self.button_signal = button_signal
        self.ui.listWidget.itemClicked.connect(self.select_seg_label)
        self.ui.pushButton.clicked.connect(self.emit_text)

    def select_seg_label(self):
        self.ui.lineEdit.setText(self.ui.listWidget.currentItem().text())

    def emit_text(self):
        text = self.ui.lineEdit.text().strip()
        if self.button_signal is not None:
            self.button_signal.send(text)


# if __name__ == '__main__':
#     app = QApplication()
#     ui = SelectWindow(title='你好')
#     ui.ui.show()
#     app.exec()
