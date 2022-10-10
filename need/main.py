import glob
import shutil
import cv2
import numpy as np
import os
import json
import onnxruntime as ort

from random import shuffle
from PIL import Image, ImageEnhance
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QMenu, QFileDialog, QInputDialog, QMessageBox, QLineEdit, QWidget, \
    QHBoxLayout, QColorDialog, QListWidgetItem, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QPixmap, QImage, QColor, QFontMetrics, QIcon, QAction
from need.custom_widgets.img_show_widget import shape_type, signal_xy_color2ui, signal_selected_shape, \
    signal_del_shape, selected_label_item, signal_open_label_window, signal_one_collection_done, \
    BaseImgFrame, signal_move2new_folder
from need.custom_widgets.marquee_label import signal_show_plain_img, signal_show_label_img
from need.custom_signals import StrSignal
from need.utils import ClassStatDict, ColorNames, ColorCode, get_seg_mask
from need.custom_widgets import *
from need.custom_threads.seg_auto_inference import signal_progress_text, signal_progress_value, signal_progress_done, \
    RunInference
from need.custom_threads.seg_change_one_class_json import ChangeOneClassJsons, signal_cocj_done
from need.custom_threads.seg_delete_one_class_json import DeleteOneClassJsons, signal_docj_done
from need.custom_widgets.waiting_label import WaitingLabel
from os import path as osp
from os.path import sep as os_sep

signal_select_ui_ok_from_label_adding = StrSignal()


# noinspection PyUnresolvedReferences
class ImgCls(QMainWindow):
    def __init__(self):
        super().__init__()
        self.WorkMode = 'cls'
        self.LabelUiCallByMo = False  # 用于区分self.label_ui是由新标注唤起还是由修改标注唤起
        self.img_root_path = ''  # 图片根目录
        self.imgs = []
        self.tv_imgs = []
        self.tv_i = 0
        self.img_num = 0
        self.cur_i = 0
        self.marquee_num = 20  # 小图的最大数量, 越大占用内存越多
        self.marquee_size = 150
        self.cur_mar_i = -1  # 当前小图的索引，最小有效值为0
        self.default_c = ''  # 多标签分类的默认类别
        self.cv2_img = None
        self.cv2_img_changed = None
        self.op_track = []
        self.bottom_img_text = ''
        self.ImgHoldOn = False

        self.file_select_dlg = QFileDialog(self)
        self.input_dlg = QInputDialog(self)

        loader = QUiLoader()
        loader.registerCustomWidget(ImgShow)
        loader.registerCustomWidget(ClassButton)
        self.main_ui = loader.load('main.ui')  # 主界面
        self.label_ui = SelectWindow(parent=self, title='类别', button_signal=signal_select_ui_ok_from_label_adding).ui

        self.setCentralWidget(self.main_ui)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setWindowTitle('图片处理工具')
        self.setWindowIcon(QIcon('images/icon.ico'))
        self.resize(1200, 900)

        self.init_button_group('temp.txt')
        self.init_menu()
        self.connect_signals()
        self.show()
        # 放在show()之后的操作
        self.main_ui.img_widget.paint_img('images/bg.png')

    def init_button_group(self, txt_path):  # 初始化类别按钮组
        button_layout = self.main_ui.groupBox_3.layout()
        with open(txt_path, 'r', encoding='utf-8') as f:
            categories = [aa.strip() for aa in f.readlines()]

        for i in range(button_layout.rowCount()):
            for j in range(button_layout.columnCount()):
                button = button_layout.itemAtPosition(i, j).wid
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
        self.main_ui.groupBox_3.customContextMenuRequested.connect(lambda: self.show_menu(self.menu_task))
        self.menu_task.addAction('加载任务').triggered.connect(self.load_cls_classes)
        self.menu_task.addAction('保存任务').triggered.connect(self.save_cls_classes)
        self.menu_task.addAction('增加一行').triggered.connect(self.add_one_line_button)
        self.action_m_cls_default = QAction('多分类默认类别', self)
        self.action_m_cls_default.triggered.connect(self.m_cls_default_c)
        self.action_m_cls_default.setDisabled(True)
        self.menu_task.addAction(self.action_m_cls_default)

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
        self.menu_seg_annotation.addAction('修改类别').triggered.connect(self.modify_seg_class_1)
        self.menu_seg_annotation.addAction('删除标注').triggered.connect(self.main_ui.img_widget.del_polygons)

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
        self.main_ui.pushButton_10.clicked.connect(self.show_class_stastics)
        self.main_ui.pushButton_auto_infer.clicked.connect(self.auto_inference)
        self.main_ui.pushButton_12.clicked.connect(self.change_pen_color)
        self.main_ui.pushButton_35.clicked.connect(self.undo_painting)
        self.main_ui.pushButton_37.clicked.connect(self.change_font_color)
        self.main_ui.pushButton_39.clicked.connect(self.change_pen_color)
        self.main_ui.pushButton_40.clicked.connect(self.clear_painted_img)
        self.main_ui.pushButton_81.clicked.connect(self.img_rotate)
        self.main_ui.pushButton_82.clicked.connect(lambda: self.img_flip(h_flip=True))
        self.main_ui.pushButton_83.clicked.connect(lambda: self.img_flip(v_flip=True))
        self.main_ui.pushButton_84.clicked.connect(lambda: self.scan_img(last=True))
        self.main_ui.pushButton_85.clicked.connect(lambda: self.scan_img(next=True))
        self.main_ui.pushButton_86.clicked.connect(lambda: self.del_img(del_path=None))
        self.main_ui.pushButton_100.clicked.connect(self.show_compare_img)
        self.main_ui.pushButton_101.clicked.connect(self.button_back)
        self.main_ui.pushButton_136.clicked.connect(self.save_edited_img)
        self.main_ui.pushButton_137.clicked.connect(lambda: self.save_edited_img(save_all=True))
        self.main_ui.pushButton_g_val.clicked.connect(self.copy_img_to_val)
        self.main_ui.pushButton_g_train.clicked.connect(self.copy_img_to_train)
        self.main_ui.pushButton_update_tv.clicked.connect(self.update_train_val)
        self.main_ui.pushButton_show_tv.clicked.connect(self.show_train_val_label)
        self.main_ui.spinBox.valueChanged.connect(self.change_pen_size)
        self.main_ui.spinBox_5.valueChanged.connect(self.change_font_size)
        self.main_ui.spinBox_6.valueChanged.connect(self.change_pen_size)
        self.main_ui.radioButton_read.toggled.connect(self.set_read_mode)
        self.main_ui.radioButton_cls.toggled.connect(self.set_work_mode)
        self.main_ui.radioButton_mcls.toggled.connect(self.set_work_mode)
        self.main_ui.radioButton_det.toggled.connect(self.set_work_mode)
        self.main_ui.radioButton_seg.toggled.connect(self.set_work_mode)
        self.main_ui.checkBox_3.toggled.connect(self.set_seg_edit_mode)
        self.main_ui.radioButton_read.toggled.connect(self.set_mcls_seg_stat)
        self.main_ui.toolBox.currentChanged.connect(self.set_tool_box)
        self.main_ui.comboBox_2.currentIndexChanged.connect(self.change_shape_type)
        self.main_ui.horizontalSlider.valueChanged.connect(self.img_enhance)
        self.main_ui.horizontalSlider_2.valueChanged.connect(self.img_enhance)
        self.main_ui.horizontalSlider_3.valueChanged.connect(self.img_pil_contrast)
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
        signal_select_ui_ok_from_label_adding.signal.connect(self.save_one_seg_label)
        signal_show_label_img.signal.connect(self.marquee_show)
        signal_show_plain_img.signal.connect(self.marquee_show)
        signal_xy_color2ui.signal.connect(self.show_xy_color)

    def closeEvent(self, e):
        if hasattr(self, 'marquee_window_label'):
            self.marquee_window_label.close()
        if hasattr(self, 'marquee_window_img'):
            self.marquee_window_img.close()
        if hasattr(self, 'seg_img_window'):
            self.seg_img_window.close()
        if hasattr(self, 'seg_png_window'):
            self.seg_png_window.close()
        if hasattr(self, 'compare_window'):
            self.compare_window.close()
        if hasattr(self, 'progress_window'):
            self.progress_auto_infer.close()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A or event.key() == Qt.Key_D:
            if hasattr(self, 'seg_img_window') and hasattr(self, 'seg_png_window'):
                if (not self.seg_img_window.IsClosed) or (not self.seg_img_window.IsClosed):
                    if event.key() == Qt.Key_A:
                        self.tv_i -= 1
                    elif event.key() == Qt.Key_D:
                        self.tv_i += 1

                    self.tv_i = min(max(0, self.tv_i), len(self.tv_imgs) - 1)
                    ori_path = self.tv_imgs[self.tv_i]
                    self.seg_img_window.paint_img(QPixmap(ori_path))
                    png_path = ori_path.replace('imgs', 'labels')[:-3] + 'png'
                    qimg_png = self.get_qimg_png(png_path)
                    self.seg_png_window.paint_img(qimg_png)
                    return

            if event.key() == Qt.Key_A:
                self.scan_img(last=True)
            elif event.key() == Qt.Key_D:
                self.scan_img(next=True)

            if hasattr(self, 'marquee_window_label'):
                png_path = self.path_to(self.imgs[self.cur_i], img2png=True)
                if os.path.exists(png_path):
                    qimg_png = self.get_qimg_png(png_path)
                    self.marquee_window_label.paint_img(qimg_png)
            if hasattr(self, 'marquee_window_img'):
                self.marquee_window_img.paint_img(QPixmap(self.imgs[self.cur_i]))

        elif event.key() == Qt.Key_Z and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.main_ui.img_widget.remove_widget_img_pair()
            self.main_ui.img_widget.update()

    def resizeEvent(self, event):
        font_metrics = QFontMetrics(self.main_ui.label_5.font())
        str_w = font_metrics.size(0, self.bottom_img_text).width()
        label_w = self.main_ui.label_5.width()

        if str_w > label_w - 12:  # 左下角信息自动省略
            elideNote = font_metrics.elidedText(self.bottom_img_text, Qt.ElideRight, label_w)
            self.main_ui.label_5.setText(elideNote)

    def add_one_line_button(self):
        button_layout = self.main_ui.groupBox_3.layout()
        row = button_layout.rowCount()
        for i in range(4):
            new_button = ClassButton()
            new_button.setText('-')
            new_button.clicked.connect(self.button_action)
            button_layout.addWidget(new_button, row + 1, i)

    def auto_inference(self):
        os.makedirs(f'{self.img_root_path}/分割/自动标注', exist_ok=True)

        if len(ClassStatDict) == 0:
            QMessageBox.critical(self.main_ui, '未找到类别名称', '请先加载类别。')
            return

        onnx_file = self.file_select_dlg.getOpenFileName(self.main_ui, '选择ONNX文件', filter='onnx (*.onnx)')[0]
        if onnx_file:
            re = QMessageBox.question(self.main_ui, '自动推理',
                                      f'"{self.img_root_path}/原图" 下的{len(self.imgs)}张图片将自动生成分割标注，继续吗？。',
                                      QMessageBox.Yes, QMessageBox.No)
            if re == QMessageBox.Yes:
                try:
                    sess = ort.InferenceSession(onnx_file, providers=["CUDAExecutionProvider"])
                    self.progress_auto_infer = ProgressWindow(title='推理中', text_prefix='使用GPU推理中：')
                except:
                    sess = ort.InferenceSession(onnx_file, providers=["CPUExecutionProvider"])
                    self.progress_auto_infer = ProgressWindow(title='推理中', text_prefix='使用CPU推理中：')

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

                self.progress_auto_infer.show()

                self.inference_thread = RunInference(sess, self.imgs, list(ClassStatDict.keys()), dp_para, filter_area)
                self.inference_thread.start()

    def auto_inference_done(self):
        self.progress_auto_infer.set_text(f'已完成，推理结果存放在 "{self.img_root_path}/自动标注"。')

    def button_action(self):
        button = self.sender()

        if self.WorkMode == 'cls':
            if self.img_root_path and button.text() != '-':
                self.cv2_img_changed = None

                work_dir = f'{self.img_root_path}/单标签分类/{button.text()}'
                os.makedirs(work_dir, exist_ok=True)

                self.cur_i = min(max(0, self.cur_i), self.img_num - 1)
                img_path = self.uniform_path(self.imgs[self.cur_i])
                dst_path = f'{work_dir}/{img_path.split("/")[-1]}'

                if not self.del_existed_file(img_path, dst_path):
                    return

                # 移动分类图片
                if img_path != 'images/图片已删除.png':
                    path_split = img_path.split('/')
                    self.imgs[self.cur_i] = f'{work_dir}/{path_split[-1]}'  # 随着图片路径变化而变化

                    if self.has_classified(img_path):
                        self.file_move(img_path, work_dir)
                        self.op_track.append(('re_cls', self.cur_i, self.cur_mar_i, img_path, work_dir))

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
                            self.op_track.append(('cut', self.cur_i, self.cur_mar_i, img_path, work_dir))
                        elif self.main_ui.radioButton_write.isChecked():  # copy
                            self.file_copy(img_path, work_dir)
                            self.op_track.append(('copy', self.cur_i, self.cur_mar_i, img_path, work_dir))

                        ClassStatDict[button.text()] += 1  # 当前类别数量加1
                        self.go_next_img()

        elif self.WorkMode == 'm_cls':
            if button.text() != '-' and self.in_edit_mode():
                if button.palette().button().color().name() == '#90ee90':
                    button.setStyleSheet('')
                    ClassStatDict.setdefault(button.text(), 0)
                    ClassStatDict[button.text()] -= 1
                else:
                    button.setStyleSheet('QPushButton { background-color: lightgreen }')
                    ClassStatDict.setdefault(button.text(), 0)
                    ClassStatDict[button.text()] += 1

    def button_back(self):
        if self.op_track and self.main_ui.groupBox_3.isEnabled():
            if self.WorkMode == 'cls':
                op, cur_i, cur_mar_i, ori_path, cur_path = self.op_track.pop()

                path_split = ori_path.split('/')
                ori_path = '/'.join(path_split[:-1])
                img_name = path_split[-1]

                if op == 'cut':
                    self.file_move(self.uniform_path(osp.join(cur_path, img_name)), ori_path)
                elif op == 'copy':
                    os.remove(osp.join(cur_path, img_name))
                elif op == 're_cls':
                    self.file_move(self.uniform_path(osp.join(cur_path, img_name)), ori_path)
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

            elif self.WorkMode == 'm_cls':
                txt_path = self.op_track.pop()
                os.remove(txt_path)
                QMessageBox.information(self.main_ui, '已删除', f'已删除: {txt_path}')

    def button_clear(self):  # 清除按钮组中按钮的stylesheet
        button_layout = self.main_ui.groupBox_3.layout()
        for i in range(button_layout.rowCount()):
            for j in range(button_layout.columnCount()):
                button_layout.itemAtPosition(i, j).wid.setStyleSheet('')

    def change_font_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.main_ui.pushButton_37.setStyleSheet('QPushButton { background-color: %s }' % color.name())
            self.main_ui.img_widget.change_font(ann_font_color=QColor(color.name()))

    def change_font_size(self):
        self.main_ui.img_widget.change_font(ann_font_size=self.main_ui.spinBox_5.value())

    def show_waiting_label(self):
        self.waiting_label = WaitingLabel(self)
        geo_self = self.frameGeometry()
        x1 = int(geo_self.width() / 2)
        y1 = int(geo_self.height() / 3)
        self.waiting_label.move(x1, y1)
        self.waiting_label.show()

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
        shape_type.send(self.main_ui.comboBox_2.currentText())

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

    def clear_painted_img(self):
        self.main_ui.img_widget.clear_scaled_img()

    def cls_to_button(self):
        self.button_clear()
        category = self.has_classified(self.imgs[self.cur_i])
        if category:
            button_layout = self.main_ui.groupBox_3.layout()
            for i in range(button_layout.rowCount()):
                for j in range(button_layout.columnCount()):
                    button = button_layout.itemAtPosition(i, j).wid
                    if button.text() == category:
                        button.setStyleSheet('QPushButton { background-color: lightgreen }')
                        return

    def copy_img_to_val(self):
        if self.WorkMode == 'seg':
            val_path = f'{self.img_root_path}/imgs/val'
            os.makedirs(val_path, exist_ok=True)
            os.makedirs(f'{self.img_root_path}/labels/val', exist_ok=True)

            val_label = self.path_to(self.imgs[self.cur_i], img2png=True)
            val_num = 0
            if '图片已删除' not in val_label:
                if osp.exists(val_label):
                    shutil.copy(self.imgs[self.cur_i], val_path)
                    shutil.copy(val_label, f'{self.img_root_path}/labels/val')
                    val_num += 1
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
                train_label = self.path_to(one, img2png=True)
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

        img_path = self.uniform_path(self.imgs[self.cur_i])
        if self.WorkMode == 'cls':
            self.file_move(img_path, del_path)
            old_class = self.has_classified(self.imgs[self.cur_i])
            if old_class:
                ClassStatDict[old_class] -= 1
        elif self.WorkMode == 'm_cls':
            path_m_cls_img = f'{del_path}/多标签分类/原图'
            path_m_cls_txt = f'{del_path}/多标签分类/标注'
            os.makedirs(path_m_cls_img, exist_ok=True)
            os.makedirs(path_m_cls_txt, exist_ok=True)
            self.file_move(img_path, path_m_cls_img)
            txt_path = self.path_to(img_path, img2txt=True)
            if os.path.exists(txt_path):
                self.file_move(txt_path, path_m_cls_txt)
        elif self.WorkMode == 'seg':
            path_seg_img = f'{del_path}/分割/原图'
            path_seg_ann = f'{del_path}/分割/标注'
            os.makedirs(path_seg_img, exist_ok=True)
            os.makedirs(path_seg_ann, exist_ok=True)
            self.file_move(img_path, path_seg_img)
            json_path = self.path_to(img_path, img2json=True)
            png_path = json_path[:-5] + '.png'
            if os.path.exists(json_path):
                self.file_move(json_path, path_seg_ann)
            if os.path.exists(png_path):
                self.file_move(png_path, path_seg_ann)

            if self.has_polygons():
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

    def export_seg_classes(self):
        text, is_ok = QInputDialog().getText(self, '名称', '请输入导出txt的名称。', QLineEdit.Normal)
        if is_ok:
            class_num = self.main_ui.listWidget.count()
            lines = ''
            for i in range(class_num):
                lines += f'{self.main_ui.listWidget.item(i).text()},\n'

            with open(f'{self.img_root_path}/分割/{text}.txt', 'w', encoding='utf-8') as f:
                f.writelines(lines)

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

    def go_next_img(self):  # 单标签分类模式或删除图片时触发
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
            self.main_ui.groupBox_3.setDisabled(True)
            self.cv2_img = None
            self.cv2_img_changed = None

        if self.WorkMode == 'cls':
            self.cls_to_button()
        if self.WorkMode == 'm_cls':
            self.m_cls_to_button()
        if self.WorkMode == 'seg':
            self.polygons_to_img()

    def has_categories(self):
        class_num = self.main_ui.listWidget.count()

        if class_num == 0:
            QMessageBox.warning(self.main_ui, '类别数量为0', '当前类别数量为0，请先加载类别。')
            return False
        return True

    def has_classified(self, path):  # 查看单标签分类模式下，图片是否已分类
        path = self.uniform_path(path)
        path_split = path.split('/')
        if path_split[-2] in ClassStatDict.keys():
            return path_split[-2]  # old class
        else:
            return False

    def has_polygons(self):  # 判断seg模式下当前图片是否有标注
        return self.main_ui.img_widget.get_json_polygons()

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

    def in_edit_mode(self):
        if self.WorkMode in ('m_cls', 'det', 'seg'):
            if self.main_ui.radioButton_write.isChecked():
                return True
        return False

    def is_first_marquee(self):  # 判断marquees中当前图片是不是是第一张图片
        return self.cur_mar_i == self.marquees_layout.count() - 2

    def load_seg_classes(self):
        txt = self.file_select_dlg.getOpenFileName(self.main_ui, '选择txt', filter='txt (*.txt)')[0]
        if txt:
            self.main_ui.listWidget.clear()
            self.label_ui.listWidget.clear()
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
                        self.main_ui.listWidget.addItem(item.clone())
                        self.label_ui.listWidget.addItem(item)

    def load_cls_classes(self):
        path = self.file_select_dlg.getOpenFileName(self.main_ui, '选择任务', filter='txt (*.txt)')[0]
        if path:
            self.reset_seg()
            self.init_button_group(path)

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
            stat = self.marquee_stat(self.uniform_path(self.imgs[self.cur_i]))
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

        if self.WorkMode in ('det', 'seg'):
            if show_png:
                if self.WorkMode == 'seg':
                    png_path = self.path_to(img_path, img2png=True)
                    if os.path.exists(png_path):
                        qimg_png = self.get_qimg_png(png_path)
                        self.marquee_window_label = BaseImgFrame()
                        self.marquee_window_label.setWindowFlags(Qt.WindowStaysOnTopHint)
                        self.marquee_window_label.setWindowTitle('标注图片')
                        self.marquee_window_label.paint_img(qimg_png)
                        self.marquee_window_label.show()
            else:
                pix_map = QPixmap(img_path)
                self.marquee_window_img = BaseImgFrame()
                self.marquee_window_img.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.marquee_window_img.setWindowTitle('原图')
                self.marquee_window_img.paint_img(pix_map)
                self.marquee_window_img.show()

    def marquee_stat(self, path):  # 获取一个特定marquee的编辑状态
        stat = 'undo'

        if self.WorkMode == 'cls':
            stat = 'done' if path.split('/')[-2] in ClassStatDict.keys() else 'undo'
        elif self.WorkMode == 'm_cls':
            txt = self.path_to(path, img2txt=True)
            if osp.exists(txt):
                with open(txt, 'r') as f:
                    if f.readlines():
                        stat = 'done'
        elif self.WorkMode == 'seg':
            json_path = self.path_to(path, img2json=True)
            if osp.exists(json_path):
                with open(json_path, 'r') as f:
                    content = json.load(f)
                stat = 'done' if content['polygons'] else 'undo'

        return stat

    def move_to_new_folder(self):
        path = self.file_select_dlg.getExistingDirectory(self.main_ui, '选择文件夹')
        if path:
            self.del_img(path)

    def m_cls_default_c(self):
        text, is_ok = QInputDialog().getText(self, '默认类别', '请输入类别名称', QLineEdit.Normal)
        if is_ok and text:
            self.default_c = text

    def m_cls_save(self):
        if self.in_edit_mode():
            lines = []
            txt_name = self.imgs[self.cur_i].split(os_sep)[-1][:-3] + 'txt'
            if '图片已删除' not in txt_name:
                button_layout = self.main_ui.groupBox_3.layout()
                for i in range(button_layout.rowCount()):
                    for j in range(button_layout.columnCount()):
                        button = button_layout.itemAtPosition(i, j).wid
                        if button.palette().button().color().name() == '#90ee90':
                            cls = button.text()
                            lines.append(f'{cls}\n')

                dir = self.img_root_path + '/多标签分类/标注'
                os.makedirs(dir, exist_ok=True)
                txt_path = f'{dir}/{txt_name}'

                if not lines and self.default_c != '':
                    lines.append(self.default_c)

                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                self.op_track.append(txt_path)

    def m_cls_to_button(self):  # 若已存在txt标注，直接显示在按钮上
        self.button_clear()

        txt_name = self.uniform_path(self.imgs[self.cur_i]).split('/')[-1][:-3] + 'txt'
        txt_path = f'{self.img_root_path}/多标签分类/标注/{txt_name}'

        if os.path.isfile(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            lines = [aa.strip() for aa in lines]
            button_layout = self.main_ui.groupBox_3.layout()

            for one in lines:
                for i in range(button_layout.rowCount()):
                    for j in range(button_layout.columnCount()):
                        button = button_layout.itemAtPosition(i, j).wid
                        if button.text() == one:
                            button.setStyleSheet('QPushButton { background-color: lightgreen }')

                            if self.is_first_marquee():  # 避免重复+1
                                ClassStatDict.setdefault(button.text(), 0)
                                ClassStatDict[button.text()] += 1

    def modify_seg_class_1(self):
        if self.main_ui.checkBox_3.isChecked():
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
            self.label_ui.listWidget.addItem(item.clone())
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
        path = self.file_select_dlg.getExistingDirectory(self.main_ui, '选择文件夹')
        if os.path.isdir(path):
            self.img_root_path = path
            self.main_ui.lineEdit.setText(self.img_root_path)
            self.reset_seg()

            if self.WorkMode == 'cls':
                sub_path = '单标签分类'
                if os.path.isdir(f'{self.img_root_path}/{sub_path}'):
                    self.files = glob.glob(f'{self.img_root_path}/{sub_path}/*')
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
                    self.init_button_group('temp.txt')
            elif self.WorkMode == 'm_cls':
                sub_path = '多标签分类/原图'
                if os.path.isdir(f'{self.img_root_path}/{sub_path}'):
                    self.imgs = glob.glob(f'{self.img_root_path}/{sub_path}/*')
                    self.imgs = [aa for aa in self.imgs if aa[-3:] in ('bmp', 'jpg', 'png')]
                    self.imgs.sort()
                    self.img_num = len(self.imgs)
            elif self.WorkMode == 'det':
                pass
            elif self.WorkMode == 'seg':
                sub_path = '分割/原图'
                if os.path.isdir(f'{self.img_root_path}/{sub_path}'):
                    self.imgs = glob.glob(f'{self.img_root_path}/{sub_path}/*')
                    self.imgs = [aa for aa in self.imgs if aa[-3:] in ('bmp', 'jpg', 'png')]
                    self.imgs.sort()
                    self.img_num = len(self.imgs)
                    if len(self.imgs):
                        self.reset_seg()

            if not os.path.isdir(f'{self.img_root_path}/{sub_path}'):
                QMessageBox.warning(self.main_ui, '未找到文件夹', f'未找到 "{sub_path}" 文件夹。')
                return

            if len(self.imgs):
                while self.marquees_layout.count() > 1:  # 清空self.marquee_layout
                    widget = self.marquees_layout.takeAt(0).widget()
                    widget.setParent(None)
                    self.marquees_layout.removeWidget(widget)

                self.cur_i = 0
                self.op_track = []
                self.default_c = ''
                self.cur_mar_i = -1
                self.show_img_status_info()
                self.marquee_add(the_first_one=True)

            if self.WorkMode == 'cls':
                self.cls_to_button()
            elif self.WorkMode == 'm_cls':
                self.m_cls_to_button()
            elif self.WorkMode == 'det':
                pass
            elif self.WorkMode == 'seg':
                self.polygons_to_img()

    def paint_changed_cv2_img(self):
        height, width, depth = self.cv2_img_changed.shape
        qimg = QImage(self.cv2_img_changed.astype('uint8').data, width, height, width * depth, QImage.Format_RGB888)
        self.main_ui.img_widget.paint_img(qimg, re_center=False)

    @staticmethod
    def path_to(path, img2json=False, img2png=False, img2txt=False):
        if img2json:
            return path.replace('分割/原图', '分割/标注')[:-3] + 'json'
        elif img2png:
            return path.replace('分割/原图', '分割/标注')[:-3] + 'png'
        elif img2txt:
            return path.replace('原图', '标注')[:-3] + 'txt'

    def polygons_to_img(self):
        json_path = self.path_to(self.imgs[self.cur_i], img2json=True)
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
                    self.main_ui.listWidget.addItem(item.clone())
                    self.label_ui.listWidget.addItem(item)

                if self.is_first_marquee():
                    ClassStatDict.setdefault(cate, 0)
                    ClassStatDict[cate] += 1

            self.main_ui.img_widget.json_to_polygons(json_path, json_data=(polygons, img_h, img_w))
            self.main_ui.img_widget.update()

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
        folders = glob.glob(f'{self.img_root_path}/单标签分类/*')

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
        self.label_ui.listWidget.clear()
        self.main_ui.img_widget.collection_ui.ui.listWidget.clear()

    def save_cls_classes(self):
        content, is_ok = self.input_dlg.getText(self.main_ui, '请输入名称', '请输入名称', QLineEdit.Normal)
        if is_ok:
            with open(f'{self.img_root_path}/{content}.txt', 'w', encoding='utf-8') as f:
                for one_c in ClassStatDict.keys():
                    f.writelines(f'{one_c}\n')

    def save_edited_img(self, save_all=False):
        if save_all:
            imgs_path = [aa for aa in self.imgs if aa != 'images/图片已删除.png']
        else:
            imgs_path = [self.imgs[self.cur_i]]

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
                self.label_ui.listWidget.addItem(item)
                self.main_ui.listWidget.addItem(item.clone())
                self.main_ui.listWidget_2.addItem(item.clone())
            else:
                item = self.main_ui.listWidget.findItems(f'{text}', Qt.MatchExactly)[0].clone()
                self.main_ui.listWidget_2.addItem(item)
                color = item.foreground().color()

            self.main_ui.img_widget.one_polygon_done(color.name(), text)
            ClassStatDict[text] += 1

            self.label_ui.close()

    def save_seg_file(self, img_path, json_polygons):  # 保存分割的json和png
        if img_path == 'images/图片已删除.png':
            return

        img_w, img_h = QPixmap(img_path).size().toTuple()
        img_name = img_path.split(os_sep)[-1]
        label_path = f'{self.img_root_path}/分割/标注'

        # save json
        json_dict = {'polygons': json_polygons, 'img_height': img_h, 'img_width': img_w}
        json_path = f'{label_path}/{img_name[:-4]}.json'

        with open(json_path, 'w') as f:
            json.dump(json_dict, f, sort_keys=False, ensure_ascii=False, indent=4)

        # save png
        seg_class_names = [aa for aa in ClassStatDict.keys()]
        seg_mask = get_seg_mask(seg_class_names, json_polygons, img_h, img_w)

        if seg_mask.__class__ == str:
            QMessageBox.critical(self.main_ui, '类别不存在', f'类别"{seg_mask}"不存在。')
            return

        if len(json_polygons) and not (0 < seg_mask.max() <= len(seg_class_names)):
            QMessageBox.critical(self.main_ui, '标注错误',
                                 f'当前仅有{len(seg_class_names)}类，但标注最大值为{seg_mask.max()}。')
            return

        if 'png' in img_name:
            img_name = 'seg_' + img_name
        cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(f'{label_path}/{img_name[:-4]}.png')

    def scan_img(self, last=False, next=False):
        if self.in_edit_mode() and self.WorkMode == 'seg':
            os.makedirs(f'{self.img_root_path}/分割/标注', exist_ok=True)
            json_polygons = self.has_polygons()
            self.save_seg_file(self.imgs[self.cur_i], json_polygons=json_polygons)

        if last:
            if 0 < self.cur_i < self.img_num:
                if self.WorkMode == 'm_cls':
                    self.m_cls_save()  # 在self.cur_i - 1之前先保存

                self.main_ui.img_widget.clear_all_polygons()
                self.main_ui.listWidget_2.clear()

                # 这3行必须是这个顺序 --------------
                self.marquee_move(left=True)
                self.cur_i -= 1
                self.show_img_status_info()
                # ------------------------------

                if self.WorkMode == 'cls':
                    self.cls_to_button()
                if self.WorkMode == 'm_cls':
                    self.m_cls_to_button()
                if self.WorkMode == 'seg':
                    self.polygons_to_img()

        elif next:
            if self.WorkMode == 'm_cls':
                self.m_cls_save()
            if self.cur_i < self.img_num - 1:
                self.main_ui.img_widget.clear_all_polygons()
                self.main_ui.listWidget_2.clear()
                self.marquee_move(right=True)
                self.cur_i += 1
                self.show_img_status_info()

                if self.WorkMode == 'cls':
                    self.cls_to_button()
                if self.WorkMode == 'm_cls':
                    self.m_cls_to_button()
                if self.WorkMode == 'seg':
                    self.polygons_to_img()

    def select_shape(self):
        selected_label_item.send(self.main_ui.listWidget_2.currentRow())

    def set_seg_edit_mode(self):
        self.main_ui.img_widget.set_mode(seg=True, seg_edit=self.main_ui.checkBox_3.isChecked())
        self.action_modify_one_class_jsons.setDisabled(not self.main_ui.checkBox_3.isChecked())
        self.action_del_one_class_jsons.setDisabled(not self.main_ui.checkBox_3.isChecked())

    def set_mcls_seg_stat(self):
        if self.WorkMode == 'm_cls':
            self.action_m_cls_default.setDisabled(self.main_ui.radioButton_read.isChecked() or
                                                  not self.main_ui.radioButton_mcls.isChecked())
        elif self.WorkMode in ('det', 'seg'):
            self.main_ui.checkBox_3.setDisabled(self.main_ui.radioButton_read.isChecked())

    def set_read_mode(self):
        if self.main_ui.checkBox_3.isChecked():
            self.main_ui.checkBox_3.setChecked(not self.main_ui.radioButton_read.isChecked())

    def set_shape_selected(self, i):
        self.main_ui.listWidget_2.item(i).setSelected(True)

    def set_tool_box(self):
        self.main_ui.img_widget.clear_scaled_img()
        self.main_ui.img_widget.clear_all_polygons()
        self.main_ui.img_widget.clear_widget_img_points()

        if self.main_ui.toolBox.currentIndex() == 0:
            if self.main_ui.radioButton_cls.isChecked():
                self.main_ui.img_widget.set_mode(cls=True)
            if self.main_ui.radioButton_mcls.isChecked():
                self.main_ui.img_widget.set_mode(m_cls=True)
            if self.main_ui.radioButton_det.isChecked():
                self.main_ui.img_widget.set_mode(det=True)
            if self.main_ui.radioButton_seg.isChecked():
                self.main_ui.img_widget.set_mode(seg=True)
        elif self.main_ui.toolBox.currentIndex() == 1:
            self.main_ui.img_widget.set_mode(ann=True)

    def set_work_mode(self):
        if self.main_ui.toolBox.currentIndex() == 1:
            self.main_ui.img_widget.set_mode(ann=True)

        if self.main_ui.radioButton_cls.isChecked():
            self.WorkMode = 'cls'
            self.main_ui.radioButton_read.setText('剪切')
            self.main_ui.radioButton_write.setText('复制')
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_mode(cls=True)
        else:
            self.main_ui.radioButton_read.setText('只读')
            self.main_ui.radioButton_write.setText('编辑')
            if self.main_ui.radioButton_mcls.isChecked():
                self.WorkMode = 'm_cls'
                if self.main_ui.toolBox.currentIndex() == 0:
                    self.main_ui.img_widget.set_mode(m_cls=True)
            elif self.main_ui.radioButton_det.isChecked():
                self.WorkMode = 'det'
                if self.main_ui.toolBox.currentIndex() == 0:
                    self.main_ui.img_widget.set_mode(det=True)
            elif self.main_ui.radioButton_seg.isChecked():
                self.WorkMode = 'seg'
                if self.main_ui.toolBox.currentIndex() == 0:
                    self.main_ui.img_widget.set_mode(seg=True)

        self.main_ui.page_4.setDisabled(self.main_ui.radioButton_cls.isChecked() or
                                        self.main_ui.radioButton_mcls.isChecked())

        self.main_ui.groupBox_3.setDisabled(self.main_ui.radioButton_det.isChecked() or
                                            self.main_ui.radioButton_seg.isChecked())

        self.main_ui.pushButton_101.setDisabled(not self.main_ui.radioButton_cls.isChecked())

        stat = self.main_ui.radioButton_read.isChecked() or self.main_ui.radioButton_cls.isChecked() \
               or self.main_ui.radioButton_mcls.isChecked()

        self.main_ui.checkBox_3.setDisabled(stat)

        self.main_ui.pushButton_auto_infer.setDisabled(self.main_ui.radioButton_cls.isChecked()
                                                       or self.main_ui.radioButton_mcls.isChecked())

        self.main_ui.pushButton_g_val.setDisabled(not self.main_ui.radioButton_seg.isChecked())
        self.main_ui.pushButton_g_train.setDisabled(not self.main_ui.radioButton_seg.isChecked())
        self.main_ui.pushButton_update_tv.setDisabled(not self.main_ui.radioButton_seg.isChecked())
        self.main_ui.pushButton_show_tv.setDisabled(not self.main_ui.radioButton_seg.isChecked())
        self.main_ui.action_get_sub_seg_png.setDisabled(not self.main_ui.radioButton_seg.isChecked())

        self.action_m_cls_default.setDisabled(self.main_ui.radioButton_read.isChecked() or
                                              not self.main_ui.radioButton_mcls.isChecked())

        ClassStatDict.clear()
        self.main_ui.img_widget.paint_img('images/bg.png')
        self.main_ui.img_widget.clear_all_polygons()
        self.update()

    def show_class_stastics(self):
        self.sub_window_stat = ClassStat()
        self.sub_window_stat.show()
        self.sub_window_stat.resize(self.sub_window_stat.class_list.size())

    def show_compare_img(self):
        path = self.file_select_dlg.getOpenFileName(self.main_ui, '选择图片', filter='图片类型 (*.png *.jpg *.bmp)')[0]
        if path:
            self.compare_window = BaseImgFrame()
            self.compare_window.setWindowTitle('对比图片')
            self.compare_window.paint_img(path)
            self.compare_window.show()

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
            self.main_ui.label_5.setText(self.uniform_path(self.bottom_img_text))

    def show_label_ui(self):
        self.label_ui.show()

    @staticmethod
    def show_menu(ob):  # 在鼠标位置显示菜单
        ob.exec(QCursor.pos())

    def show_train_val_label(self):
        if not self.has_categories():
            return

        self.tv_i = 0
        tv_path = self.file_select_dlg.getExistingDirectory(self.main_ui, '选择文件夹', dir=self.img_root_path)

        if tv_path:
            self.tv_imgs = sorted(glob.glob(f'{tv_path}/*'))

        self.seg_img_window = BaseImgFrame()
        self.seg_img_window.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.seg_img_window.setWindowTitle('分割原图')

        geo_self = self.frameGeometry()
        geo_sub = self.seg_img_window.frameGeometry()
        x1 = geo_self.left()
        y1 = int((geo_self.height() - geo_sub.height()) / 2)
        self.seg_img_window.move(x1, y1)

        self.seg_png_window = BaseImgFrame()
        self.seg_png_window.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.seg_png_window.setWindowTitle('分割标注')

        x2 = x1 + geo_sub.width()
        self.seg_png_window.move(x2, y1)

        ori_path = self.tv_imgs[self.tv_i]
        self.seg_img_window.paint_img(QPixmap(ori_path))
        self.seg_img_window.show()

        png_path = ori_path.replace('imgs', 'labels')[:-3] + 'png'
        qimg_png = self.get_qimg_png(png_path)
        self.seg_png_window.paint_img(qimg_png)
        self.seg_png_window.show()

    def show_xy_color(self, info):
        x, y, r, g, b = info
        self.main_ui.label_8.setText(f'X: {x}, Y: {y} &nbsp; &nbsp;'  # &nbsp; 加入空格
                                     f'<font color=red> R: {r}, </font>'
                                     f'<font color=green> G: {g}, </font>'
                                     f'<font color=blue> B: {b} </font>')

    def undo_painting(self):
        self.main_ui.img_widget.undo_stack.undo()

    def update_progress_auto_infer_value(self, info):
        self.progress_auto_infer.set_value(info)

    def update_progress_auto_infer_text(self, info):
        self.progress_auto_infer.set_text(info)

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

    @staticmethod
    def uniform_path(path):
        return path.replace('\\', '/').replace('\\\\', '/')