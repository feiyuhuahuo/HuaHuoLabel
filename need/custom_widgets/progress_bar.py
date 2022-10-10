#!/usr/bin/env python 
# -*- coding:utf-8 -*-
from PySide6.QtWidgets import QWidget, QApplication, QVBoxLayout, QProgressBar, QLabel


class ProgressBar(QProgressBar):
    def __init__(self, *args, **kwargs):
        super(ProgressBar, self).__init__(*args, **kwargs)
        self.setValue(0)


class ProgressWindow(QWidget):
    # 如果加入parent参数，并在实例化时传入主窗口，则实例以寄存于主窗口内的控件存在，没有默认的窗口标题，最大化、最小化等按钮，
    # 若不加入parent参数，实例化时作为主窗口的一个属性创建，即self.xxx, 则以一个独立的窗口存在，有默认的窗口标题，最大化、最小化等按钮，
    def __init__(self, title='', text_prefix='', minimum=0, maximum=100):
        super().__init__()

        StyleSheet = """
        /*设置红色进度条*/
        #RedProgressBar {
            text-align: center; /*进度值居中*/
        }
        #RedProgressBar::chunk {
            background-color: #F44336;
        }
        #GreenProgressBar {
            text-align: center;
            min-height: 20px;
            max-height: 20px;
        }
        #GreenProgressBar::chunk {
            background-color: #009688;
        }
        #BlueProgressBar {
            border: 2px solid #2196F3;/*边框以及边框颜色*/
            border-radius: 5px;
            background-color: #E0E0E0;
        }
        #BlueProgressBar::chunk {
            background-color: #2196F3;
            width: 10px; /*区块宽度*/
            margin: 0.5px;
        }
        """

        self.resize(400, 80)
        self.setWindowTitle(title)
        self.text_prefix = text_prefix
        self.info_label = QLabel(self)
        self.info_label.setMaximumHeight(20)
        self.info_label.setText(text_prefix)
        self.progress_bar = ProgressBar(self, minimum=minimum, maximum=maximum,
                                        textVisible=True, objectName="GreenProgressBar")
        self.progress_bar.setStyleSheet(StyleSheet)
        layout = QVBoxLayout(self)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.info_label)

    def set_text(self, text):
        self.info_label.setText(self.text_prefix + text)

    def set_value(self, value):
        self.progress_bar.setValue(value)


if __name__ == "__main__":
    app = QApplication()
    w = ProgressWindow()
    w.show()

    for i in range(60):
        w.set_value(int((i + 1) / 160))
        import time
        time.sleep(0.1)

        w.set_text(f'{i + 1}/160')

    app.exec()
