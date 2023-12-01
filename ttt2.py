#!/usr/bin/env python
# -*- coding: utf-8 -*-
import random
import sys
import time

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtGui import QPixmap, QImageReader, QImage
from PySide6.QtCore import QRect, QSize


class ImageDisplay(QWidget):
    def __init__(self):
        super().__init__()
        label = QLabel(self)
        image_reader = QImageReader("images/test_imgs/1_2.jpg")
        image_reader.setAllocationLimit(512)

        # image_reader = QImageReader("images/test_imgs/rgba.png")
        print(image_reader.canRead())
        print(image_reader.size())

        image_reader.setClipRect(QRect(100, 100, 200, 600))
        image_reader.setScaledSize(QSize(500, 800))

        partial_image = image_reader.read()
        print(partial_image.isNull())
        aa = QPixmap(partial_image)
        label.setPixmap(aa)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageDisplay()
    window.show()
    sys.exit(app.exec())
