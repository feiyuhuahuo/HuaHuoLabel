#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import random

from PySide6.QtGui import QUndoCommand, QColor
from need.custom_widgets import CustomMessageBox

COlOR_Ms = [['青绿', (33, 90, 89), '凌霄橙', (237, 114, 63)], ['松绿', (61, 96, 54), '草黄', (177, 129, 81)],
            ['石榴红', (219, 8, 53), '桂黄', (237, 160, 31)], ['淡紫2', (165, 154, 202), '紫罗兰', (95, 71, 154)],
            ['绥蓝', (111, 155, 198), '雄黄', (243, 153, 58)], ['太师青', (85, 118, 123), '黄白', (233, 209, 181)],
            ['萼绿', (1, 73, 70), '缙红', (143, 52, 48)], ['青雀戴', (21, 60, 70), '琥珀黄', (249, 180, 0)],
            ['淡紫', (161, 114, 208), '锦粉', (248, 198, 181)], ['朱颜红', (239, 133, 109), '浅白', (223, 215, 194)],
            ['法蓝', (41, 175, 212), '皮肤粉', (231, 194, 202)], ['蓝绿', (135, 192, 202), '红白', (240, 207, 227)],
            ['酒蓝', (30, 59, 122), '珊瑚红', (202, 70, 47)], ['淡竹绿', (108, 169, 132), '秋波蓝', (138, 188, 209)],
            ['青雀戴', (21, 60, 70), '金红', (238, 120, 31)], ['海棠红', (219, 91, 108), '粉红', (255, 179, 167)],
            ['抹茶绿', (113, 152, 71), '玉白', (248, 247, 240)], ['浅松绿', (132, 192, 190), '竹绿', (27, 167, 132)],
            ['锦粉', (248, 198, 181), '深咖', (86, 66, 50)], ['风信紫', (195, 166, 203), '粉白', (255, 200, 222)],
            ['珠红', (210, 57, 24), '水碧', (128, 164, 146)], ['甘石粉', (234, 220, 214), '落霞红', (207, 72, 19)],
            ['中国红', (195, 39, 43), '黛绿', (66, 102, 102)], ['珍珠白', (229, 223, 213), '藤萝紫', (124, 115, 159)],
            ['鸭绿', (20, 102, 84), '赤橘', (240, 85, 16)], ['银白', (237, 237, 237), '瓦松绿', (107, 135, 112)],
            ['桃夭', (247, 189, 203), '桔梗蓝', (84, 86, 162)], ['银白', (237, 237, 237), '荷叶绿', (140, 184, 131)],
            ['淡黄白', (224, 223, 198), '朱柿', (237, 109, 70)], ['欧碧', (192, 214, 149), '黑朱', (112, 105, 93)],
            ['盈粉', (249, 211, 227), '玄红', (107, 84, 88)], ['凝脂白', (245, 242, 233), '灰绿', (134, 144, 138)],
            ['法翠', (16, 139, 150), '奶油黄', (234, 216, 154)], ['鹤顶红', (210, 71, 53), '女贞黄', (247, 238, 173)],
            ['金黄', (250, 192, 61), '黑蓝', (44, 47, 59)], ['朱颜红2', (242, 154, 118), '奶油黄2', (237, 241, 187)],
            ['凝脂白', (245, 242, 233), '天水碧', (90, 164, 174)], ['墙红', (207, 146, 158), '黄绿', (227, 235, 152)],
            ['浅黑', (48, 48, 48), '金橘', (253, 110, 0)], ['紫禁红', (164, 47, 31), '黄琉璃', (232, 168, 75)],
            ['墙蓝', (0, 88, 173), '白垩', (223, 224, 219)], ['深巧', (76, 33, 27), '嫣红', (255, 113, 127)],
            ['朱颜红3', (252, 148, 108), '灰青', (169, 211, 206)], ['千山翠', (102, 126, 113), '米白', (239, 234, 215)],
            ['抹茶绿', (107, 140, 51), '落叶黄', (254, 190, 0)], ['紫薇粉', (231, 192, 190), '青瓷绿', (127, 192, 161)],
            ['朱阳', (195, 0, 46), '浅黑2', (39, 41, 43)], ['黛紫', (84, 63, 99), '紫薯紫', (180, 162, 232)],
            ['蜜桃粉', (239, 148, 146), '苹果绿', (151, 195, 61)], [(228, 71, 87), (91, 55, 139), (56, 31, 73)],
            [(160, 36, 103), (239, 193, 182), (53, 49, 102)], [(210, 105, 142), (114, 131, 190), (255, 202, 186)],
            [(230, 20, 55), (255, 112, 66), (255, 200, 140)], [(254, 168, 44), (244, 195, 23), (77, 59, 45)],
            [(25, 28, 37), (195, 61, 26), (253, 219, 198)], [(43, 71, 113), (248, 95, 89), (247, 183, 151)],
            [(67, 48, 41), (254, 203, 64), (185, 144, 123)], [(24, 29, 47), (253, 205, 145), (222, 164, 81)],
            [(13, 103, 161), (114, 148, 194), (190, 199, 217)], [(23, 46, 89), (60, 75, 108), (184, 168, 159)],
            [(62, 49, 74), (254, 51, 54), (255, 157, 82)], [(62, 94, 132), (212, 198, 166), (234, 221, 208)],
            [(49, 87, 123), (253, 239, 208), (255, 243, 187)], [(48, 59, 84), (253, 243, 217), (159, 143, 144)],
            [(129, 112, 164), (232, 145, 159), (255, 198, 97)], [(217, 177, 175), (150, 161, 176), (226, 221, 224)],
            [(42, 119, 170), (245, 92, 151), (43, 97, 140)],
            ]

# CSS 通用color
COlOR_NAMEs = ['black', 'blue', 'blueviolet', 'brown', 'burlywood',
               'cadetblue', 'chocolate', 'coral', 'crimson', 'cyan',
               'darkblue', 'darkcyan', 'darkgoldenrod', 'darkgreen', 'darkkhaki', 'darkolivegreen',
               'darkorange', 'darksalmon', 'darkseagreen', 'darkslategray', 'darkturquoise',
               'darkviolet', 'deeppink', 'deepskyblue', 'dimgray',
               'fuchsia',
               'gold', 'goldenrod', 'gray', 'green',
               'hotpink',
               'indianred', 'indigo',
               'khaki',
               'lawngreen', 'lightblue', 'lightcoral', 'lightgreen', 'lightpink', 'lightsalmon', 'lightseagreen',
               'lightskyblue', 'lightslategray', 'lightsteelblue', 'lime', 'limegreen',
               'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid', 'mediumseagreen',
               'mediumslateblue', 'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 'midnightblue',
               'olive', 'orangered', 'orchid',
               'palevioletred', 'peachpuff', 'peru', 'pink', 'plum', 'purple',
               'red', 'rosybrown', 'royalblue',
               'saddlebrown', 'sienna', 'silver', 'steelblue',
               'tan', 'teal', 'thistle',
               'violet',
               'wheat',
               'yellowgreen']


class AnnUndo(QUndoCommand):
    def __init__(self, board, undo_img, parent=None):
        super().__init__(parent)
        self.board = board
        self.undo_img = undo_img
        self.setText('undo paint')

    def redo(self):
        pass

    def undo(self):
        self.board.scaled_img = self.undo_img
        self.board.scaled_img_painted = self.board.scaled_img.copy()
        self.board.update()


class ClassStatistic:
    def __init__(self):
        self.__classes = []

    def add(self, category, color='none'):
        for one in self.__classes:
            if one[0] == category:
                return

        self.__classes.append([category, color])

    def change_c(self, old_c, new_c):
        for one in self.__classes:
            if one[0] == old_c:
                one[0] = new_c

    def delete(self, c):
        if type(c) == int:
            self.__classes.pop(c)
        elif type(c) == str:
            for i, one in enumerate(self.__classes):
                if one[0] == c:
                    self.__classes.pop(i)

    def classes(self):
        return [aa[0] for aa in self.__classes]

    def colors(self):
        return [aa[1] for aa in self.__classes]

    def class_at(self, i):
        return self.__classes[i][0]

    def color_at(self, i):
        return self.__classes[i][1]

    def clear(self):
        self.__classes = []

    def __len__(self):
        return len(self.__classes)


class Palette:
    def __init__(self):
        self.color_names = COlOR_NAMEs.copy()
        self.color_codes = {}
        for one in COlOR_NAMEs:
            self.color_codes[QColor(one).name()] = one

    def get_color(self):
        random.shuffle(self.color_names)
        existed_colors = INS_all_classes.colors()
        color = self.color_names.pop()
        while color in existed_colors:
            if len(self.color_names) == 0:
                self.color_names = COlOR_NAMEs.copy()
            color = self.color_names.pop()
        return color


class ShapeType:
    def __init__(self):
        self.shape_type = {'多边形': 'Polygon', '矩形': 'Rectangle', '椭圆形': 'Ellipse', '像素': 'Pixel', '组合': 'Combo'}

    def __call__(self, name):
        if type(name) == str:
            name = [name]

        result = []
        for one in name:
            result.append(one)
            result.append(self.shape_type[one])

        return result


class MonitorVariable:
    def __init__(self, parent):
        self.parent = parent
        self._train_num = 0
        self._val_num = 0

    @property
    def train_num(self):
        return self._train_num

    @train_num.setter
    def train_num(self, value):
        self._train_num = value
        self.set_tv_bar()

    @property
    def val_num(self):
        return self._train_num

    @val_num.setter
    def val_num(self, value):
        self._val_num = value
        self.set_tv_bar()

    def set_tv_bar(self):
        total_num = self._train_num + self._val_num
        if total_num:
            self.parent.label_train.set_tv(self._train_num, self._val_num)
            self.parent.label_val.set_tv(self._train_num, self._val_num)


# INS开头表示整个项目的全局对象
INS_all_classes = ClassStatistic()
INS_palette = Palette()
INS_shape_type = ShapeType()
# INS_large_img_warn = CustomMessageBox('information', 'HuaHuoLabel')
