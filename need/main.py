import glob
import math
import pdb
import shutil
import cv2
import numpy as np
import os
import json
import onnxruntime as ort
import sys

from random import shuffle
from os import path as osp
from os.path import sep as os_sep
from PIL import Image, ImageEnhance
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QMenu, QFileDialog, QInputDialog, QMessageBox, QLineEdit, QWidget, \
    QHBoxLayout, QColorDialog, QListWidgetItem, QApplication, QGroupBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QPixmap, QImage, QColor, QFontMetrics, QIcon, QAction
from need.custom_widgets import *
from need.custom_widgets.marquee_label import signal_show_plain_img, signal_show_label_img
from need.custom_widgets.img_show_widget import signal_shape_type, signal_xy_color2ui, signal_selected_shape, \
    signal_del_shape, signal_selected_label_item, signal_open_label_window, signal_one_collection_done, \
    BaseImgFrame, signal_move2new_folder
from need.custom_signals import StrSignal, ErrorSignal
from need.custom_threads.seg_auto_inference import signal_progress_text, signal_progress_value, signal_progress_done, \
    RunInference
from need.custom_threads.seg_change_one_class_json import ChangeOneClassJsons, signal_cocj_done
from need.custom_threads.seg_delete_one_class_json import DeleteOneClassJsons, signal_docj_done
from need.utils import ClassStatDict, ColorNames, ColorCode, get_seg_mask, path_to, uniform_path, \
    qimage_to_array, get_datetime

signal_select_ui_ok_button = StrSignal()
error2app = ErrorSignal()


# noinspection PyUnresolvedReferences
class ImgCls(QMainWindow):
    def __init__(self):
        super().__init__()
        self.WorkMode = '单类别分类'  # ('单类别分类', '多类别分类', '目标检测', '分割')
        self.ImgHoldOn = False
        self.LabelUiCallByMo = False  # 用于区分self.label_ui是由新标注唤起还是由修改标注唤起
        self.OneFileLabel = True

        self.img_root_path = ''  # 图片根目录
        self.task = ''
        self.imgs = []
        self.label_file_dict = {}
        self.tv_imgs = []
        self.tv_i = 0
        self.img_num = 0
        self.cur_i = 0
        self.marquee_num = 20  # 小图的最大数量, 越大占用内存越多
        self.marquee_size = 150
        self.cur_mar_i = -1  # 当前小图的索引，最小有效值为0
        self.mcls_default_c = ''  # 多类别分类的默认类别
        self.cv2_img = None
        self.cv2_img_changed = None
        self.cls_op_track = []
        self.bottom_img_text = ''
        self.icon_look = QIcon('images/图片100.png')
        self.icon_look_key = self.icon_look.cacheKey()
        self.icon_not_look = QIcon('images/图片101.png')
        self.icon_not_look_key = self.icon_not_look.cacheKey()
        self.looking_classes = []
        self.looking_all = True

        self.window_marquee_img = None
        self.window_marquee_label = None
        self.window_train_val_img = None
        self.window_train_val_png = None
        self.window_compare = None
        self.window_auto_infer_progress = None

        self.pinned_images = []  # todo

        self.file_select_dlg = QFileDialog(self)
        self.input_dlg = QInputDialog(self)

        loader = QUiLoader()
        loader.registerCustomWidget(ImgShow)
        loader.registerCustomWidget(ClassButton)
        self.main_ui = loader.load('main_window.ui')  # 主界面
        self.label_ui = SelectWindow(title='类别', button_signal=signal_select_ui_ok_button)

        self.setCentralWidget(self.main_ui)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle('图片处理工具')
        self.setWindowIcon(QIcon('images/icon.ico'))
        self.resize(1200, 900)

        # sys.stderr = error2app
        self.init_menu()
        self.connect_signals()
        self.show()
        # 放在show()之后的操作
        self.main_ui.img_widget.paint_img('images/bg.png')

    def init_button_group(self, buttons: QGroupBox, txt_path):  # 初始化类别按钮组
        buttons = buttons.layout()
        with open(txt_path, 'r', encoding='utf-8') as f:
            categories = [aa.strip() for aa in f.readlines()]

        for i in range(buttons.rowCount()):
            for j in range(buttons.columnCount()):
                button = buttons.itemAtPosition(i, j).wid
                if categories:
                    cate = categories.pop(0)
                    button.setText(cate)
                    ClassStatDict.setdefault(cate, 0)
                else:
                    button.setText('-')

                clicked_signal = button.metaObject().method(37)  # 37为信号clicked的索引
                if not button.isSignalConnected(clicked_signal):  # 避免信号重复连接
                    button.clicked.connect(self.button_action)

    def init_menu(self):
        self.main_ui.action_get_sub_seg_png.triggered.connect(self.get_sub_seg_png)
        self.main_ui.action_mc_mr.triggered.connect(self.remove_mc_mr)

        self.menu_task = QMenu(self)
        self.main_ui.groupBox_1.customContextMenuRequested.connect(lambda: self.show_menu(self.menu_task))
        self.main_ui.groupBox_2.customContextMenuRequested.connect(lambda: self.show_menu(self.menu_task))
        self.menu_task.addAction('加载按钮').triggered.connect(self.buttons_load)
        self.menu_task.addAction('保存按钮').triggered.connect(self.buttons_save)
        self.menu_task.addAction('增加一行').triggered.connect(self.buttons_add_line)
        self.menu_task.addAction('删减一行').triggered.connect(self.buttons_remove_line)

        self.menu_seg_class = QMenu(self)
        self.main_ui.listWidget.customContextMenuRequested.connect(lambda: self.show_menu(self.menu_seg_class))
        self.menu_seg_class.addAction('加载类别').triggered.connect(self.load_seg_classes)
        self.menu_seg_class.addAction('导出类别').triggered.connect(self.export_seg_classes)

        self.action_modify_one_class_jsons = QAction('修改类别', self)
        self.action_modify_one_class_jsons.triggered.connect(self.change_one_class_jsons)
        self.action_modify_one_class_jsons.setDisabled(True)
        self.menu_seg_class.addAction(self.action_modify_one_class_jsons)

        self.action_del_one_class_jsons = QAction('删除类别', self)
        self.action_del_one_class_jsons.triggered.connect(self.delete_one_class_jsons)
        self.action_del_one_class_jsons.setDisabled(True)
        self.menu_seg_class.addAction(self.action_del_one_class_jsons)

        self.menu_seg_annotation = QMenu(self)
        self.main_ui.listWidget_2.customContextMenuRequested.connect(lambda: self.show_menu(self.menu_seg_annotation))
        self.action_modify_one_shape_class = QAction('修改类别', self)
        self.action_modify_one_shape_class.setDisabled(True)
        self.action_modify_one_shape_class.triggered.connect(self.modify_seg_class_1)
        self.action_delete_one_shape = QAction('删除标注', self)
        self.action_delete_one_shape.setDisabled(True)
        self.action_delete_one_shape.triggered.connect(self.main_ui.img_widget.del_polygons)
        self.menu_seg_annotation.addAction(self.action_modify_one_shape_class)
        self.menu_seg_annotation.addAction(self.action_delete_one_shape)

        self.menu_img_enhance = QMenu(self)
        self.main_ui.groupBox.customContextMenuRequested.connect(lambda: self.show_menu(self.menu_img_enhance))
        self.menu_img_enhance.addAction('还原').triggered.connect(self.img_enhance_reset)
        self.action_hold_on = QAction('切图保持', self)
        self.action_hold_on.triggered.connect(self.img_hold_on)
        self.menu_img_enhance.addAction(self.action_hold_on)

        self.marquees = QWidget(self)
        self.marquees_layout = QHBoxLayout()
        self.marquees_layout.addStretch()
        self.marquees.setLayout(self.marquees_layout)
        self.main_ui.scrollArea.setWidget(self.marquees)

        # 工具栏和状态栏
        # self.main_ui.toolbar = self.main_ui.addToolBar('toolbar')
        # tool_show_png = QAction('查看分割标注', self)
        # tool_show_png.triggered.connect(self.show_seg_png)
        # self.main_ui.toolbar.addAction(tool_show_png)
        # self.main_ui.statusBar().showMessage('Ready')

    def connect_signals(self):
        self.main_ui.pushButton.clicked.connect(self.open_dir)
        self.main_ui.pushButton_stat.clicked.connect(self.show_class_statistic)
        self.main_ui.pushButton_pen_color.clicked.connect(self.change_pen_color)
        self.main_ui.pushButton_35.clicked.connect(self.undo_painting)
        self.main_ui.pushButton_36.clicked.connect(self.save_ann_img)
        self.main_ui.pushButton_37.clicked.connect(self.change_font_color)
        self.main_ui.pushButton_39.clicked.connect(self.change_pen_color)
        self.main_ui.pushButton_40.clicked.connect(self.clear_painted_img)
        self.main_ui.pushButton_50.clicked.connect(self.set_m_cls_default_c)
        self.main_ui.pushButton_81.clicked.connect(self.img_rotate)
        self.main_ui.pushButton_82.clicked.connect(lambda: self.img_flip(h_flip=True))
        self.main_ui.pushButton_83.clicked.connect(lambda: self.img_flip(v_flip=True))
        self.main_ui.pushButton_90.clicked.connect(lambda: self.scan_img(last=True))
        self.main_ui.pushButton_91.clicked.connect(lambda: self.scan_img(next=True))
        self.main_ui.pushButton_92.clicked.connect(lambda: self.del_img(del_path=None))
        self.main_ui.pushButton_100.clicked.connect(self.show_compare_img)
        self.main_ui.pushButton_101.clicked.connect(self.cls_back)
        self.main_ui.pushButton_136.clicked.connect(self.save_edited_img)
        self.main_ui.pushButton_137.clicked.connect(lambda: self.save_edited_img(save_all=True))
        self.main_ui.pushButton_auto_infer.clicked.connect(self.auto_inference)
        self.main_ui.pushButton_g_val.clicked.connect(self.copy_img_to_val)
        self.main_ui.pushButton_g_train.clicked.connect(self.copy_img_to_train)
        self.main_ui.pushButton_update_tv.clicked.connect(self.update_train_val)
        self.main_ui.pushButton_show_tv.clicked.connect(self.show_train_val_label)
        self.main_ui.pushButton_pin.clicked.connect(self.pin_unpin_image)
        self.main_ui.pushButton_pin_last.clicked.connect(lambda: self.pin_jump(last=True))
        self.main_ui.pushButton_pin_next.clicked.connect(lambda: self.pin_jump(next=True))
        self.main_ui.pushButton_jump.clicked.connect(self.img_jump)
        self.main_ui.pushButton_search.clicked.connect(self.img_search)
        self.main_ui.spinBox.valueChanged.connect(self.change_pen_size)
        self.main_ui.spinBox_5.valueChanged.connect(self.change_font_size)
        self.main_ui.spinBox_6.valueChanged.connect(self.change_pen_size)
        self.main_ui.radioButton_read.toggled.connect(self.set_read_mode)
        self.main_ui.tabWidget.currentChanged.connect(self.set_work_mode)
        self.main_ui.checkBox_2.toggled.connect(self.set_one_file_label)
        self.main_ui.checkBox_seg_edit.toggled.connect(self.set_seg_edit_mode)
        self.main_ui.toolBox.currentChanged.connect(self.set_tool_box)
        self.main_ui.comboBox_2.currentIndexChanged.connect(self.change_shape_type)
        self.main_ui.horizontalSlider.valueChanged.connect(self.img_enhance)
        self.main_ui.horizontalSlider_2.valueChanged.connect(self.img_enhance)
        self.main_ui.horizontalSlider_3.valueChanged.connect(self.img_pil_contrast)
        self.main_ui.listWidget.itemClicked.connect(self.look_or_not_look)
        self.main_ui.listWidget_2.itemClicked.connect(self.select_shape)
        signal_cocj_done.signal.connect(self.change_one_class_jsons_done)
        signal_docj_done.signal.connect(self.delete_one_class_jsons_done)
        signal_del_shape.signal.connect(self.del_shape)
        signal_move2new_folder.signal.connect(self.move_to_new_folder)
        signal_one_collection_done.signal.connect(self.save_one_seg_label)
        signal_open_label_window.signal.connect(self.show_label_ui)
        signal_progress_done.signal.connect(self.auto_inference_done)
        signal_progress_text.signal.connect(self.update_progress_auto_infer_text)
        signal_progress_value.signal.connect(self.update_progress_auto_infer_value)
        signal_selected_shape.signal.connect(self.set_shape_selected)
        signal_select_ui_ok_button.signal.connect(self.save_one_seg_label)
        signal_show_label_img.signal.connect(self.marquee_show)
        signal_show_plain_img.signal.connect(self.marquee_show)
        signal_xy_color2ui.signal.connect(self.show_xy_color)
        # sys.stderr.signal.connect(self.error2log)

    def closeEvent(self, e):
        if self.window_marquee_img:
            self.window_marquee_img.close()
        if self.window_marquee_label:
            self.window_marquee_label.close()
        if self.window_train_val_img:
            self.window_train_val_img.close()
        if self.window_train_val_png:
            self.window_train_val_png.close()
        if self.window_compare:
            self.window_compare.close()
        if self.window_auto_infer_progress:
            self.window_auto_infer_progress.close()

        self.save_one_label_file()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A or event.key() == Qt.Key_D:
            # 查看训练/验证集时的图片翻页功能
            if self.window_train_val_img and self.window_train_val_png:
                if (not self.window_train_val_img.IsClosed) or (not self.window_train_val_png.IsClosed):
                    if event.key() == Qt.Key_A:
                        self.tv_i -= 1
                    elif event.key() == Qt.Key_D:
                        self.tv_i += 1

                    self.tv_i = min(max(0, self.tv_i), len(self.tv_imgs) - 1)
                    ori_path = self.tv_imgs[self.tv_i]
                    self.window_train_val_img.paint_img(QPixmap(ori_path))
                    png_path = ori_path.replace('imgs', 'labels')[:-3] + 'png'
                    qimg_png = self.get_qimg_png(png_path)
                    if qimg_png:
                        self.window_train_val_png.paint_img(qimg_png)
                    return

            if event.key() == Qt.Key_A:
                self.scan_img(last=True)
            elif event.key() == Qt.Key_D:
                self.scan_img(next=True)

        elif event.key() == Qt.Key_Z and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.main_ui.img_widget.remove_widget_img_pair()

    def resizeEvent(self, event):
        font_metrics = QFontMetrics(self.main_ui.label_5.font())
        str_w = font_metrics.size(0, self.bottom_img_text).width()
        label_w = self.main_ui.label_5.width()

        if str_w > label_w - 12:  # 左下角信息自动省略
            elideNote = font_metrics.elidedText(self.bottom_img_text, Qt.ElideRight, label_w)
            self.main_ui.label_5.setText(elideNote)

    def auto_inference(self):
        os.makedirs(f'{self.img_root_path}/分割/自动标注', exist_ok=True)

        if len(ClassStatDict) == 0:
            QMessageBox.critical(self.main_ui, '未找到类别名称', '请先加载类别。')
            return

        QMessageBox.information(self.main_ui, '加载onnx文件', '请选择一个onnx文件。')

        onnx_file = self.file_select_dlg.getOpenFileName(self.main_ui, '选择ONNX文件', filter='onnx (*.onnx)')[0]
        if not onnx_file:
            return
        re = QMessageBox.question(self.main_ui, '自动推理',
                                  f'"{self.img_root_path}/原图" 下的{len(self.imgs)}张图片将自动生成分割标注，继续吗？。',
                                  QMessageBox.Yes, QMessageBox.No)
        if re != QMessageBox.Yes:
            return

        try:
            sess = ort.InferenceSession(onnx_file, providers=["CUDAExecutionProvider"])
            self.window_auto_infer_progress = ProgressWindow(title='推理中', text_prefix='使用GPU推理中：')
        except:
            sess = ort.InferenceSession(onnx_file, providers=["CPUExecutionProvider"])
            self.window_auto_infer_progress = ProgressWindow(title='推理中', text_prefix='使用CPU推理中：')

        inputs = sess.get_inputs()
        if len(inputs) > 1:
            QMessageBox.critical(self.main_ui, '输入错误', f'模型只能有一个输入，实际检测到{len(inputs)}个输入。')
            return

        in_type, in_shape, in_name = inputs[0].type, tuple(inputs[0].shape), inputs[0].name
        if in_type != 'tensor(uint8)':
            QMessageBox.critical(self.main_ui, '输入错误', f'模型输入的类型必须为tensor(uint8)，实际为{in_type}。')
            return

        QMessageBox.information(self.main_ui, '图片形状不匹配',
                                f'模型输入尺寸：{in_shape}，如果图片尺寸不匹配，图片将自动调整至需要的尺寸。')

        content, is_ok = self.input_dlg.getText(self.main_ui, f'请输入DP抽稀算法阈值, 轮廓点数最小值、最大值',
                                                '请输入整数，阈值越高，抽稀后轮廓点数越少，反之越多，默认为(2, 4, 50)',
                                                QLineEdit.Normal, text='2, 4, 50')
        if is_ok:
            try:
                dp_para = content.replace('，', ',').split(',')
                dp_para = [float(one.strip()) for one in dp_para]
            except:
                QMessageBox.critical(self.main_ui, '格式错误', f'请输入正确的格式，参照：2, 4, 40。')
                return
        else:
            return

        content, is_ok = self.input_dlg.getText(self.main_ui, f'请输入面积过滤阈值',
                                                '面积为目标区域对应的像素数量，低于阈值的目标将被过滤， 默认为16',
                                                QLineEdit.Normal, text='16')
        if is_ok:
            try:
                filter_area = int(content.strip())
            except:
                QMessageBox.critical(self.main_ui, '格式错误', f'请输入正确的格式，参照：16。')
                return
        else:
            return

        self.window_auto_infer_progress.show()

        self.inference_thread = RunInference(sess, self.imgs, list(ClassStatDict.keys()), dp_para, filter_area)
        self.inference_thread.start()

    def auto_inference_done(self):
        self.window_auto_infer_progress.set_text(f'已完成，推理结果存放在 "{self.img_root_path}/自动标注"。')

    def button_action(self):
        button = self.sender()

        if self.WorkMode == '单类别分类':
            if self.img_root_path and button.text() != '-':
                self.cv2_img_changed = None

                work_dir = f'{self.img_root_path}/单类别分类/{button.text()}'
                os.makedirs(work_dir, exist_ok=True)

                self.cur_i = min(max(0, self.cur_i), self.img_num - 1)
                img_path = self.imgs[self.cur_i]
                dst_path = f'{work_dir}/{img_path.split("/")[-1]}'

                if not self.del_existed_file(img_path, dst_path):
                    return

                # 移动分类图片
                if img_path != 'images/图片已删除.png':
                    path_split = img_path.split('/')
                    self.imgs[self.cur_i] = f'{work_dir}/{path_split[-1]}'  # 随着图片路径变化而变化

                    if self.has_classified(img_path):
                        self.file_move(img_path, work_dir)
                        self.cls_op_track.append(('re_cls', self.cur_i, self.cur_mar_i, img_path, work_dir))

                        new_class = work_dir.split('/')[-1]
                        old_class, img_name = path_split[-2:]

                        ClassStatDict[old_class] -= 1
                        ClassStatDict[new_class] += 1
                        self.cls_to_button()
                        QMessageBox.information(self.main_ui, '移动图片',
                                                f'"{img_name}"已从<font color=red>"{old_class}"</font>移动至'
                                                f'<font color=red>"{new_class}"</font>。')
                    else:
                        if self.main_ui.radioButton_read.isChecked():  # cut
                            self.file_move(img_path, work_dir)
                            self.cls_op_track.append(('cut', self.cur_i, self.cur_mar_i, img_path, work_dir))
                        elif self.main_ui.radioButton_write.isChecked():  # copy
                            self.file_copy(img_path, work_dir)
                            self.cls_op_track.append(('copy', self.cur_i, self.cur_mar_i, img_path, work_dir))

                        ClassStatDict[button.text()] += 1  # 当前类别数量加1
                        self.go_next_img()

        elif self.WorkMode == '多类别分类':
            if button.text() != '-' and self.in_edit_mode():
                if button.palette().button().color().name() == '#90ee90':
                    button.setStyleSheet('')
                    ClassStatDict.setdefault(button.text(), 0)
                    ClassStatDict[button.text()] -= 1
                else:
                    button.setStyleSheet('QPushButton { background-color: lightgreen }')
                    ClassStatDict.setdefault(button.text(), 0)
                    ClassStatDict[button.text()] += 1

    def button_clear(self):  # 清除按钮组中按钮的stylesheet
        if self.WorkMode == '单类别分类':
            button_layout = self.main_ui.groupBox_1.layout()
        elif self.WorkMode == '多类别分类':
            button_layout = self.main_ui.groupBox_2.layout()

        for i in range(button_layout.rowCount()):
            for j in range(button_layout.columnCount()):
                button_layout.itemAtPosition(i, j).wid.setStyleSheet('')

    def buttons_load(self):
        path = self.file_select_dlg.getOpenFileName(self.main_ui, '选择任务', filter='txt (*.txt)')[0]
        if path:
            self.reset_seg()
            if self.WorkMode == '单类别分类':
                self.init_button_group(self.main_ui.groupBox_1, path)
            elif self.WorkMode == '多类别分类':
                self.init_button_group(self.main_ui.groupBox_2, path)

    def buttons_save(self):
        content, is_ok = self.input_dlg.getText(self.main_ui, '请输入名称', '请输入名称', QLineEdit.Normal)
        if is_ok:
            with open(f'{self.img_root_path}/{content}.txt', 'w', encoding='utf-8') as f:
                for one_c in ClassStatDict.keys():
                    f.writelines(f'{one_c}\n')

    def buttons_add_line(self):
        if self.WorkMode == '单类别分类':
            button_layout = self.main_ui.groupBox_1.layout()
        elif self.WorkMode == '多类别分类':
            button_layout = self.main_ui.groupBox_2.layout()

        new_line = QHBoxLayout()
        for i in range(4):
            new_button = ClassButton()
            new_button.setText('-')
            new_button.clicked.connect(self.button_action)
            new_line.addWidget(new_button)

        button_layout.addLayout(new_line)

    def buttons_remove_line(self):
        if self.WorkMode == '单类别分类':
            button_layout = self.main_ui.groupBox_1.layout()
        elif self.WorkMode == '多类别分类':
            button_layout = self.main_ui.groupBox_2.layout()

        count = button_layout.count()
        line = button_layout.takeAt(count - 1)
        for i in range(4):
            widget = line.takeAt(0).widget()
            widget.setParent(None)

    def change_font_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.main_ui.pushButton_37.setStyleSheet('QPushButton { background-color: %s }' % color.name())
            self.main_ui.img_widget.change_font(ann_font_color=QColor(color.name()))

    def change_font_size(self):
        self.main_ui.img_widget.change_font(ann_font_size=self.main_ui.spinBox_5.value())

    def change_one_class_jsons(self):
        new_c, is_ok = self.input_dlg.getText(self.main_ui, f'修改类别', '请输入类别名称', QLineEdit.Normal)
        if is_ok:
            c_name = self.main_ui.listWidget.currentItem().text()
            row_i = self.main_ui.listWidget.currentRow()
            new_c = new_c.strip()
            re = QMessageBox.question(self.main_ui, '修改类别', f'确定将所有<font color=red>"{c_name}"</font>修改为'
                                                            f'<font color=red>"{new_c}"</font>吗？')
            if re == QMessageBox.Yes:
                ClassStatDict.pop(c_name)
                if new_c not in ClassStatDict.keys():
                    ClassStatDict.setdefault(new_c, 0)
                    item = QListWidgetItem(new_c)
                    color = self.choose_new_color()
                    item.setForeground(color)
                    item.setIcon(self.icon_look)
                    self.main_ui.listWidget.addItem(item.clone())

                imgs = glob.glob(f'{self.img_root_path}/分割/原图/*')
                imgs.sort()

                self.thread_cocj = ChangeOneClassJsons(imgs, c_name, new_c, row_i)
                self.thread_cocj.start()

                self.show_waiting_label()

    def change_one_class_jsons_done(self, row_i):
        item = self.main_ui.listWidget.takeItem(row_i)
        del item

        self.waiting_label.stop()
        self.waiting_label.close()
        QMessageBox.information(self.main_ui, '修改完成', f'已完成，对应的PNG标注图已同步更新，请重新打开目录。')

    def change_pen_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.pushButton_12.setStyleSheet('QPushButton { background-color: %s }' % color.name())
                self.main_ui.img_widget.change_pen(seg_pen_color=QColor(color.name()))
            elif self.main_ui.toolBox.currentIndex() == 1:
                self.main_ui.pushButton_39.setStyleSheet('QPushButton { background-color: %s }' % color.name())
                self.main_ui.img_widget.change_pen(ann_pen_color=QColor(color.name()))
                self.main_ui.img_widget.ann_pen_color = QColor(color.name())

    def change_pen_size(self):
        if self.main_ui.toolBox.currentIndex() == 0:
            self.main_ui.img_widget.change_pen(seg_pen_size=self.main_ui.spinBox.value())
        elif self.main_ui.toolBox.currentIndex() == 1:
            self.main_ui.img_widget.change_pen(ann_pen_size=self.main_ui.spinBox_6.value())

    def change_shape_angle(self):
        self.main_ui.img_widget.set_angle(self.main_ui.spinBox_angle.value())

    def change_shape_type(self):
        signal_shape_type.send(self.main_ui.comboBox_2.currentText())

    def choose_new_color(self):
        existed_color = []
        for i in range(self.main_ui.listWidget.count()):
            item = self.main_ui.listWidget.item(i)
            existed_color.append(ColorCode[item.foreground().color().name()])

        shuffle(ColorNames)
        color = QColor(ColorNames.pop())
        while color in existed_color:
            color = QColor(ColorNames.pop())

        return color

    def clear_marquee_layout(self):  # 清空self.marquee_layout
        while self.marquees_layout.count() > 1:
            widget = self.marquees_layout.takeAt(0).widget()
            widget.setParent(None)
            self.marquees_layout.removeWidget(widget)

    def clear_painted_img(self):
        self.main_ui.img_widget.clear_scaled_img()

    def cls_back(self):
        if self.cls_op_track and self.main_ui.groupBox_1.isEnabled():
            if self.WorkMode == '单类别分类':
                op, cur_i, cur_mar_i, ori_path, cur_path = self.cls_op_track.pop()

                path_split = ori_path.split('/')
                ori_path = '/'.join(path_split[:-1])
                img_name = path_split[-1]

                if op == 'cut':
                    self.file_move(uniform_path(osp.join(cur_path, img_name)), ori_path)
                elif op == 'copy':
                    os.remove(osp.join(cur_path, img_name))
                elif op == 're_cls':
                    self.file_move(uniform_path(osp.join(cur_path, img_name)), ori_path)
                    old_class = path_split[-2]
                    ClassStatDict[old_class] += 1

                cur_class = cur_path.split('/')[-1]
                ClassStatDict[cur_class] -= 1

                if self.is_first_marquee():
                    self.cur_i -= 1
                    self.imgs[self.cur_i] = osp.join(ori_path, img_name)
                    self.main_ui.img_widget.paint_img(self.imgs[self.cur_i])
                    self.main_ui.label_5.setText(f'{self.imgs[self.cur_i]}，{self.cur_i + 1}/{self.img_num}')
                    self.pop_marquee()
                else:
                    self.imgs[cur_i] = osp.join(ori_path, img_name)
                    if op != 're_cls':
                        self.marquees_layout.itemAt(cur_mar_i).widget().set_stat('undo')

                    self.cls_to_button()
                    QMessageBox.information(self.main_ui, '已撤销', f'已撤销: {img_name},  '
                                                                 f'{ori_path} --> {cur_path}。')

    def cls_to_button(self):
        self.button_clear()
        category = self.has_classified(self.imgs[self.cur_i])
        if category:
            button_layout = self.main_ui.groupBox_1.layout()
            for i in range(button_layout.rowCount()):
                for j in range(button_layout.columnCount()):
                    button = button_layout.itemAtPosition(i, j).wid
                    if button.text() == category:
                        button.setStyleSheet('QPushButton { background-color: lightgreen }')
                        return

    def copy_img_to_val(self):
        if self.WorkMode == '分割':
            val_path = f'{self.img_root_path}/imgs/val'
            os.makedirs(val_path, exist_ok=True)
            os.makedirs(f'{self.img_root_path}/labels/val', exist_ok=True)

            val_label = path_to(self.imgs[self.cur_i], img2png=True)
            if '图片已删除' not in val_label:
                if osp.exists(val_label):
                    shutil.copy(self.imgs[self.cur_i], val_path)
                    shutil.copy(val_label, f'{self.img_root_path}/labels/val')
                    val_num = len(glob.glob(f'{val_path}/*'))
                    self.main_ui.label_5.setText(f'已复制到 "{val_path}", 共 {val_num} 张图片.')
                else:
                    QMessageBox.warning(self.main_ui, '未找到对应的标注文件', f'未找到"{val_label}"。')

    def copy_img_to_train(self):
        train_path = f'{self.img_root_path}/imgs/train'
        os.makedirs(train_path, exist_ok=True)
        os.makedirs(f'{self.img_root_path}/labels/train', exist_ok=True)
        i = 0

        val_img_list = glob.glob(f'{self.img_root_path}/imgs/val/*')
        val_img_list.sort()
        val_img_list = [one.split(os_sep)[-1] for one in val_img_list]

        for one in self.imgs:
            name = one.split(os_sep)[-1]
            if ('图片已删除' not in name) and (name not in val_img_list):
                train_label = path_to(one, img2png=True)
                if osp.exists(train_label):
                    shutil.copy(one, train_path)
                    shutil.copy(train_label, f'{self.img_root_path}/labels/train')
                    i += 1

        QMessageBox.information(self.main_ui, '已完成', f'已复制到 "{train_path}", 共 {i} 张图片。')

    def del_existed_file(self, cur_path, file_path):
        if cur_path == file_path:
            return True
        if os.path.exists(file_path):
            choice = QMessageBox.question(self.main_ui, '文件已存在', f'"{file_path}"已存在，要覆盖吗？')
            if choice == QMessageBox.Yes:
                os.remove(file_path)
                return True
            elif choice == QMessageBox.No:  # 右上角关闭按钮也返回QMessageBox.No
                return False
        else:
            return True

    def del_img(self, del_path=None):
        if not (0 <= self.cur_i < len(self.imgs)):
            return
        if self.imgs[self.cur_i] == 'images/图片已删除.png':
            return

        if del_path is None:
            del_path = f'{self.img_root_path}/deleted'
        os.makedirs(del_path, exist_ok=True)

        img_path = self.imgs[self.cur_i]
        if self.WorkMode == '单类别分类':
            self.file_move(img_path, del_path)
            old_class = self.has_classified(self.imgs[self.cur_i])
            if old_class:
                ClassStatDict[old_class] -= 1
        else:
            path_del_img = f'{del_path}/{self.WorkMode}/原图'
            path_del_label = f'{del_path}/{self.WorkMode}/标注'
            os.makedirs(path_del_img, exist_ok=True)
            os.makedirs(path_del_label, exist_ok=True)

            if self.WorkMode == '多类别分类':
                self.file_move(img_path, path_del_img)
                txt_path = path_to(img_path, img2txt=True)
                if os.path.exists(txt_path):
                    self.file_move(txt_path, path_del_label)
            elif self.WorkMode == '目标检测':
                pass

            elif self.WorkMode == '分割':
                self.file_move(img_path, path_del_img)
                json_path = path_to(img_path, img2json=True)
                png_path = json_path[:-5] + '.png'
                if os.path.exists(json_path):
                    self.file_move(json_path, path_del_label)
                if os.path.exists(png_path):
                    self.file_move(png_path, path_del_label)

                if self.main_ui.img_widget.get_json_polygons():
                    for one in self.main_ui.img_widget.all_polygons:
                        ClassStatDict[one['category']] -= 1

                self.main_ui.img_widget.clear_all_polygons()
                self.main_ui.listWidget_2.clear()

        self.imgs[self.cur_i] = 'images/图片已删除.png'  # 将删除的图片替换为背景图片
        self.show_img_status_info()
        del_map = QPixmap('images/图片已删除.png').scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio)
        self.marquees_layout.itemAt(self.cur_mar_i).widget().setPixmap(del_map, del_img=True)
        self.go_next_img()

    def del_shape(self, i):
        item = self.main_ui.listWidget_2.takeItem(i)
        seg_class = item.text()
        del item
        ClassStatDict[seg_class] -= 1

    def delete_one_class_jsons(self):
        c_name = self.main_ui.listWidget.currentItem().text()
        row_i = self.main_ui.listWidget.currentRow()
        re = QMessageBox.question(self.main_ui, '删除类别', f'确定删除所有<font color=red>"{c_name}"</font>"标注吗？')

        if re == QMessageBox.Yes:
            ClassStatDict.pop(c_name)
            imgs = glob.glob(f'{self.img_root_path}/分割/原图/*')
            imgs.sort()

            self.thread_docj = DeleteOneClassJsons(imgs, c_name, row_i)
            self.thread_docj.start()

            self.show_waiting_label()

    def delete_one_class_jsons_done(self, row_i):
        item = self.main_ui.listWidget.takeItem(row_i)
        del item

        self.waiting_label.stop()
        self.waiting_label.close()
        QMessageBox.information(self.main_ui, '已完成', f'已完成，对应的PNG标注图已同步更新。')

    def error2log(self, text):
        QMessageBox.warning(self.main_ui, '系统错误', f'<font color=red>{text}</font>，请反馈给开发者。')

        date_time = get_datetime()

        with open('error_log.txt', 'a+', encoding='utf-8') as f:
            f.writelines(text)

    def export_seg_classes(self):
        text, is_ok = QInputDialog().getText(self, '名称', '请输入导出txt的名称。', QLineEdit.Normal)
        if is_ok:
            class_num = self.main_ui.listWidget.count()
            lines = ''
            for i in range(class_num):
                lines += f'{self.main_ui.listWidget.item(i).text()},\n'

            txt_path = f'{self.img_root_path}/分割/{text}.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            QMessageBox.information(self.main_ui, '已完成', f'已导出到"{txt_path}"。')

    def file_copy(self, src_path, dst_path):
        new_file_path = osp.join(dst_path, src_path.split('/')[-1])
        if self.del_existed_file(src_path, new_file_path):
            if src_path != new_file_path:
                shutil.copy(src_path, dst_path)

    def file_move(self, src_path, dst_path):
        new_file_path = osp.join(dst_path, src_path.split('/')[-1])
        if self.del_existed_file(src_path, new_file_path):
            if src_path != new_file_path:
                shutil.move(src_path, dst_path)

    def get_current_classes(self):
        classes = []
        for i in range(self.main_ui.listWidget_2.count()):
            classes.append(self.main_ui.listWidget_2.item(i).text())
        return classes

    def get_current_img_name(self):
        return self.imgs[self.cur_i].split('/')[-1]

    def get_looking_classes(self):
        classes = []
        for i in range(self.main_ui.listWidget.count()):
            item = self.main_ui.listWidget.item(i)
            if item.icon().cacheKey() == self.icon_look_key:
                classes.append(item.text())

        return classes, len(classes) == self.main_ui.listWidget.count()

    def get_qimg_png(self, png_path):
        if self.has_categories():
            png_img = cv2.imdecode(np.fromfile(png_path, dtype='uint8'), cv2.IMREAD_COLOR)
            class_num = self.main_ui.listWidget.count()
            if class_num != len(ClassStatDict.keys()):
                QMessageBox.critical(self.main_ui, '类别数量错误', '类别列表数量与类别字典数量不一致！')
                return
            png_img = png_img * int(255 / class_num)
            height, width, depth = png_img.shape
            return QImage(png_img.astype('uint8').data, width, height, width * depth, QImage.Format_RGB888)
        else:
            return False

    def get_sub_seg_png(self):
        if len(ClassStatDict) == 0:
            QMessageBox.critical(self.main_ui, '未找到类别名称', '请先加载类别。')
            return

        json_path = self.file_select_dlg.getExistingDirectory(self.main_ui, '选择文件夹')

        if json_path:
            jsons = glob.glob(f'{json_path}/*.json')
            jsons.sort()

            if len(jsons) == 0:
                QMessageBox.critical(self.main_ui, '未找到文件', f'未找到json文件。')
                return

            content, is_ok = self.input_dlg.getText(self.main_ui, f'共找到 {len(jsons)} 个标注文件',
                                                    '请输入名称', QLineEdit.Normal)
            if is_ok:
                classes = [aa.strip() for aa in content.replace('，', ',').split(',')]
                all_classes = list(ClassStatDict.keys())
                for one in classes:
                    if one not in all_classes:
                        QMessageBox.critical(self.main_ui, '不存在的类别', f'当前类别在加载的类别中不存在。')
                        return

                ori_path, _ = jsons[0].split(os_sep)
                save_path = f'{ori_path}/' + '_'.join(classes)
                os.makedirs(save_path, exist_ok=True)

                for one_j in jsons:
                    with open(one_j, 'r') as f:
                        content = json.load(f)
                        polygons, img_h, img_w = content['polygons'], content['img_height'], content['img_width']

                    img_name = one_j.split(os_sep)[-1].replace('json', 'png')
                    seg_mask = get_seg_mask(classes, polygons, img_h, img_w, from_sub=True)
                    cv2.imencode('.png', seg_mask)[1].tofile(osp.join(save_path, img_name))

                QMessageBox.information(self.main_ui, '已完成', f'新的标签位于"{save_path}"。')

    def go_next_img(self):  # 单类别分类模式或删除图片时触发
        self.marquee_move(right=True)
        self.cur_i += 1

        if self.cur_i < self.img_num:
            self.show_img_status_info()
        else:
            self.marquees_layout.itemAt(self.cur_mar_i).widget().set_stat('done')
            self.cur_mar_i += 1
            self.main_ui.img_widget.paint_img('images/bg.png')
            self.main_ui.label_5.setText('已完成。')
            QMessageBox.information(self.main_ui, '已完成', '已完成。')
            self.main_ui.groupBox_1.setDisabled(True)
            self.cv2_img = None
            self.cv2_img_changed = None

        if self.WorkMode == '单类别分类':
            self.cls_to_button()
        if self.WorkMode == '多类别分类':
            self.m_cls_to_button()
        if self.WorkMode == '分割':
            self.polygons_to_img()
            self.go_next_marquee_window()

    def go_next_marquee_window(self):
        if self.window_marquee_label:
            png_path = path_to(self.imgs[self.cur_i], img2png=True)
            if os.path.exists(png_path):
                qimg_png = self.get_qimg_png(png_path)
                if qimg_png:
                    self.window_marquee_label.paint_img(qimg_png)
        if self.window_marquee_img:
            self.window_marquee_img.paint_img(QPixmap(self.imgs[self.cur_i]))

    def has_categories(self):
        class_num = self.main_ui.listWidget.count()

        if class_num == 0:
            QMessageBox.warning(self.main_ui, '类别数量为0', '当前类别数量为0，请先加载类别。')
            return False
        return True

    def has_classified(self, path):  # 查看单类别分类模式下，图片是否已分类
        path = uniform_path(path)
        path_split = path.split('/')
        if path_split[-2] in ClassStatDict.keys():
            return path_split[-2]  # old class
        else:
            return False

    def img_enhance(self):
        self.main_ui.horizontalSlider_3.setValue(100)

        brightness_v = self.main_ui.horizontalSlider.value()
        self.main_ui.label_3.setText(str(brightness_v))
        contrast_v = self.main_ui.horizontalSlider_2.value() / 100
        self.main_ui.label_4.setText(str(contrast_v))

        if len(self.imgs):
            self.cv2_img_changed = (self.cv2_img.astype('float32') + brightness_v) * contrast_v
            self.cv2_img_changed = np.clip(self.cv2_img_changed, a_min=0., a_max=255.)
            self.paint_changed_cv2_img()

    def img_enhance_reset(self):
        self.main_ui.horizontalSlider.setValue(0)  # setValue 自动触发valueChanged信号
        self.main_ui.horizontalSlider_2.setValue(100)
        self.main_ui.horizontalSlider_3.setValue(100)

    def img_flip(self, h_flip=False, v_flip=False):
        if len(self.imgs) and self.cv2_img_changed is not None:
            if h_flip:
                self.cv2_img_changed = cv2.flip(self.cv2_img_changed, 1)
            if v_flip:
                self.cv2_img_changed = cv2.flip(self.cv2_img_changed, 0)

            self.paint_changed_cv2_img()

    def img_hold_on(self):
        if self.action_hold_on.text() == '切图保持':
            self.action_hold_on.setText('切图还原')
            self.ImgHoldOn = True
        elif self.action_hold_on.text() == '切图还原':
            self.action_hold_on.setText('切图保持')
            self.ImgHoldOn = False

    def img_jump(self, i=None):
        if i:
            index = i
        else:
            value = self.main_ui.spinBox_2.value()
            value = max(1, min(self.img_num, value))
            self.main_ui.spinBox_2.setValue(value)
            index = value - 1

        if index < self.cur_i:
            self.scan_img(last=True, count=self.cur_i - index)

        elif index > self.cur_i:
            self.scan_img(next=True, count=index - self.cur_i)

    def img_pil_contrast(self):
        self.main_ui.horizontalSlider.setValue(0)
        self.main_ui.horizontalSlider_2.setValue(100)

        value = self.main_ui.horizontalSlider_3.value() / 100
        self.main_ui.label_26.setText(str(value))

        if len(self.imgs):
            img = Image.fromarray(self.cv2_img)
            contrast_enhancer = ImageEnhance.Contrast(img)
            contrast_img = contrast_enhancer.enhance(value)
            self.cv2_img_changed = np.array(contrast_img)
            self.paint_changed_cv2_img()

    def img_rotate(self):
        if len(self.imgs) and self.cv2_img_changed is not None:
            self.cv2_img_changed = cv2.rotate(self.cv2_img_changed, cv2.ROTATE_90_CLOCKWISE)
            self.paint_changed_cv2_img()

    def img_search(self):
        text = self.main_ui.lineEdit_2.text()
        for i, img in enumerate(self.imgs):
            if text in img:
                self.img_jump(i)

    def in_edit_mode(self):
        if self.WorkMode in ('多类别分类', '目标检测', '分割'):
            if self.main_ui.radioButton_write.isChecked():
                return True
        return False

    def is_first_marquee(self):  # 判断marquees中当前图片是不是是第一张图片
        return self.cur_mar_i == self.marquees_layout.count() - 2

    def load_seg_classes(self):
        txt = self.file_select_dlg.getOpenFileName(self.main_ui, '选择txt', filter='txt (*.txt)')[0]
        if txt:
            self.main_ui.listWidget.clear()
            self.label_ui.ui.listWidget.clear()
            ClassStatDict.clear()

            shuffle(ColorNames)
            with open(txt, 'r', encoding='utf-8') as f:
                classes = f.readlines()
                classes = [aa.replace('，', ',').split(',')[0].strip() for aa in classes]
                for one in classes:
                    if one != '':
                        item = QListWidgetItem(one)
                        aa = ColorNames.pop()
                        item.setForeground(QColor(aa))
                        print(one, aa)
                        ClassStatDict.setdefault(one, 0)
                        self.label_ui.ui.listWidget.addItem(item.clone())
                        item.setIcon(self.icon_look)
                        self.main_ui.listWidget.addItem(item.clone())

            self.looking_classes, _ = self.get_looking_classes()

    def load_one_file_dict(self):
        json_path = f'{self.img_root_path}/{self.WorkMode}/标注/labels.json'
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                self.label_file_dict = json.load(f)
        else:
            self.label_file_dict = {'task': self.task, 'work_mode': self.WorkMode, 'labels': {}}

    def load_pinned_images(self):
        json_path = 'log_files/pinned_images.json'
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                content = json.load(f).get(self.task)
                if content:
                    self.pinned_images = content

    def look_or_not_look(self):
        item = self.main_ui.listWidget.currentItem()
        if item.icon().cacheKey() == self.icon_look_key:
            item.setIcon(self.icon_not_look)
        elif item.icon().cacheKey() == self.icon_not_look_key:
            item.setIcon(self.icon_look)

    def marquee_add(self, the_first_one=False):
        if the_first_one:
            img_path = self.imgs[self.cur_i]
        else:
            img_path = self.imgs[self.cur_i + 1]

        m_label = MarqueeLabel(img_path=img_path, stat='doing', parent=self)
        pix_map = QPixmap(img_path)
        m_label.setPixmap(pix_map.scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio))
        self.marquees_layout.insertWidget(self.marquees_layout.count() - 1, m_label)
        self.cur_mar_i += 1

        max_len = self.main_ui.scrollArea.horizontalScrollBar().maximum()
        self.main_ui.scrollArea.horizontalScrollBar().setValue(max_len)

    def marquee_insert(self, first=False, last=True):  # 在头或尾插入一个新的marquee
        if first:
            img_path = self.imgs[self.cur_i - 1]
            m_label = MarqueeLabel(img_path=img_path, stat='doing', parent=self)
            m_label.setPixmap(QPixmap(img_path).scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio))

            widget = self.marquees_layout.takeAt(self.marquee_num - 1).widget()
            widget.setParent(None)
            self.marquees_layout.removeWidget(widget)
            self.marquees_layout.insertWidget(0, m_label)
        elif last:
            img_path = self.imgs[self.cur_i + 1]
            m_label = MarqueeLabel(img_path=img_path, stat='doing', parent=self)
            m_label.setPixmap(QPixmap(img_path).scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio))

            widget = self.marquees_layout.takeAt(0).widget()
            widget.setParent(None)
            self.marquees_layout.removeWidget(widget)
            self.marquees_layout.insertWidget(self.marquees_layout.count() - 1, m_label)

            max_len = self.main_ui.scrollArea.horizontalScrollBar().maximum()
            self.main_ui.scrollArea.horizontalScrollBar().setValue(max_len)

    def marquee_move(self, left=False, right=False):  # 该函数以及其调用的函数都不能去改变self.cur_i
        if '图片已删除' in self.imgs[self.cur_i]:
            self.marquees_layout.itemAt(self.cur_mar_i).widget().set_stat('undo')
        else:
            stat = self.marquee_stat(self.imgs[self.cur_i])
            self.marquees_layout.itemAt(self.cur_mar_i).widget().set_stat(stat)

        if left:
            if self.cur_mar_i > 0:
                self.marquees_layout.itemAt(self.cur_mar_i - 1).widget().set_stat('doing')
                self.cur_mar_i -= 1
            else:
                if self.cur_i > 0:
                    self.marquee_insert(first=True, last=False)
        elif right:
            if self.cur_mar_i < self.marquees_layout.count() - 2:
                self.marquees_layout.itemAt(self.cur_mar_i + 1).widget().set_stat('doing')
                self.cur_mar_i += 1
            else:
                if self.cur_i < self.img_num - 1:
                    if self.marquees_layout.count() - 1 < self.marquee_num:
                        self.marquee_add()
                    else:
                        self.marquee_insert(last=True)

        self.main_ui.scrollArea.horizontalScrollBar().setValue(self.marquee_size * self.cur_mar_i)

    def marquee_show(self, info):
        img_path, show_png = info

        if self.WorkMode in ('目标检测', '分割'):
            if show_png:
                if self.WorkMode == '分割':
                    png_path = path_to(img_path, img2png=True)

                    if os.path.exists(png_path):
                        qimg_png = self.get_qimg_png(png_path)
                        if qimg_png:
                            self.window_marquee_label = BaseImgFrame(title='标注图片')
                            self.window_marquee_label.setWindowFlags(Qt.WindowStaysOnTopHint)
                            self.window_marquee_label.paint_img(qimg_png)
                            self.window_marquee_label.show()
            else:
                pix_map = QPixmap(img_path)
                self.window_marquee_img = BaseImgFrame(title='原图')
                self.window_marquee_img.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.window_marquee_img.paint_img(pix_map)
                self.window_marquee_img.show()

    def marquee_stat(self, path):  # 获取一个特定marquee的编辑状态
        stat = 'undo'

        if self.WorkMode == '单类别分类':
            stat = 'done' if path.split('/')[-2] in ClassStatDict.keys() else 'undo'
        elif self.WorkMode == '多类别分类':
            txt = path_to(path, img2txt=True)
            if osp.exists(txt):
                with open(txt, 'r', encoding='utf-8') as f:
                    if f.readlines():
                        stat = 'done'
        elif self.WorkMode == '分割':
            json_path = path_to(path, img2json=True)
            if osp.exists(json_path):
                with open(json_path, 'r') as f:
                    content = json.load(f)
                stat = 'done' if content['polygons'] else 'undo'

        return stat

    def move_to_new_folder(self):
        path = self.file_select_dlg.getExistingDirectory(self.main_ui, '选择文件夹')
        if path:
            self.del_img(path)

    def m_cls_to_button(self):  # 若已存在txt标注，直接显示在按钮上
        self.button_clear()

        txt_name = self.get_current_img_name()[:-3] + 'txt'
        txt_path = f'{self.img_root_path}/多类别分类/标注/{txt_name}'

        if os.path.isfile(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            lines = [aa.strip() for aa in lines]
            lines_copy = lines.copy()
            button_layout = self.main_ui.groupBox_2.layout()
            for one in lines:
                for i in range(button_layout.rowCount()):
                    for j in range(button_layout.columnCount()):
                        button = button_layout.itemAtPosition(i, j).wid
                        if button.text() == one:
                            button.setStyleSheet('QPushButton { background-color: lightgreen }')
                            lines_copy.remove(one)

                            if self.is_first_marquee():  # 避免重复+1
                                ClassStatDict.setdefault(button.text(), 0)
                                ClassStatDict[button.text()] += 1

            if len(lines_copy):
                error_class = ', '.join(lines_copy)
                QMessageBox.warning(self.main_ui, '标注错误', f'不存在的类别：{error_class} !')

    def modify_seg_class_1(self):
        if self.main_ui.checkBox_seg_edit.isChecked():
            self.LabelUiCallByMo = True
            self.show_label_ui()

    def modify_seg_class_2(self, text):
        i = self.main_ui.listWidget_2.currentRow()
        item = self.main_ui.listWidget.findItems(text, Qt.MatchExactly)
        if len(item):
            name = item[0].text()
            color = item[0].foreground().color()
        else:
            name = text
            color = self.choose_new_color()
            item = QListWidgetItem(name)
            item.setForeground(color)
            self.label_ui.ui.listWidget.addItem(item.clone())
            item.setIcon(self.icon_look)
            self.main_ui.listWidget.addItem(item.clone())
            ClassStatDict.setdefault(name, 0)

        self.main_ui.img_widget.modify_polygon_class(i, name, color.name())
        old_item = self.main_ui.listWidget_2.currentItem()
        old_class = old_item.text()
        ClassStatDict[old_class] -= 1

        old_item.setText(name)
        old_item.setForeground(color)
        ClassStatDict[name] += 1

        self.label_ui.close()

    def open_dir(self):
        file_path = self.file_select_dlg.getExistingDirectory(self.main_ui, '选择文件夹')
        if os.path.isdir(file_path):
            self.img_root_path = file_path
            self.main_ui.lineEdit.setText(self.img_root_path)
            self.reset_seg()
            self.window_marquee_label = None
            self.window_train_val_png = None
            self.task = self.img_root_path.split('/')[-1]
            self.load_one_file_dict()
            self.load_pinned_images()

            if self.WorkMode == '单类别分类':
                path = f'{self.img_root_path}/{self.WorkMode}'
            else:
                path = f'{self.img_root_path}/{self.WorkMode}/原图'

            if not os.path.isdir(path):
                QMessageBox.warning(self.main_ui, '未找到文件夹', f'未找到 "{path}" 文件夹。')
                return

            if self.WorkMode == '单类别分类':
                self.files = glob.glob(f'{path}/*')
                self.imgs = [aa for aa in self.files if aa[-3:] in ('bmp', 'jpg', 'png')]
                self.imgs.sort()

                folders = [aa for aa in self.files if os.path.isdir(aa)]
                folders.sort()
                for one in folders:
                    imgs = glob.glob(f'{one}/*')
                    imgs = [aa for aa in imgs if aa[-3:] in ('bmp', 'jpg', 'png')]
                    imgs.sort()
                    self.imgs += imgs

                self.img_num = len(self.imgs)
                self.init_button_group(self.main_ui.groupBox_1, 'log_files/buttons.txt')
            else:
                self.imgs = glob.glob(f'{path}/*')
                self.imgs = [aa for aa in self.imgs if aa[-3:] in ('bmp', 'jpg', 'png')]
                self.imgs.sort()
                self.img_num = len(self.imgs)

                if self.WorkMode == '多类别分类':
                    self.init_button_group(self.main_ui.groupBox_2, 'log_files/buttons.txt')
                elif self.WorkMode == '目标检测':
                    pass
                elif self.WorkMode == '分割':
                    if len(self.imgs):
                        self.reset_seg()

            self.imgs = [uniform_path(aa) for aa in self.imgs]
            if len(self.imgs):
                self.cur_i = 0
                self.cls_op_track = []
                self.mcls_default_c = ''
                self.cur_mar_i = -1
                self.clear_marquee_layout()
                self.show_img_status_info()
                self.marquee_add(the_first_one=True)

            if self.WorkMode == '单类别分类':
                self.cls_to_button()
            elif self.WorkMode == '多类别分类':
                self.m_cls_to_button()
            elif self.WorkMode == '目标检测':
                pass
            elif self.WorkMode == '分割':
                self.polygons_to_img()

    def paint_changed_cv2_img(self):
        height, width, depth = self.cv2_img_changed.shape
        qimg = QImage(self.cv2_img_changed.astype('uint8').data, width, height, width * depth, QImage.Format_RGB888)
        self.main_ui.img_widget.paint_img(qimg, re_center=False)

    def paint_pinned_ann_img(self):
        img_name = self.get_current_img_name()
        if img_name in self.pinned_images:
            ann_jpg = f'{self.img_root_path}/注释图片/{img_name[:-4]}.jpg'
            if os.path.exists(ann_jpg):
                self.main_ui.img_widget.set_ann_painted_img(ann_jpg)

    def pin_jump(self, last=False, next=False):
        _, self.looking_all = self.get_looking_classes()
        if not self.looking_all:
            QMessageBox.warning(self.main_ui, '模式冲突', '存在屏蔽的类别时，该功能无法启用，请先取消屏蔽的类别。')
            return

        jump = True
        i = jump_start = self.cur_i
        while jump:
            if last:
                if i > 0:
                    i -= 1
                    img_name = self.imgs[i].split('/')[-1]
                    if img_name in self.pinned_images:
                        self.scan_img(last=True, count=jump_start - i)
                        jump = False
                else:
                    jump = False
            elif next:
                if i < self.img_num - 1:
                    i += 1
                    img_name = self.imgs[i].split('/')[-1]
                    if img_name in self.pinned_images:
                        self.scan_img(next=True, count=i - jump_start)
                        jump = False
                else:
                    jump = False

    def pin_unpin_image(self):
        img_name = self.get_current_img_name()
        if img_name in self.pinned_images:
            self.pinned_images.remove(img_name)
            self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_black.png'))
        else:
            self.pinned_images.append(img_name)
            self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_green.png'))

        json_dict = {self.task: self.pinned_images}
        with open('log_files/pinned_images.json', 'w') as f:
            json.dump(json_dict, f, sort_keys=False, ensure_ascii=False, indent=4)

    def polygons_to_img(self):
        json_path = path_to(self.imgs[self.cur_i], img2json=True)
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                content = json.load(f)
                polygons, img_h, img_w = content['polygons'], content['img_height'], content['img_width']

            for one in polygons:
                cate = one['category']
                if cate in ClassStatDict.keys():
                    item = self.main_ui.listWidget.findItems(cate, Qt.MatchExactly)[0]
                    one['qcolor'] = item.foreground().color().name()

                color = QColor(one['qcolor'])
                item = QListWidgetItem(cate)
                item.setForeground(color)
                self.main_ui.listWidget_2.addItem(item.clone())
                if cate not in ClassStatDict.keys():
                    self.label_ui.ui.listWidget.addItem(item.clone())
                    item.setIcon(self.icon_look)
                    self.main_ui.listWidget.addItem(item.clone())

                if self.is_first_marquee():
                    ClassStatDict.setdefault(cate, 0)
                    ClassStatDict[cate] += 1

            self.main_ui.img_widget.json_to_polygons(json_path, json_data=(polygons, img_h, img_w))

    def pop_marquee(self):
        item_num = self.marquees_layout.count()
        if item_num >= 2:
            widget = self.marquees_layout.takeAt(item_num - 2).widget()
            widget.setParent(None)
            self.marquees_layout.removeWidget(widget)
            self.cur_mar_i -= 1

            cur_item = self.marquees_layout.itemAt(self.cur_mar_i)
            if cur_item is not None:
                cur_item.widget().set_doing()

    def remove_mc_mr(self):
        folders = glob.glob(f'{self.img_root_path}/单类别分类/*')

        for one_f in folders:
            imgs = glob.glob(f'{one_f}/*')
            for one in imgs:
                if 'MC' in one or 'MR' in one:
                    os.remove(one)

        QMessageBox.information(self.main_ui, '已完成', '已完成。')

    def reset_seg(self):  # 清除控件上的所有标注图形，清空标注列表、类别字典
        self.main_ui.img_widget.clear_all_polygons()
        self.main_ui.listWidget.clear()
        self.main_ui.listWidget_2.clear()
        ClassStatDict.clear()
        self.label_ui.ui.listWidget.clear()
        self.main_ui.img_widget.collection_ui.ui.listWidget.clear()

    def save_ann_img(self):
        os.makedirs(f'{self.img_root_path}/注释图片', exist_ok=True)
        img = self.main_ui.img_widget.get_ann_img()
        img_array = qimage_to_array(img)
        img_name = self.get_current_img_name()[:-4]
        save_path = f'{self.img_root_path}/注释图片/{img_name}.jpg'
        cv2.imencode('.jpg', img_array.astype('uint8'))[1].tofile(save_path)
        QMessageBox.information(self.main_ui, '已保存', f'图片保存于：{save_path}。')

    def save_edited_img(self, save_all=False):
        if save_all:
            imgs_path = [aa for aa in self.imgs if aa != 'images/图片已删除.png']
            re = QMessageBox.question(self.main_ui, '覆盖图片', f'"{self.img_root_path}"下的所有图片将被覆盖，继续吗？')
            if re != QMessageBox.Yes:
                return
        else:
            imgs_path = [self.imgs[self.cur_i]]
            re = QMessageBox.question(self.main_ui, '覆盖图片', f'"{self.imgs[self.cur_i]}"将被覆盖，继续吗？')
            if re != QMessageBox.Yes:
                return

        for one in imgs_path:
            cv2_img = cv2.imdecode(np.fromfile(one, dtype='uint8'), cv2.IMREAD_UNCHANGED)
            ori_h, ori_w = cv2_img.shape[:2]
            rotate_a = self.main_ui.spinBox_16.value()

            if rotate_a == 90:
                cv2_img = cv2.rotate(cv2_img, cv2.ROTATE_90_CLOCKWISE)
            elif rotate_a == 180:
                cv2_img = cv2.rotate(cv2_img, cv2.ROTATE_180)
            elif rotate_a == 270:
                cv2_img = cv2.rotate(cv2_img, cv2.ROTATE_90_COUNTERCLOCKWISE)

            if self.main_ui.checkBox_131.isChecked():
                cv2_img = cv2.flip(cv2_img, 1)
            if self.main_ui.checkBox_132.isChecked():
                cv2_img = cv2.flip(cv2_img, 0)

            resize_w, resize_h = self.main_ui.spinBox_13.value(), self.main_ui.spinBox_14.value()
            if ori_w != resize_w or ori_h != resize_h:
                if self.main_ui.radioButton_12.isChecked():
                    scale_alg = cv2.INTER_NEAREST
                elif self.main_ui.radioButton_13.isChecked():
                    scale_alg = cv2.INTER_LINEAR
                cv2_img = cv2.resize(cv2_img, (resize_w, resize_h), scale_alg)

            if self.main_ui.radioButton_14.isChecked():
                suffix = '.jpg'
            elif self.main_ui.radioButton_15.isChecked():
                suffix = '.png'
            elif self.main_ui.radioButton_16.isChecked():
                suffix = '.bmp'

            cv2.imencode(suffix, cv2_img.astype('uint8'))[1].tofile(one[:-4] + suffix)

        QMessageBox.information(self.main_ui, '保存完成', f'保存完成，共{len(imgs_path)}张图片。')

    def save_m_cls(self):
        lines = []
        txt_name = self.imgs[self.cur_i].split('/')[-1][:-3] + 'txt'
        if '图片已删除' not in txt_name:
            button_layout = self.main_ui.groupBox_2.layout()
            for i in range(button_layout.rowCount()):
                for j in range(button_layout.columnCount()):
                    button = button_layout.itemAtPosition(i, j).wid
                    if button.palette().button().color().name() == '#90ee90':
                        cls = button.text()
                        lines.append(f'{cls}\n')

            dir = self.img_root_path + '/多类别分类/标注'
            os.makedirs(dir, exist_ok=True)
            txt_path = f'{dir}/{txt_name}'

            if not lines and self.mcls_default_c != '':
                lines.append(self.mcls_default_c)

            with open(txt_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

    def save_one_label_file(self):
        if self.OneFileLabel and self.img_root_path:
            json_path = f'{self.img_root_path}/{self.WorkMode}/标注/labels.json'
            with open(json_path, 'w') as f:
                json.dump(self.label_file_dict, f, sort_keys=False, ensure_ascii=False, indent=4)

    def save_one_seg_label(self, text):
        if self.LabelUiCallByMo:
            self.modify_seg_class_2(text)
            self.LabelUiCallByMo = False
            return
        if text:
            if text not in ClassStatDict.keys() and text != '':
                ClassStatDict.setdefault(text, 0)

                color = self.choose_new_color()
                item = QListWidgetItem(text)
                item.setForeground(color)
                self.label_ui.ui.listWidget.addItem(item.clone())
                self.main_ui.listWidget_2.addItem(item.clone())
                item.setIcon(self.icon_look)
                self.main_ui.listWidget.addItem(item.clone())
            else:
                item = self.main_ui.listWidget.findItems(f'{text}', Qt.MatchExactly)[0].clone()
                item_2 = item.clone()
                item_2.setIcon(QIcon())
                self.main_ui.listWidget_2.addItem(item_2)
                color = item.foreground().color()

            self.main_ui.img_widget.one_polygon_done(color.name(), text)
            ClassStatDict[text] += 1

            self.label_ui.close()

    def save_seg(self):  # 保存分割的json和png
        os.makedirs(f'{self.img_root_path}/分割/标注', exist_ok=True)
        img_path = self.imgs[self.cur_i]
        if img_path == 'images/图片已删除.png':
            return

        img_w, img_h = QPixmap(img_path).size().toTuple()
        img_name = img_path.split('/')[-1]
        json_polygons = self.main_ui.img_widget.get_json_polygons()

        one_label = {'img_height': img_h, 'img_width': img_w, 'tv': '', 'polygons': json_polygons}
        if self.OneFileLabel:
            self.label_file_dict['labels'][img_name] = one_label
        else:
            # save json
            label_path = f'{self.img_root_path}/分割/标注'
            json_path = f'{label_path}/{img_name[:-4]}.json'
            with open(json_path, 'w') as f:
                json.dump(one_label, f, sort_keys=False, ensure_ascii=False, indent=4)

            # save png
            seg_class_names = [aa for aa in ClassStatDict.keys()]
            seg_mask = get_seg_mask(seg_class_names, json_polygons, img_h, img_w)

            if seg_mask.__class__ == str:
                QMessageBox.critical(self.main_ui, '类别不存在', f'类别"{seg_mask}"不存在。')
                return

            if len(json_polygons) and not (0 < seg_mask.max() <= len(seg_class_names)):
                QMessageBox.critical(self.main_ui, '标注错误',
                                     f'当前有{len(seg_class_names)}类，但分割mask最大值为{seg_mask.max()}。')
                return

            cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(f'{label_path}/{img_name[:-4]}.png')

    # def scan_looking_img(self, last=False, next=False):
    #     if self.WorkMode in ('目标检测', '分割'):
    #         self.looking_classes, self.looking_all = self.get_looking_classes()
    #         if not self.looking_all:
    #             if self.OneFileLabel:
    #                 json_path = f'{self.img_root_path}/{mode}/标注/labels.json'
    #                 if not os.path.exists(json_path):
    #                     return
    #
    #                 with open(json_path, 'r') as f:
    #                     content = json.load(f)['labels']
    #
    #                 i = self.cur_i
    #                 while 0 <= i < self.img_num:
    #                     if last:
    #                         i -= 1
    #                     elif next:
    #                         i += 1
    #
    #                     img_name = self.imgs[i].split('/')[-1]
    #                     if content[img_name]['polygons']:
    #
    #
    #             else:
    #                 pass

    def scan_img(self, last=False, next=False, from_self=False, count=1):
        if self.cur_i < 0 or self.cur_i >= self.img_num:
            QMessageBox.critical(self.main_ui, '索引超限', f'当前self.cur_i为{self.cur_i}，超出限制！')
            return

        if self.WorkMode in ('目标检测', '分割') and not from_self:
            self.looking_classes, self.looking_all = self.get_looking_classes()
            if not self.looking_all:
                if self.OneFileLabel:
                    KeepGoing = True
                    i = self.cur_i
                    while 0 <= i < self.img_num and KeepGoing:
                        if last:
                            i -= 1
                        elif next:
                            i += 1

                        img_name = self.imgs[i].split('/')[-1]
                        polygons = self.label_file_dict['labels'][img_name]['polygons']
                        for one in polygons:
                            if one['category'] in self.looking_classes:
                                count = abs(i - self.cur_i)
                                KeepGoing = False
                                break
                else:
                    pass

        if self.in_edit_mode() and not from_self:
            if self.WorkMode == '多类别分类':
                self.save_m_cls()
            elif self.WorkMode == '分割':
                self.save_seg()

        if last and 0 < self.cur_i < self.img_num:
            self.main_ui.img_widget.clear_all_polygons()
            self.main_ui.listWidget_2.clear()

            # 这4行必须是这个顺序 --------------
            for _ in range(count):
                self.marquee_move(left=True)
                self.cur_i -= 1
            self.show_img_status_info()
            # ------------------------------

            if self.WorkMode == '单类别分类':
                self.cls_to_button()
            if self.WorkMode == '多类别分类':
                self.m_cls_to_button()
            if self.WorkMode == '分割':
                self.polygons_to_img()
                self.go_next_marquee_window()
                # self.scan_img_auto(last=True)

        elif next and self.cur_i < self.img_num - 1:
            self.main_ui.img_widget.clear_all_polygons()
            self.main_ui.listWidget_2.clear()

            # 这4行必须是这个顺序 --------------
            for _ in range(count):
                self.marquee_move(right=True)
                self.cur_i += 1
            self.show_img_status_info()
            # ------------------------------

            if self.WorkMode == '单类别分类':
                self.cls_to_button()
            if self.WorkMode == '多类别分类':
                self.m_cls_to_button()
            if self.WorkMode == '分割':
                self.polygons_to_img()
                self.go_next_marquee_window()
                # self.scan_img_auto(next=True)

    def scan_img_auto(self, last=False, next=False):  # 查看部分类别的标注时的自动翻页功能
        if not self.looking_all:
            current_classes = self.get_current_classes()
            call_self = True
            for one_c in current_classes:
                if one_c in self.looking_classes:
                    call_self = False

            if call_self:
                self.scan_img(last, next, from_self=True)

    def select_shape(self):
        signal_selected_label_item.send(self.main_ui.listWidget_2.currentRow())

    def set_m_cls_default_c(self):
        text, is_ok = QInputDialog().getText(self, '默认类别', '请输入类别名称', QLineEdit.Normal)
        if is_ok and text:
            self.mcls_default_c = text

    def set_one_file_label(self):
        self.OneFileLabel = self.main_ui.checkBox_2.isChecked()

    def set_read_mode(self):
        if self.WorkMode in ('目标检测', '分割'):
            self.main_ui.checkBox_seg_edit.setDisabled(self.main_ui.radioButton_read.isChecked())

    def set_seg_edit_mode(self):
        self.main_ui.img_widget.set_mode(seg=True, seg_edit=self.main_ui.checkBox_seg_edit.isChecked())
        self.action_modify_one_class_jsons.setDisabled(not self.main_ui.checkBox_seg_edit.isChecked())
        self.action_del_one_class_jsons.setDisabled(not self.main_ui.checkBox_seg_edit.isChecked())
        self.action_modify_one_shape_class.setDisabled(not self.main_ui.checkBox_seg_edit.isChecked())
        self.action_delete_one_shape.setDisabled(not self.main_ui.checkBox_seg_edit.isChecked())

    def set_shape_selected(self, i):
        self.main_ui.listWidget_2.item(i).setSelected(True)

    def set_tool_box(self):
        self.main_ui.img_widget.clear_scaled_img()
        self.main_ui.img_widget.clear_all_polygons()
        self.main_ui.img_widget.clear_widget_img_points()

        if self.main_ui.toolBox.currentIndex() == 0:
            tab_index = self.main_ui.tabWidget.currentIndex()
            if tab_index == 0:
                self.main_ui.img_widget.set_mode(cls=True)
            elif tab_index == 1:
                self.main_ui.img_widget.set_mode(m_cls=True)
            elif tab_index == 2:
                self.main_ui.img_widget.set_mode(det=True)
            elif tab_index == 3:
                self.main_ui.img_widget.set_mode(seg=True)
        elif self.main_ui.toolBox.currentIndex() == 1:
            self.main_ui.img_widget.set_mode(ann=True)
            self.paint_pinned_ann_img()

    def set_work_mode(self):
        tab_index = self.main_ui.tabWidget.currentIndex()
        self.WorkMode = self.main_ui.tabWidget.tabText(tab_index)

        if self.main_ui.toolBox.currentIndex() == 1:
            self.main_ui.img_widget.set_mode(ann=True)

        if self.WorkMode != '单类别分类':
            self.main_ui.radioButton_read.setText('只读')
            self.main_ui.radioButton_write.setText('编辑')

        if self.WorkMode == '单类别分类':
            self.main_ui.radioButton_read.setText('剪切')
            self.main_ui.radioButton_write.setText('复制')
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_mode(cls=True)
        elif self.WorkMode == '多类别分类':
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_mode(m_cls=True)
        elif self.WorkMode == '目标检测':
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_mode(det=True)
        elif self.WorkMode == '分割':
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_mode(seg=True)

        self.main_ui.page_4.setDisabled(tab_index == 0 or tab_index == 1)

        stat = self.main_ui.radioButton_read.isChecked() or tab_index == 0 or tab_index == 1
        self.main_ui.checkBox_seg_edit.setDisabled(stat)

        self.main_ui.pushButton_auto_infer.setDisabled(tab_index == 0 or tab_index == 1)
        self.main_ui.action_get_sub_seg_png.setDisabled(tab_index != 3)

        self.save_one_label_file()
        ClassStatDict.clear()
        self.main_ui.img_widget.paint_img('images/bg.png')
        self.main_ui.img_widget.clear_all_polygons()

    def show_class_statistic(self):
        add_info = []
        num = 0
        if self.WorkMode == '单类别分类':
            files = glob.glob(f'{self.img_root_path}/单类别分类/*')
            for one in files:
                if os.path.isdir(one):
                    num += len(glob.glob(f'{one}/*'))
            add_info += [f'已分类图片数量：{num}', f'总图片数量：{self.img_num}']

        elif self.WorkMode == '多类别分类':
            files = glob.glob(f'{self.img_root_path}/多类别分类/标注/*.txt')
            for one in files:
                if os.stat(one).st_size > 0:
                    num += 1
            add_info += [f'已分类图片数量：{num}', f'总图片数量：{self.img_num}']
        elif self.WorkMode == '目标检测':
            pass
        elif self.WorkMode == '分割':
            files = glob.glob(f'{self.img_root_path}/分割/标注/*.json')
            for one in files:
                if os.stat(one).st_size > 200 and 'labels.json' not in one:
                    num += 1
            add_info += [f'带标注图片数量：{num}', f'总图片数量：{self.img_num}']

        self.sub_window_stat = ClassStat(add_info)
        self.sub_window_stat.show()
        self.sub_window_stat.resize(self.sub_window_stat.class_list.size())

    def show_compare_img(self):
        path = self.file_select_dlg.getOpenFileName(self.main_ui, '选择图片', filter='图片类型 (*.png *.jpg *.bmp)')[0]
        if path:
            self.window_compare = BaseImgFrame(title='对比图片')
            self.window_compare.paint_img(path)
            self.window_compare.show()

    def show_img_status_info(self):
        path = self.imgs[self.cur_i]
        self.cv2_img = cv2.imdecode(np.fromfile(path, dtype='uint8'), cv2.IMREAD_COLOR)
        self.cv2_img = cv2.cvtColor(self.cv2_img, cv2.COLOR_BGR2RGB)
        self.cv2_img_changed = self.cv2_img

        if not self.ImgHoldOn:
            self.img_enhance_reset()
            self.main_ui.img_widget.paint_img(path)
        else:
            br_v = self.main_ui.horizontalSlider.value()
            co_v = self.main_ui.horizontalSlider_2.value() / 100
            pil_v = self.main_ui.horizontalSlider_3.value() / 100

            if pil_v == 1.:
                self.cv2_img_changed = (self.cv2_img.astype('float32') + br_v) * co_v
                self.cv2_img_changed = np.clip(self.cv2_img_changed, a_min=0., a_max=255.)
            else:
                img = Image.fromarray(self.cv2_img)
                contrast_enhancer = ImageEnhance.Contrast(img)
                contrast_img = contrast_enhancer.enhance(pil_v)
                self.cv2_img_changed = np.array(contrast_img)

            height, width, depth = self.cv2_img_changed.shape
            qimg = QImage(self.cv2_img_changed.astype('uint8').data, width, height, width * depth, QImage.Format_RGB888)
            self.main_ui.img_widget.paint_img(qimg)

        if path == 'images/图片已删除.png':
            self.main_ui.label_5.setText('图片已删除。')
        else:
            img_w, img_h = self.main_ui.img_widget.img.size().width(), self.main_ui.img_widget.img.size().height()
            self.bottom_img_text = f'{path}，H: {img_h}, W: {img_w}, {self.cur_i + 1}/{self.img_num}'
            self.main_ui.label_5.setTextFormat(Qt.PlainText)
            self.main_ui.label_5.setText(uniform_path(self.bottom_img_text))

            img_name = path.split('/')[-1]
            if img_name in self.pinned_images:
                self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_green.png'))
            else:
                self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_black.png'))

            self.paint_pinned_ann_img()

    def show_label_ui(self):
        geo = self.frameGeometry()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
        new_x = x + int(w / 3)
        new_y = y + int(h / 3)
        self.label_ui.move(new_x, new_y)
        self.label_ui.show()

    @staticmethod
    def show_menu(ob):  # 在鼠标位置显示菜单
        ob.exec(QCursor.pos())

    def show_train_val_label(self):
        if not self.has_categories():
            return

        QMessageBox.information(self.main_ui, '选择图片', '请选择一张训练集或验证集中的图片。')

        self.tv_i = 0
        tv_path = self.file_select_dlg.getExistingDirectory(self.main_ui, '选择文件夹', dir=self.img_root_path)

        if tv_path:
            self.tv_imgs = sorted(glob.glob(f'{tv_path}/*'))
        else:
            return

        self.window_train_val_img = BaseImgFrame(title='分割原图')
        self.window_train_val_img.setWindowFlags(Qt.WindowStaysOnTopHint)

        geo_self = self.frameGeometry()
        geo_sub = self.window_train_val_img.frameGeometry()
        x1 = geo_self.left()
        y1 = int((geo_self.height() - geo_sub.height()) / 2)
        self.window_train_val_img.move(x1, y1)

        self.window_train_val_png = BaseImgFrame(title='分割标注')
        self.window_train_val_png.setWindowFlags(Qt.WindowStaysOnTopHint)

        x2 = x1 + geo_sub.width()
        self.window_train_val_png.move(x2, y1)

        ori_path = self.tv_imgs[self.tv_i]
        self.window_train_val_img.paint_img(QPixmap(ori_path))
        self.window_train_val_img.show()

        png_path = ori_path.replace('imgs', 'labels')[:-3] + 'png'
        qimg_png = self.get_qimg_png(png_path)
        if qimg_png:
            self.window_train_val_png.paint_img(qimg_png)
            self.window_train_val_png.show()

    def show_waiting_label(self):
        self.waiting_label = WaitingLabel(self)
        geo_self = self.frameGeometry()
        x1 = int(geo_self.width() / 2)
        y1 = int(geo_self.height() / 3)
        self.waiting_label.move(x1, y1)
        self.waiting_label.show()

    def show_xy_color(self, info):
        x, y, r, g, b = info
        self.main_ui.label_8.setText(f'X: {x}, Y: {y} &nbsp; &nbsp;'  # &nbsp; 加入空格
                                     f'<font color=red> R: {r}, </font>'
                                     f'<font color=green> G: {g}, </font>'
                                     f'<font color=blue> B: {b} </font>')

    def undo_painting(self):
        self.main_ui.img_widget.undo_stack.undo()

    def update_progress_auto_infer_value(self, info):
        self.window_auto_infer_progress.set_value(info)

    def update_progress_auto_infer_text(self, info):
        self.window_auto_infer_progress.set_text(info)

    def update_train_val(self):
        t_path = f'{self.img_root_path}/labels/train'
        v_path = f'{self.img_root_path}/labels/val'
        train_labels = glob.glob(f'{t_path}/*')
        val_labels = glob.glob(f'{v_path}/*')

        re = QMessageBox.question(self.main_ui, '更新标注图片', f'"{t_path}" 下的{len(train_labels)}张标注将被更新，继续吗。')
        if re == QMessageBox.Yes:
            for one in train_labels:
                name = one.split(os_sep)[-1]
                shutil.copy(f'{self.img_root_path}/分割/标注/{name}', t_path)

            QMessageBox.information(self.main_ui, '已完成', f'已完成')

        re = QMessageBox.question(self.main_ui, '更新标注图片', f'"{v_path}" 下的{len(val_labels)}张标注将被更新，继续吗。')
        if re == QMessageBox.Yes:
            for one in val_labels:
                name = one.split(os_sep)[-1]
                shutil.copy(f'{self.img_root_path}/分割/标注/{name}', v_path)

            QMessageBox.information(self.main_ui, '已完成', f'已完成')
