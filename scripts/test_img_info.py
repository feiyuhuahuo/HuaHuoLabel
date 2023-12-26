#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import glob
import pdb
import time
import cv2
import numpy as np
from PIL import Image, ImageOps, ExifTags

Image.MAX_IMAGE_PIXELS = None

img = Image.open('D:\Data\SIC_D/test/3.1.jpg')
exif = img.getexif()
exif = {ExifTags.TAGS[k]: v for k, v in exif.items() if k in ExifTags.TAGS}
orientation = exif.get('Orientation', None)
print('rotation: ', orientation)
print('w, h: ', img.size)
