import pdb
import random
import shutil
import cv2
import numpy as np
import os
import json
import onnxruntime as ort
import sys
import time
import glob

from need.main_utils import connect_all_other_signals, init_menu
from copy import deepcopy
from os import path as osp
from PIL import Image, ImageEnhance
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QFileDialog, QInputDialog, QLineEdit, QWidget, \
    QHBoxLayout, QColorDialog, QListWidgetItem, QApplication, QGroupBox
from PySide6.QtWidgets import QMessageBox as QMB
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QPixmap, QImage, QColor, QFontMetrics, QIcon
from need.custom_widgets import *
from need.custom_threads import *
from need.custom_signals import StrSignal, ErrorSignal
from need.utils import get_seg_mask, uniform_path, AllClasses, qimage_to_array, get_datetime, file_remove, \
    glob_imgs, glob_labels, two_way_check, hhl_info, get_file_cmtime, MultiIndex

signal_select_class_ok = StrSignal()
signal_error2app = ErrorSignal()


# noinspection PyUnresolvedReferences
class ImgCls(QMainWindow):
    def __init__(self):
        super().__init__()
        with open('project.json', 'r', encoding='utf-8') as f:
            self.language = json.load(f)['language']

        self.image_folder = self.tr('原图')
        self.label_folder = self.tr('标注')
        self.tv_folder = self.tr('训练集&验证集')
        self.ann_folder = self.tr('注释图片')
        self.AllModes = MultiIndex((self.tr('单分类'), self.tr('多分类'), self.tr('语义分割'),
                                    self.tr('目标检测'), self.tr('实例分割')))
        self.WorkMode = self.AllModes[0]
        self.OneFileLabel = True
        self.SeparateLabel = False
        self.LabelUiCallByMo = False  # 用于区分self.label_ui是由新标注唤起还是由修改标注唤起
        self.EditImgMode = False
        self.marquee_num = 30  # 小图的最大数量, 越大占用内存越多
        self.marquee_size = 150
        self.scan_delay = 0

        loader = QUiLoader()
        loader.registerCustomWidget(CenterImgFrame)
        loader.registerCustomWidget(ClassButton)
        loader.registerCustomWidget(ClassListWidget)
        loader.registerCustomWidget(ShapeListWidget)
        loader.registerCustomWidget(ButtonWithHoverWindow)
        loader.registerCustomWidget(SearchBox)
        loader.registerCustomWidget(LabelTrainVal)
        loader.registerCustomWidget(LabelTrainBar)
        loader.registerCustomWidget(LabelValBar)

        self.main_ui = loader.load('main_window.ui')  # 主界面
        self.setCentralWidget(self.main_ui)
        self.setWindowTitle(self.tr('花火标注'))
        self.setWindowIcon(QIcon('images/icon.png'))
        self.resize(1280, 920)
        self.setFocusPolicy(Qt.StrongFocus)

        self.window_build_task = BuildTask()
        self.window_select_class = SelectItem(title=self.tr('类别'), button_signal=signal_select_class_ok)
        self.window_sem_class_changed = CustomMessageBox('information', self.tr('类别列表变化'))
        self.window_ann_saved = CustomMessageBox('information', self.tr('已保存'))
        self.window_version_remind = CustomMessageBox('question', self.tr('版本提醒'))
        self.window_choose_version = ChooseVersion(self.main_ui)

        self.thread_auto_save = AutoSave(5 * 60)  # 5min

        self.file_select_dlg = QFileDialog(self)
        self.input_dlg = QInputDialog(self)

        self.marquees = QWidget(self)
        self.marquees_layout = QHBoxLayout()
        self.marquees_layout.addStretch()
        self.marquees.setLayout(self.marquees_layout)
        self.main_ui.scrollArea.setWidget(self.marquees)

        self.set_seg_lists()
        self.reset_init_variables()
        init_menu(self)
        self.set_action_disabled()
        self.connect_signals()

        self.main_ui.img_widget.paint_img('images/bg.png')
        self.log_info('Application opened.', mark_line=True)

        # 获取字符串宽度
        # self.main_ui.toolBox.currentWidget().fontMetrics().boundingRect('hello')
        # 工具栏和状态栏
        # self.main_ui.toolbar = self.main_ui.addToolBar('toolbar')
        # tool_show_png = QAction('查看实例分割标注', self)
        # tool_show_png.triggered.connect(self.show_seg_png)
        # self.main_ui.toolbar.addAction(tool_show_png)
        # self.main_ui.statusBar().showMessage('Ready')

    def connect_signals(self):
        self.connect_buttons_signal()
        connect_all_other_signals(self)
        signal_select_class_ok.signal.connect(self.save_one_shape)
        sys.stderr = signal_error2app
        sys.stderr.signal.connect(self.log_sys_error)

    def changeEvent(self, event):  # 窗口大小改变时，背景图片大小也随着改变
        if not self.main_ui.lineEdit.text():
            self.main_ui.img_widget.mouseDoubleClickEvent(None, True)

    def closeEvent(self, e):
        self.window_build_task.close()
        if self.window_auto_infer_progress:
            self.window_auto_infer_progress.close()
        if self.window_class_stat:
            self.window_class_stat.close()
        if self.window_compare:
            self.window_compare.close()
        if self.window_marquee_img:
            self.window_marquee_img.close()
        if self.window_marquee_label:
            self.window_marquee_label.close()
        if self.window_usp_progress:
            self.window_usp_progress.close()

        self.save_backup_classes()
        self.save_one_file_json()
        self.thread_auto_save.terminate()

        with open('project.json', 'w', encoding='utf-8') as f:
            json.dump({'language': self.language}, f, sort_keys=False, ensure_ascii=False, indent=4)

        self.log_info('Application closed.', mark_line=True)
        self.close()

    def keyPressEvent(self, event):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.save_ann_img()
            elif event.key() == Qt.Key_Z:
                if self.main_ui.toolBox.currentIndex() == 1:
                    self.undo_painting()
                else:
                    self.main_ui.img_widget.remove_widget_img_pair()
        else:
            if event.key() == Qt.Key_A:
                self.scan_img(last=True)
            elif event.key() == Qt.Key_D:
                self.scan_img(next=True)

    def resizeEvent(self, event):
        font_metrics = QFontMetrics(self.main_ui.label_path.font())
        str_w = font_metrics.size(0, self.bottom_img_text).width()
        label_w = self.main_ui.label_path.width()

        if str_w > label_w - 12:  # 左下角信息自动省略
            elideNote = font_metrics.elidedText(self.bottom_img_text, Qt.ElideRight, label_w)
            self.main_ui.label_path.setText(elideNote)

    def about_hhl(self):
        self.hhl_info = hhl_info(self.language)
        self.hhl_info.show(clear_old=False)

    def add_to_train_val(self, dst_part, img_path=None, pass_one_file=False, pass_separate_file=False):
        if not self.has_img_root():
            return
        if not self.in_edit_mode():
            QMB.warning(self.main_ui, self.tr('模式错误'), self.tr('请先切换至编辑模式!'))
            return

        if img_path is None:  # 直接由按钮触发
            cur_path = self.imgs[self.cur_i]
        else:
            cur_path = img_path

        if '图片已删除' in cur_path:
            return

        img_name = cur_path.split('/')[-1]
        tv_tag = ['train', 'val']
        tv_tag.remove(dst_part)
        opp_part = tv_tag[0]

        if not self.has_labeled(cur_path):
            if self.WorkMode in self.AllModes[(0, 1)]:
                QMB.warning(self.main_ui, self.tr('图片未分类'), self.tr('当前图片尚未分类!'))
            elif self.WorkMode in self.AllModes[(2, 3, 4)]:
                QMB.warning(self.main_ui, self.tr('图片无标注'), self.tr('当前图片尚未标注!'))
            return

        if self.OneFileLabel and not pass_one_file:
            img_tv = self.label_file_dict['labels'][img_name]['tv']

            if img_tv == 'train' and dst_part == 'val':
                self.train_num -= 1
                self.val_num += 1
            elif img_tv == 'val' and dst_part == 'train':
                self.train_num += 1
                self.val_num -= 1
            elif img_tv == 'none':
                if dst_part == 'train':
                    self.train_num += 1
                elif dst_part == 'val':
                    self.val_num += 1

            self.label_file_dict['labels'][img_name]['tv'] = dst_part

        if self.SeparateLabel and not pass_separate_file:
            tv_img_path = f'{self.get_root("tv")}/imgs/{dst_part}'
            os.makedirs(tv_img_path, exist_ok=True)

            if self.WorkMode == self.AllModes[0]:
                c_name = self.cls_has_classified(cur_path)
                dst_path = f'{tv_img_path}/{c_name}'
                os.makedirs(dst_path, exist_ok=True)

                if img_path is None and self.current_tv() == opp_part:
                    file_remove(dst_path.replace(dst_part, opp_part) + f'/{img_name}')
                    if not self.OneFileLabel:
                        if opp_part == 'train':
                            self.train_num -= 1
                        elif opp_part == 'val':
                            self.val_num -= 1

                shutil.copy(cur_path, dst_path)
                self.remove_empty_cls_folder()
            elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                tv_label_path = f'{self.get_root("tv")}/labels/{dst_part}'
                os.makedirs(tv_label_path, exist_ok=True)

                if img_path is None and self.current_tv() == opp_part:
                    opp_img_path = tv_img_path.replace(dst_part, opp_part) + f'/{img_name}'
                    file_remove(opp_img_path)

                    opp_label_path = opp_img_path.replace('imgs', 'labels')
                    opp_txt = opp_label_path[:-3] + 'txt'
                    opp_png = opp_label_path[:-3] + 'png'
                    opp_json = opp_label_path[:-3] + 'json'
                    if self.WorkMode == self.AllModes[1]:
                        file_remove(opp_txt)
                    elif self.WorkMode == self.AllModes[2]:
                        file_remove([opp_json, opp_png])
                    elif self.WorkMode == self.AllModes[3]:
                        file_remove([opp_json, opp_txt])
                    elif self.WorkMode == self.AllModes[4]:
                        file_remove(opp_json)

                    if not self.OneFileLabel:
                        if opp_part == 'train':
                            self.train_num -= 1
                        elif opp_part == 'val':
                            self.val_num -= 1

                shutil.copy(cur_path, tv_img_path)

                txt = self.get_separate_label(cur_path, 'txt')
                png = self.get_separate_label(cur_path, 'png')
                json = self.get_separate_label(cur_path, 'json')
                if self.WorkMode == self.AllModes[1]:
                    shutil.copy(txt, tv_label_path)
                elif self.WorkMode == self.AllModes[2]:
                    shutil.copy(png, tv_label_path)
                    shutil.copy(json, tv_label_path)
                elif self.WorkMode == self.AllModes[3]:
                    shutil.copy(txt, tv_label_path)
                    shutil.copy(json, tv_label_path)
                elif self.WorkMode == self.AllModes[4]:
                    shutil.copy(json, tv_label_path)

            if not self.OneFileLabel:
                if dst_part == 'train':
                    self.train_num += 1
                elif dst_part == 'val':
                    self.val_num += 1

        self.set_tv_label()
        self.set_tv_bar()

    def after_get_self_imgs(self):
        self.img_num = len(self.imgs)
        if self.img_num:
            self.cur_i = 0
            self.cur_mar_i = -1
            self.clear_marquee_layout()
            self.show_img_status_info()
            self.marquee_add(the_first_one=True)

    def auto_inference(self):  # todo--------------------------------- 可以单开一个文件吗
        return

        os.makedirs(f'{self.task_root}/实例分割/自动标注', exist_ok=True)
        classes = AllClasses.classes()
        if len(classes) == 0:
            QMB.critical(self.main_ui, '未找到类别名称', '请先加载类别。')
            return

        QMB.information(self.main_ui, '加载onnx文件', '请选择一个onnx文件。')

        onnx_file = self.file_select_dlg.getOpenFileName(self.main_ui, '选择ONNX文件', filter='onnx (*.onnx)')[0]
        if not onnx_file:
            return
        re = QMB.question(self.main_ui, '自动推理',
                          f'"{self.task_root}/原图" 下的{len(self.imgs)}张图片将自动生成实例分割标注，继续吗？。',
                          QMB.Yes, QMB.No)
        if re != QMB.Yes:
            return

        try:
            sess = ort.InferenceSession(onnx_file, providers=["CUDAExecutionProvider"])
            self.window_auto_infer_progress = ProgressWindow(title='推理中', text_prefix='使用GPU推理中：')
        except:
            sess = ort.InferenceSession(onnx_file, providers=["CPUExecutionProvider"])
            self.window_auto_infer_progress = ProgressWindow(title='推理中', text_prefix='使用CPU推理中：')

        inputs = sess.get_inputs()
        if len(inputs) > 1:
            QMB.critical(self.main_ui, '输入错误', f'模型只能有一个输入，实际检测到{len(inputs)}个输入。')
            return

        in_type, in_shape, in_name = inputs[0].type, tuple(inputs[0].shape), inputs[0].name
        if in_type != 'tensor(uint8)':
            QMB.critical(self.main_ui, '输入错误', f'模型输入的类型必须为tensor(uint8)，实际为{in_type}。')
            return

        QMB.information(self.main_ui, '图片形状不匹配',
                        f'模型输入尺寸：{in_shape}，如果图片尺寸不匹配，图片将自动调整至需要的尺寸。')

        content, is_ok = self.input_dlg.getText(self.main_ui, f'请输入DP抽稀算法阈值, 轮廓点数最小值、最大值',
                                                '请输入整数，阈值越高，抽稀后轮廓点数越少，反之越多，默认为(2, 4, 50)',
                                                QLineEdit.Normal, text='2, 4, 50')
        if is_ok:
            try:
                dp_para = content.replace('，', ',').split(',')
                dp_para = [float(one.strip()) for one in dp_para]
            except:
                QMB.critical(self.main_ui, '格式错误', f'请输入正确的格式，参照：2, 4, 40。')
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
                QMB.critical(self.main_ui, '格式错误', f'请输入正确的格式，参照：16。')
                return
        else:
            return

        self.window_auto_infer_progress.show()

        self.inference_thread = RunInference(sess, self.imgs, AllClasses.classes(), dp_para, filter_area)
        self.inference_thread.start()

    def auto_inference_done(self):
        self.window_auto_infer_progress.set_text(f'已完成，推理结果存放在 "{self.task_root}/自动标注"。')

    def button_action(self):
        if not self.task_root:
            return
        button = self.sender()
        c_name = button.text()
        img_path = self.imgs[self.cur_i]
        img_name = img_path.split('/')[-1]
        if img_path == 'images/图片已删除.png':
            return

        if self.WorkMode == self.AllModes[0]:
            if self.task_root and c_name != '-':
                self.cv2_img_changed = None

                if self.OneFileLabel:
                    img_w, img_h = QPixmap(img_path).size().toTuple()
                    if self.label_file_dict['labels'].get(img_name):
                        self.label_file_dict['labels'][img_name]['class'] = c_name
                    else:
                        one = {'img_height': img_h, 'img_width': img_w, 'tv': 'none', 'class': c_name}
                        self.label_file_dict['labels'][img_name] = one

                if self.SeparateLabel:
                    if not self.version_remind():
                        return

                    label_path = f'{self.get_root("separate")}/{c_name}'
                    os.makedirs(label_path, exist_ok=True)
                    old_class = img_path.split('/')[-2]

                    if old_class != self.image_folder:
                        if old_class != c_name:
                            self.file_move(img_path, label_path)
                            self.cls_train_val_move(img_name, old_class, c_name)
                            self.imgs[self.cur_i] = f'{label_path}/{img_name}'  # 随着图片路径变化而变化
                            self.cls_op_track.append(('re_cls', self.cur_i, self.cur_mar_i, img_path, label_path))
                            self.show_label_to_ui()

                            QMB.information(self.main_ui, self.tr('移动图片'),
                                            self.tr('{}已从<font color=red>{}</font>移动至<font color=red>{}</font>。')
                                            .format(img_name, old_class, c_name))
                    else:
                        if self.main_ui.radioButton_read.isChecked():  # cut
                            self.file_move(img_path, label_path)
                            self.cls_op_track.append(('cut', self.cur_i, self.cur_mar_i, img_path, label_path))
                        elif self.main_ui.radioButton_write.isChecked():  # copy
                            self.file_copy(img_path, label_path)
                            self.cls_op_track.append(('copy', self.cur_i, self.cur_mar_i, img_path, label_path))

                        self.imgs[self.cur_i] = f'{label_path}/{img_name}'  # 随着图片路径变化而变化

                    if len(self.cls_op_track) > 100:
                        self.cls_op_track.pop(0)

                    self.remove_empty_cls_folder()

                self.go_next_img()

        elif self.WorkMode == self.AllModes[1]:
            if self.in_edit_mode():
                if c_name != '-':
                    if button.palette().button().color().name() == '#90ee90':
                        button.setStyleSheet('')
                    else:
                        button.setStyleSheet('QPushButton { background-color: lightgreen }')
            else:
                QMB.warning(self.main_ui, self.tr('模式错误'), self.tr('请先切换至编辑模式!'))

    def buttons_add_line(self):
        if self.WorkMode == self.AllModes[0]:
            button_layout = self.main_ui.groupBox_1.layout()
        elif self.WorkMode == self.AllModes[1]:
            button_layout = self.main_ui.groupBox_2.layout()

        new_line = QHBoxLayout()
        for i in range(4):
            new_button = ClassButton()
            new_button.setText('-')
            new_button.clicked.connect(self.button_action)
            new_line.addWidget(new_button)

        button_layout.addLayout(new_line)
        self.main_ui.setFocus()

    def buttons_clear(self):  # 清除按钮组中按钮的stylesheet
        if self.WorkMode == self.AllModes[0]:
            button_layout = self.main_ui.groupBox_1.layout()
        elif self.WorkMode == self.AllModes[1]:
            button_layout = self.main_ui.groupBox_2.layout()

        for i in range(button_layout.count()):
            item = button_layout.itemAt(i)
            for j in range(item.count()):
                item.itemAt(j).widget().setStyleSheet('')

    def buttons_remove_line(self):
        if self.WorkMode == self.AllModes[0]:
            button_layout = self.main_ui.groupBox_1.layout()
        elif self.WorkMode == self.AllModes[1]:
            button_layout = self.main_ui.groupBox_2.layout()

        count = button_layout.count()
        line = button_layout.takeAt(count - 1)
        for i in range(4):
            widget = line.takeAt(0).widget()
            widget.setParent(None)

        self.main_ui.setFocus()

    def change_cross_color(self):
        if self.WorkMode == self.AllModes[3]:
            color = QColorDialog.getColor()
            if color.isValid():
                self.main_ui.pushButton_cross_color.setStyleSheet('QPushButton { background-color: %s }' % color.name())
                self.main_ui.img_widget.change_pen(det_cross_color=QColor(color.name()))

    def change_font_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.main_ui.pushButton_font_color.setStyleSheet('QPushButton { color: %s }' % color.name())
            self.main_ui.img_widget.change_font(ann_font_color=QColor(color.name()))

    def change_font_size(self):
        self.main_ui.img_widget.change_font(ann_font_size=self.main_ui.spinBox_5.value())

    def change_one_class_category(self):
        new_c, ok = self.input_dlg.getText(self.main_ui, self.tr('修改类别'), self.tr('请输入类别名称'),
                                           QLineEdit.Normal)
        if ok:
            new_c = new_c.strip()
            cur_c = self.main_ui.class_list.currentItem().text()
            re = QMB.question(self.main_ui, self.tr('修改类别'),
                              self.tr('确定将所有<font color=red>{}</font>修改为'
                                      '<font color=red>{}</font>吗？').format(cur_c, new_c))
            if re == QMB.Yes:
                self.thread_cocc = ChangeOneClassCategory(self.imgs, self.WorkMode, self.OneFileLabel,
                                                          self.SeparateLabel, deepcopy(self.label_file_dict),
                                                          AllClasses.classes(), cur_c, new_c, self)
                self.thread_cocc.start()
                self.show_waiting_label()

    def change_one_class_category_done(self, info):
        done, new_c = info
        if done:
            if self.OneFileLabel:
                self.label_file_dict = self.thread_cocc.label_file_dict

            if new_c in AllClasses.classes():
                self.main_ui.class_list.del_row(self.main_ui.class_list.currentRow())
            else:
                self.main_ui.class_list.modify_cur_c(new_c)

            self.save_backup_classes()
            QMB.information(self.main_ui, self.tr('修改完成'), self.tr('已完成, 类别列表已备份，请重新打开目录。'))
            self.set_work_mode()

        self.waiting_label.stop()
        self.waiting_label.close()

    def change_pen_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.change_pen(seg_pen_color=QColor(color.name()))
            elif self.main_ui.toolBox.currentIndex() == 1:
                self.main_ui.img_widget.change_pen(ann_pen_color=QColor(color.name()))

    def change_pen_size(self):
        if self.main_ui.toolBox.currentIndex() == 0:
            self.main_ui.img_widget.change_pen(seg_pen_size=self.main_ui.spinBox.value())
        elif self.main_ui.toolBox.currentIndex() == 1:
            self.main_ui.img_widget.change_pen(ann_pen_size=self.main_ui.spinBox_6.value())

    def change_shape_type(self):
        signal_shape_type.send(self.main_ui.comboBox_2.currentText())

    def check_dataset(self):
        if self.has_img_root():
            if self.check_labels():
                self.check_train_val_set()

    def check_draw_enable(self):
        if not self.task_root:
            QMB.warning(self.main_ui, self.tr('未加载任务'), self.tr('请先加载任务！'))
        elif not self.in_edit_mode():
            QMB.warning(self.main_ui, self.tr('模式错误'), self.tr('请先切换至编辑模式！'))
        elif self.main_ui.pushButton_bg.objectName() == 'bg':
            QMB.warning(self.main_ui, self.tr('已标注为背景'), self.tr('当前图片已作为纯背景标注！'))

    def check_labels(self):
        if self.OneFileLabel:
            redu_num, unla_num = 0, 0
            redu_list, unla_list = [], []
            img_names = [aa.split('/')[-1] for aa in self.imgs]

            for one in self.label_file_dict['labels'].keys():
                if one not in img_names:
                    redu_list.append(one)
                    redu_num += 1

            QMB.information(self.main_ui, self.tr('统一标注模式'),
                            self.tr('{}条标注记录找不到对应"原图"。').format(redu_num))

            if redu_num > 0:
                choice = QMB.question(self.main_ui, self.tr('统一标注模式'),
                                      self.tr('清理找不到对应"原图"的标注记录吗？'))
                if choice == QMB.Yes:
                    for one in redu_list:
                        self.label_file_dict['labels'].pop(one)

                    QMB.information(self.main_ui, self.tr('统一标注模式'), self.tr('共清理{}条记录。').format(redu_num))

            for i, one in enumerate(img_names):
                if not self.label_file_dict['labels'].get(one):
                    unla_list.append(self.imgs[i])
                    unla_num += 1

            QMB.information(self.main_ui, self.tr('统一标注模式'), self.tr('{}张"原图"未标注。').format(unla_num))

            if unla_num > 0:
                if self.remove_redu_files(unla_list, self.tr('统一标注模式'), self.tr('清理未标注的"原图"吗？')):
                    QMB.information(self.main_ui, self.tr('统一标注模式'), self.tr('清理"原图"后需要重新打开目录。'))
                    self.set_work_mode()
                    return False
        if self.SeparateLabel:
            redu_num, unla_num = 0, 0
            redu_list, unla_list = [], []
            if self.WorkMode == self.AllModes[0]:
                for one in self.imgs:
                    category = self.cls_has_classified(one)
                    if not category:
                        unla_list.append(one)
                        unla_num += 1

                QMB.information(self.main_ui, self.tr('独立标注模式'), self.tr('{}张"原图"未标注。').format(unla_num))
            elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                label_files = glob_labels(f'{self.get_root("separate")}')
                unla_list, redu_list = two_way_check(self.imgs, label_files)
                unla_num, redu_num = len(unla_list), len(redu_list)

                QMB.information(self.main_ui, self.tr('独立标注模式'),
                                self.tr('{}个标注文件找不到对应的"原图"，{}张"原图"未标注。').format(redu_num, unla_num))

                if redu_num > 0:
                    self.remove_redu_files(redu_list, self.tr('独立标注模式'),
                                           self.tr('清理找不到对应"原图"的标注文件吗？'))

            if unla_num > 0:
                if self.remove_redu_files(unla_list, self.tr('独立标注模式'), self.tr('清理未标注的"原图"吗？')):
                    QMB.information(self.main_ui, self.tr('独立标注模式'), self.tr('清理"原图"后需要重新打开目录。'))
                    self.set_work_mode()
                    return False
        return True

    def check_train_val_set(self):
        if self.SeparateLabel:
            # 1 清理训练/验证集里不在原图中的图片
            t_imgs = glob_imgs(f'{self.get_root("tv")}/imgs/train', self.WorkMode == self.AllModes[0])
            v_imgs = glob_imgs(f'{self.get_root("tv")}/imgs/val', self.WorkMode == self.AllModes[0])
            t_redu, _ = two_way_check(t_imgs, self.imgs, one_way=True)
            v_redu, _ = two_way_check(v_imgs, self.imgs, one_way=True)

            QMB.information(self.main_ui, self.tr('独立标注模式'),
                            self.tr('训练集中{}张图片不在"原图"中，验证集中{}张图片不在"原图"中。')
                            .format(len(t_redu), len(v_redu)))

            if t_redu:
                result = self.remove_redu_files(t_redu, self.tr('独立标注模式'),
                                                self.tr('清理训练集里不在"原图"中的图片吗？'))
                if result:
                    t_imgs = glob_imgs(f'{self.get_root("tv")}/imgs/train', self.WorkMode == self.AllModes[0])
                    self.train_num = len(t_imgs)
                    self.set_tv_bar()
            if v_redu:
                result = self.remove_redu_files(v_redu, self.tr('独立标注模式'),
                                                self.tr('清理验证集里不在"原图"中的图片吗？'))
                if result:
                    v_imgs = glob_imgs(f'{self.get_root("tv")}/imgs/val', self.WorkMode == self.AllModes[0])
                    self.val_num = len(v_imgs)
                    self.set_tv_bar()

            # 2 清理训练/验证集里重复的图片
            t_names = [aa.split('/')[-1] for aa in t_imgs]
            v_names = [aa.split('/')[-1] for aa in v_imgs]
            dupli_names = list(set(t_names).intersection(set(v_names)))
            if dupli_names:
                dupli_num = len(dupli_names)
                choice = QMB.question(self.main_ui, self.tr('独立标注模式'),
                                      self.tr('训练集和验证集有{}张重复的图片，清理<font color=red>'
                                              '训练集</font>中的这些图片吗？').format(dupli_num))
                if choice == QMB.Yes:
                    for one in t_imgs:
                        if one.split('/')[-1] in dupli_names:
                            file_remove(one)

                    QMB.information(self.main_ui, self.tr('独立标注模式'),
                                    self.tr('共清理{}个文件。').format(dupli_num))
                    t_imgs = glob_imgs(f'{self.get_root("tv")}/imgs/train', self.WorkMode == self.AllModes[0])
                    self.train_num = len(t_imgs)
                    self.set_tv_bar()

                if choice == QMB.No:
                    choice = QMB.question(self.main_ui, self.tr('独立标注模式'),
                                          self.tr('训练集和验证集有{}张重复的图片，清理<font color=red>'
                                                  '验证集</font>中的这些图片吗？').format(dupli_num))
                    if choice == QMB.Yes:
                        for one in v_imgs:
                            if one.split('/')[-1] in dupli_names:
                                file_remove(one)

                        QMB.information(self.main_ui, self.tr('独立标注模式'),
                                        self.tr('共清理{}个文件。').format(dupli_num))
                        v_imgs = glob_imgs(f'{self.get_root("tv")}/imgs/val', self.WorkMode == self.AllModes[0])
                        self.val_num = len(v_imgs)
                        self.set_tv_bar()

            # 3 清理训练/验证集里找不到图片的标注
            if self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                t_labels = glob_labels(f'{self.get_root("tv")}/labels/train')
                v_labels = glob_labels(f'{self.get_root("tv")}/labels/val')

                t_r_imgs, t_r_labels = two_way_check(t_imgs, t_labels)
                v_r_imgs, v_r_labels = two_way_check(v_imgs, v_labels)

                QMB.information(self.main_ui, self.tr('独立标注模式'),
                                self.tr('训练集中{}张图片找不到对应的标注，{}个标注找不到对应的图片。\n'
                                        '验证集中{}张图片找不到对应的标注，{}个标注找不到对应的图片。')
                                .format((len(t_r_imgs)), len(t_r_labels), len(v_r_imgs), len(v_r_labels)))

                if t_r_imgs:
                    if self.remove_redu_files(t_r_imgs, self.tr('独立标注模式'),
                                              self.tr('清理训练集中找不到对应标注的图片吗？')):
                        self.get_tv_num()
                        self.set_tv_bar()
                if t_r_labels:
                    self.remove_redu_files(t_r_labels, self.tr('独立标注模式'),
                                           self.tr('清理训练集中找不到对应图片的标注吗？'))
                if v_r_imgs:
                    if self.remove_redu_files(v_r_imgs, self.tr('独立标注模式'),
                                              self.tr('清理验证集中找不到对应标注的图片吗？')):
                        self.get_tv_num()
                        self.set_tv_bar()
                if v_r_labels:
                    self.remove_redu_files(v_r_labels, self.tr('独立标注模式'),
                                           self.tr('清理验证集中找不到对应图片的标注吗？'))

            self.remove_empty_cls_folder()

    def clear_marquee_layout(self):
        while self.marquees_layout.count() > 1:
            widget = self.marquees_layout.takeAt(0).widget()
            widget.setParent(None)
            self.marquees_layout.removeWidget(widget)

    def clear_painted_img(self):
        self.main_ui.img_widget.clear_scaled_img(to_undo=True)

    def clear_shape_info(self):
        self.main_ui.listWidget_sem.clear()
        self.main_ui.listWidget_det.clear()
        self.main_ui.listWidget_ins.clear()

    def cls_back(self):
        if self.cls_op_track:
            op, cur_i, cur_mar_i, ori_path, cur_path = self.cls_op_track.pop()

            path_split = ori_path.split('/')
            ori_path = '/'.join(path_split[:-1])
            img_name = path_split[-1]

            if self.OneFileLabel:
                if op in ('cut', 'copy'):
                    self.label_file_dict['labels'][img_name]['class'] = ''
                elif op == 're_cls':
                    self.label_file_dict['labels'][img_name]['class'] = ori_path.split('/')[-1]

            if self.SeparateLabel:
                if op == 'cut':
                    self.file_move(uniform_path(osp.join(cur_path, img_name)), ori_path)
                elif op == 'copy':
                    file_remove(osp.join(cur_path, img_name))
                elif op == 're_cls':
                    self.file_move(uniform_path(osp.join(cur_path, img_name)), ori_path)
                    self.cls_train_val_move(img_name, cur_path.split('/')[-1], ori_path.split('/')[-1])

                self.imgs[cur_i] = uniform_path(osp.join(ori_path, img_name))
                if op != 're_cls':
                    self.marquees_layout.itemAt(cur_mar_i).widget().set_stat('undo')

            self.show_label_to_ui()
            QMB.information(self.main_ui, self.tr('撤销操作'), self.tr('已撤销: ') +
                            f'{img_name}, {ori_path} --> {cur_path}。')

            self.remove_empty_cls_folder()

    def cls_has_classified(self, img_path=None):  # 查看单分类，多分类模式下，图片是否已分类
        path = img_path if img_path else self.imgs[self.cur_i]
        if '图片已删除' in path:
            return False

        if self.WorkMode in self.AllModes[(0, 1)]:
            if self.OneFileLabel:
                img_name = path.split('/')[-1]
                img_dict = self.label_file_dict['labels'].get(img_name)
                if img_dict:
                    category = img_dict['class']
                    if category:
                        return category
                return False
            elif self.SeparateLabel:
                if self.WorkMode == self.AllModes[0]:
                    split = uniform_path(path).split('/')[-2]
                    if split != self.image_folder:
                        return split
                    return False
                elif self.WorkMode == self.AllModes[1]:
                    txt = self.get_separate_label(path, 'txt')
                    if osp.exists(txt):
                        with open(txt, 'r', encoding='utf-8') as f:
                            content = f.readlines()
                            classes = [aa.strip() for aa in content]
                        return classes
                    return False

    def cls_to_button(self):
        self.buttons_clear()
        category = self.cls_has_classified()
        has_this_class = False
        if category:
            button_layout = self.main_ui.groupBox_1.layout()
            for i in range(button_layout.count()):
                item = button_layout.itemAt(i)
                for j in range(item.count()):
                    button = item.itemAt(j).widget()
                    if button.text() == category:
                        button.setStyleSheet('QPushButton { background-color: lightgreen }')
                        return

            if not has_this_class:
                for i in range(button_layout.count()):
                    item = button_layout.itemAt(i)
                    for j in range(item.count()):
                        button = item.itemAt(j).widget()
                        if button.text() == '-':
                            button.setText(category)
                            button.setStyleSheet('QPushButton { background-color: lightgreen }')
                            return

    def cls_train_val_move(self, img_name, old_c, new_c):
        img_path = f'{self.get_root("tv")}/imgs/train/{old_c}/{img_name}'
        if osp.exists(img_path):
            dir_path = f'{self.get_root("tv")}/imgs/train/{new_c}'
            os.makedirs(dir_path, exist_ok=True)
            self.file_move(img_path, dir_path)

        img_path = f'{self.get_root("tv")}/imgs/val/{old_c}/{img_name}'
        if osp.exists(img_path):
            dir_path = f'{self.get_root("tv")}/imgs/val/{new_c}'
            os.makedirs(dir_path, exist_ok=True)
            self.file_move(img_path, dir_path)

    def connect_buttons_signal(self):
        layouts = [self.main_ui.groupBox_1.layout(), self.main_ui.groupBox_2.layout()]
        for lo in layouts:
            for i in range(lo.count()):
                item = lo.itemAt(i)
                for j in range(item.count()):
                    button = item.itemAt(j).widget()
                    clicked_signal = button.metaObject().method(37)  # 37为信号clicked的索引
                    if not button.isSignalConnected(clicked_signal):  # 避免信号重复连接
                        button.clicked.connect(self.button_action)

    def current_img_name(self):
        return self.imgs[self.cur_i].split('/')[-1]

    def current_shape_info_widget(self):
        if self.WorkMode == self.AllModes[2]:
            lw = self.main_ui.listWidget_sem
        elif self.WorkMode == self.AllModes[3]:
            lw = self.main_ui.listWidget_det
        elif self.WorkMode == self.AllModes[4]:
            lw = self.main_ui.listWidget_ins
        else:
            lw = None

        return lw

    def current_tv(self):
        return self.main_ui.label_train_val.text()

    def current_version(self):
        return self.main_ui.lineEdit_version.text()

    def del_all_shapes(self, del_all=True):
        if del_all:
            self.main_ui.img_widget.clear_all_polygons()
            self.main_ui.shape_list.clear()
        else:
            self.main_ui.img_widget.del_polygons()

        self.main_ui.setFocus()

    def del_existed_file(self, cur_path, file_path):
        if cur_path == file_path:
            raise SystemError('func: del_existed_file, 路径相同, 请检查。')

        if osp.exists(file_path):
            choice = QMB.question(self.main_ui, self.tr('文件已存在'), self.tr('{}已存在，要覆盖吗？').format(file_path))
            if choice == QMB.Yes:
                os.remove(file_path)
                return True
            elif choice == QMB.No:  # 右上角关闭按钮也返回QMB.No
                return False
        else:
            return True

    def del_img(self, dst_path=None):
        if not (0 <= self.cur_i < len(self.imgs)):
            return
        img_path = self.imgs[self.cur_i]
        img_name = img_path.split('/')[-1]
        if '图片已删除' in img_name:
            return

        if self.EditImgMode:
            file_remove(img_path)
        else:
            if dst_path is None:
                path_del_img = f'{self.task_root}/deleted/{self.WorkMode}/{self.image_folder}'
            else:
                path_del_img = dst_path

            os.makedirs(path_del_img, exist_ok=True)
            self.file_move(img_path, path_del_img)

            if self.OneFileLabel:
                if self.label_file_dict['labels'].get(img_name):
                    self.label_file_dict['labels'].pop(img_name)

            if self.SeparateLabel:
                if self.WorkMode == self.AllModes[0]:
                    if self.main_ui.radioButton_write.isChecked():  # 复制模式
                        file_remove(f'{self.get_root("img")}/{img_name}')

                    c_name = self.cls_has_classified()
                    if file_remove(f'{self.get_root("tv")}/imgs/train/{c_name}/{img_name}'):
                        self.train_num -= 1
                    if file_remove(f'{self.get_root("tv")}/imgs/val/{c_name}/{img_name}'):
                        self.val_num -= 1

                    self.remove_empty_cls_folder()
                elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                    if file_remove(f'{self.get_root("tv")}/imgs/train/{img_name}'):
                        self.train_num -= 1
                    if file_remove(f'{self.get_root("tv")}/imgs/val/{img_name}'):
                        self.val_num -= 1

                    path_del_label = f'{self.task_root}/deleted/{self.WorkMode}/{self.label_folder}'
                    os.makedirs(path_del_label, exist_ok=True)

                    txt_path = self.get_separate_label(img_path, 'txt')
                    png_path = self.get_separate_label(img_path, 'png')
                    json_path = self.get_separate_label(img_path, 'json')
                    t_txt_path = f'{self.get_root("tv")}/labels/train/{txt_path.split("/")[-1]}'
                    v_txt_path = f'{self.get_root("tv")}/labels/val/{txt_path.split("/")[-1]}'
                    t_png_path = f'{self.get_root("tv")}/labels/train/{png_path.split("/")[-1]}'
                    v_png_path = f'{self.get_root("tv")}/labels/val/{png_path.split("/")[-1]}'
                    t_json_path = f'{self.get_root("tv")}/labels/train/{json_path.split("/")[-1]}'
                    v_json_path = f'{self.get_root("tv")}/labels/val/{json_path.split("/")[-1]}'

                    if self.WorkMode == self.AllModes[1]:
                        if osp.exists(txt_path):
                            self.file_move(txt_path, path_del_label)
                            file_remove([t_txt_path, v_txt_path])
                    elif self.WorkMode == self.AllModes[2]:
                        if osp.exists(png_path):
                            self.file_move(png_path, path_del_label)
                            file_remove([t_png_path, v_png_path])
                        if osp.exists(json_path):
                            self.file_move(json_path, path_del_label)
                            file_remove([t_json_path, v_json_path])
                    elif self.WorkMode == self.AllModes[3]:
                        if osp.exists(txt_path):
                            self.file_move(txt_path, path_del_label)
                            file_remove([t_txt_path, v_txt_path])
                        if osp.exists(json_path):
                            self.file_move(json_path, path_del_label)
                            file_remove([t_json_path, v_json_path])
                    elif self.WorkMode == self.AllModes[4]:
                        if osp.exists(json_path):
                            self.file_move(json_path, path_del_label)
                            file_remove([t_json_path, v_json_path])

            self.set_tv_bar()

        self.imgs[self.cur_i] = 'images/图片已删除.png'  # 将删除的图片替换为背景图片
        self.show_img_status_info()
        del_map = QPixmap('images/图片已删除.png').scaled(self.marquee_size, self.marquee_size, Qt.KeepAspectRatio)
        self.marquees_layout.itemAt(self.cur_mar_i).widget().setPixmap(del_map, del_img=True)
        self.go_next_img()

    def del_shape(self, i):
        self.main_ui.shape_list.del_row(i)

        lw = self.current_shape_info_widget()
        if lw and lw.count():
            lw.takeItem(i)

    def delete_one_class_jsons(self):
        c_name = self.main_ui.class_list.currentItem().text()
        re = QMB.question(self.main_ui, self.tr('删除类别'), self.tr('确定删除所有<font color=red>{}</font>标注吗？')
                          .format(c_name))

        if re == QMB.Yes:
            # 删除某一类后，若图片无标注，则对应的标注文件会删除，原图不会，train和val里的对应图片和标注都会删除
            self.thread_docl = DeleteOneClassLabels(self.imgs, self.WorkMode, self.OneFileLabel,
                                                    self.SeparateLabel, deepcopy(self.label_file_dict),
                                                    AllClasses.classes(), c_name, self)
            self.thread_docl.start()
            self.show_waiting_label()

    def delete_one_class_jsons_done(self, done):
        if done:
            if self.OneFileLabel:
                self.label_file_dict = self.thread_docl.label_file_dict

            self.main_ui.class_list.del_row(self.main_ui.class_list.currentRow())
            self.save_backup_classes()
            QMB.information(self.main_ui, self.tr('删除完成'), self.tr('已完成, 类别列表已备份，请重新打开目录。'))
            self.set_work_mode()

        self.waiting_label.stop()
        self.waiting_label.close()

    def disable_some_widgets(self):
        self.main_ui.tabWidget.setDisabled(True)
        self.main_ui.groupBox_6.setDisabled(True)
        self.main_ui.groupBox_7.setDisabled(True)
        self.main_ui.label_train.setDisabled(True)
        self.main_ui.label_val.setDisabled(True)
        self.main_ui.toolBox.setDisabled(True)
        self.main_ui.pushButton_pin.setDisabled(True)
        self.main_ui.label_train_val.setDisabled(True)

    def edit_img(self):
        folder = self.file_select_dlg.getExistingDirectory(self.main_ui, self.tr('选择文件夹'))
        if folder:
            self.set_work_mode()
            self.EditImgMode = True
            self.disable_some_widgets()
            self.task_root = folder
            self.imgs = glob_imgs(folder)
            self.after_get_self_imgs()

    def export_classes(self):
        txt, is_ok = QInputDialog().getText(self, self.tr('名称'), self.tr('请输入导出txt的名称。'),
                                            QLineEdit.Normal, text='classes')
        if is_ok:
            lines = ''
            name = f'{txt}_{self.current_version()}'
            txt_path = f'{self.get_root("version")}/{name}.txt'
            for one_c in AllClasses.classes():
                lines += f'{one_c},\n'

            with open(txt_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            QMB.information(self.main_ui, self.tr('已完成'), self.tr('已导出到{}。').format(txt_path))

        self.main_ui.setFocus()

    def file_copy(self, src_path, dst_path):
        new_file_path = osp.join(dst_path, src_path.split('/')[-1])
        if self.del_existed_file(src_path, new_file_path):
            shutil.copy(src_path, dst_path)

    def file_move(self, src_path, dst_dir):
        new_file_path = osp.join(dst_dir, src_path.split('/')[-1])
        if self.del_existed_file(src_path, new_file_path):
            shutil.move(src_path, dst_dir)

    def fold_list(self):
        button = self.sender()
        button_name = button.objectName()
        sh = button.styleSheet()

        if button_name == 'pushButton_class_list':
            self.main_ui.class_list.setVisible(not self.main_ui.class_list.isVisible())
        elif button_name == 'pushButton_shape_list':
            self.main_ui.shape_list.setVisible(not self.main_ui.shape_list.isVisible())
        elif button_name == 'pushButton_tag_list':
            self.main_ui.tag_list.setVisible(not self.main_ui.tag_list.isVisible())

        sh1, sh2 = sh.split('background-color')
        if '(230, 229, 255)' in sh:
            new_sh = sh1 + 'background-color: rgb(220, 220, 220);'
        elif '(220, 220, 220)' in sh:
            new_sh = sh1 + 'background-color: rgb(230, 229, 255);'

        button.setStyleSheet(new_sh)

    def has_labeled(self, img_path):
        img_name = img_path.split('/')[-1]
        if self.OneFileLabel:
            if self.label_file_dict['labels'].get(img_name):
                return True
            return False
        elif self.SeparateLabel:
            if self.WorkMode in self.AllModes[(0, 1)]:
                if self.cls_has_classified(img_path):
                    return True
            elif self.WorkMode in self.AllModes[(2, 3, 4)]:
                json_path = self.get_separate_label(img_path, 'json')
                if osp.exists(json_path):
                    return True
            return False

    def generate_train(self):
        if not self.has_img_root():
            return
        if not self.in_edit_mode():
            QMB.warning(self.main_ui, self.tr('模式错误'), self.tr('请先切换至编辑模式!'))
            return

        if self.OneFileLabel:
            for k, v in self.label_file_dict['labels'].items():
                if v['tv'] != 'val':
                    if self.WorkMode == self.AllModes[0] and self.SeparateLabel:
                        img_path = f'{self.get_root("img")}/{v["class"]}/{k}'
                        assert osp.exists(img_path), f'Error, {img_path} does not exist.'
                    else:
                        img_path = f'{self.get_root("img")}/{k}'
                    self.add_to_train_val('train', img_path, pass_separate_file=True)

        if self.SeparateLabel:
            choice = QMB.question(self.main_ui, self.tr('独立标注模式'), self.tr('训练集将被覆盖，继续吗？'))
            if choice == QMB.Yes:
                if not self.OneFileLabel:
                    self.train_num = 0

                if osp.exists(f'{self.get_root("tv")}/imgs/train'):
                    shutil.rmtree(f'{self.get_root("tv")}/imgs/train')
                if self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                    if osp.exists(f'{self.get_root("tv")}/labels/train'):
                        shutil.rmtree(f'{self.get_root("tv")}/labels/train')

                val_img_list = glob_imgs(f'{self.get_root("tv")}/imgs/val', self.WorkMode == self.AllModes[0])
                val_img_list = [one.split('/')[-1] for one in val_img_list]
                for one in self.imgs:
                    if self.has_labeled(one) and one.split('/')[-1] not in val_img_list:
                        self.add_to_train_val('train', one, pass_one_file=True)

        QMB.information(self.main_ui, self.tr('已完成'), self.tr('已完成。'))

    def get_img_tv(self, img_path):
        img_name = img_path.split('/')[-1]
        if self.OneFileLabel:
            if self.label_file_dict['labels'].get(img_name):
                return self.label_file_dict['labels'][img_name]['tv']
            else:
                return 'none'
        elif self.SeparateLabel:
            if self.WorkMode == self.AllModes[0]:
                c_name = self.cls_has_classified(img_path)
                if osp.exists(f'{self.get_root("tv")}/imgs/train/{c_name}/{img_name}'):
                    return 'train'
                elif osp.exists(f'{self.get_root("tv")}/imgs/val/{c_name}/{img_name}'):
                    return 'val'
                else:
                    return 'none'
            elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                if osp.exists(f'{self.get_root("tv")}/imgs/train/{img_name}'):
                    return 'train'
                elif osp.exists(f'{self.get_root("tv")}/imgs/val/{img_name}'):
                    return 'val'
                else:
                    return 'none'

    def get_info_text(self, polygon):
        if self.WorkMode == self.AllModes[3]:
            points = polygon['img_points']
            width = points[1][0] - points[0][0]
            height = points[1][1] - points[0][1]
            text = self.tr('类别：{}\n宽度：{}\n高度：{}\n').format(polygon['category'], width, height)
        elif self.WorkMode in self.AllModes[(2, 4)]:
            img_path = self.imgs[self.cur_i]
            img_w, img_h = QPixmap(img_path).size().toTuple()
            mask = get_seg_mask(['fake'], [polygon], img_h, img_w, value=1)
            mask = (mask > 0).astype('uint8')
            area = mask.sum()
            cv2_img = cv2.imdecode(np.fromfile(img_path, dtype='uint8'), cv2.IMREAD_COLOR)
            img_masked = cv2_img * (mask[:, :, None])
            color_avg = (img_masked.sum((0, 1)) / area).astype('uint8').tolist()
            text = self.tr('类别：{}\n面积：{}\n平均灰度：{}\n').format(polygon['category'], area, color_avg)

        return text

    def get_qimg_png(self, img_path):
        seg_mask = None
        classes = AllClasses.classes()
        if self.OneFileLabel:
            img_name = img_path.split('/')[-1]
            img_dict = self.label_file_dict['labels'].get(img_name)
            if img_dict:
                polygons, img_h, img_w = img_dict['polygons'], img_dict['img_height'], img_dict['img_width']
                if polygons == ['bg']:
                    polygons = []
                seg_mask = get_seg_mask(classes, polygons, img_h, img_w, ins_seg=self.WorkMode == self.AllModes[4])
        elif self.SeparateLabel:
            if self.WorkMode == self.AllModes[2]:
                png_path = self.get_separate_label(img_path, 'png')
                if osp.exists(png_path):
                    seg_mask = cv2.imdecode(np.fromfile(png_path, dtype='uint8'), cv2.IMREAD_GRAYSCALE)
            elif self.WorkMode == self.AllModes[4]:
                json_path = self.get_separate_label(img_path, 'json')
                if osp.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        polygons, img_h, img_w = content['polygons'], content['img_height'], content['img_width']
                        seg_mask = get_seg_mask(classes, polygons, img_h, img_w, ins_seg=True)

        if seg_mask is not None:
            if self.WorkMode == self.AllModes[2]:
                png_img = seg_mask * int(255 / len(classes))
                height, width = png_img.shape
                return QImage(png_img.astype('uint8').data, width, height, width * 1, QImage.Format_Grayscale8)
            elif self.WorkMode == self.AllModes[4]:
                color = np.random.randint(20, 255, size=(100, 3), dtype='uint8')
                color[0, :] *= 0
                png_img = color[seg_mask]
                height, width, depth = png_img.shape
                return QImage(png_img.astype('uint8').data, width, height, width * 3, QImage.Format_RGB888)
        else:
            return None

    def get_root(self, root):
        version = self.current_version()
        if root == 'img':
            return f'{self.task_root}/{self.WorkMode}/{self.image_folder}'
        elif root == 'version':
            return f'{self.task_root}/{self.WorkMode}/{self.label_folder}/{version}'
        elif root == 'separate':
            return f'{self.task_root}/{self.WorkMode}/{self.label_folder}/{version}/' + self.tr('独立标注')
        elif root == 'tv':
            return f'{self.task_root}/{self.WorkMode}/{self.tv_folder}/{version}'
        elif root == 'ann':
            return f'{self.task_root}/{self.WorkMode}/{self.ann_folder}'

    def get_separate_label(self, img_path, suffix):
        img_pure_name = img_path.split('/')[-1][:-4]
        label_root = self.get_root('separate')
        return f'{label_root}/{img_pure_name}.{suffix}'

    def get_tv_num(self):
        if self.OneFileLabel:
            self.train_num, self.val_num = 0, 0
            for one in self.label_file_dict['labels'].values():
                if one['tv'] == 'train':
                    self.train_num += 1
                elif one['tv'] == 'val':
                    self.val_num += 1
        elif self.SeparateLabel:
            self.train_num = len(glob_imgs(f'{self.get_root("tv")}/imgs/train', self.WorkMode == self.AllModes[0]))
            self.val_num = len(glob_imgs(f'{self.get_root("tv")}/imgs/val', self.WorkMode == self.AllModes[0]))

    def go_next_img(self):  # 单分类模式或删除图片时触发
        self.marquee_move(right=True)

        if self.cur_i < self.img_num - 1:
            self.cur_i += 1
            self.show_img_status_info()
            self.show_label_to_ui()
            self.set_tv_label()
        else:
            self.show_label_to_ui()
            self.set_tv_label()
            self.marquees_layout.itemAt(self.cur_mar_i).widget().set_stat('done')
            self.cur_i += 1
            self.cur_mar_i += 1
            self.main_ui.label_path.setText(self.tr('已完成。'))
            QMB.information(self.main_ui, self.tr('已完成'), self.tr('已完成。'))

    def go_next_marquee_window(self):
        if self.window_marquee_label:
            qimg_png = self.get_qimg_png(self.imgs[self.cur_i])
            if qimg_png:
                self.window_marquee_label.paint_img(qimg_png)
        if self.window_marquee_img:
            self.window_marquee_img.paint_img(QPixmap(self.imgs[self.cur_i]))

    def has_img_root(self):
        if not self.task_root:
            QMB.information(self.main_ui, self.tr('图片根目录为空'), self.tr('请先加载图片。'))
            return False
        return True

    def has_looking_classes(self, img_path):
        if self.OneFileLabel:
            img_name = img_path.split('/')[-1]
            img_dict = self.label_file_dict['labels'].get(img_name)
            if img_dict:
                polygons = img_dict['polygons']
            else:
                return False
        elif self.SeparateLabel:
            json_path = self.get_separate_label(img_path, 'json')
            if osp.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    polygons = content['polygons']
            else:
                return False

        if polygons == ['bg']:
            polygons = []

        for one in polygons:
            if one['category'] in self.looking_classes:
                return True
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
        self.main_ui.pushButton_82.setChecked(False)
        self.main_ui.pushButton_83.setChecked(False)
        self.main_ui.pushButton_81.setText(' 0°')
        self.main_ui.pushButton_81.setChecked(False)
        self.main_ui.horizontalSlider.setValue(0)  # setValue 自动触发valueChanged信号
        self.main_ui.horizontalSlider_2.setValue(100)
        self.main_ui.horizontalSlider_3.setValue(100)

    def img_flip(self, h_flip=False, v_flip=False, do_paint=True):
        if len(self.imgs) and self.cv2_img_changed is not None:
            if h_flip:
                self.cv2_img_changed = cv2.flip(self.cv2_img_changed, 1)
            if v_flip:
                self.cv2_img_changed = cv2.flip(self.cv2_img_changed, 0)

            if do_paint:
                self.paint_changed_cv2_img()

    def img_jump(self, i=None):
        if i:
            index = i
        else:
            value = self.main_ui.spinBox_2.value()
            value = max(1, min(self.img_num, value))
            self.main_ui.spinBox_2.setValue(value)
            index = value - 1

        if index < self.cur_i:
            self.scan_img(last=True, count=self.cur_i - index, from_jump=True)

        elif index > self.cur_i:
            self.scan_img(next=True, count=index - self.cur_i, from_jump=True)

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

    def img_rotate(self, do_paint=True):
        if len(self.imgs) and self.cv2_img_changed is not None:
            old_degree = int(self.main_ui.pushButton_81.text().strip().removesuffix('°'))
            if do_paint:
                self.cv2_img_changed = cv2.rotate(self.cv2_img_changed, cv2.ROTATE_90_CLOCKWISE)
                new_degree = f' {(old_degree + 90) % 360}°'
                self.main_ui.pushButton_81.setText(new_degree)
                self.main_ui.pushButton_81.setChecked(new_degree != ' 0°')
                self.paint_changed_cv2_img()
            else:
                for i in range(old_degree // 90):
                    self.cv2_img_changed = cv2.rotate(self.cv2_img_changed, cv2.ROTATE_90_CLOCKWISE)

    def img_search(self):
        text = self.main_ui.lineEdit_search.text()
        for i, img in enumerate(self.imgs):
            if text in img:
                self.img_jump(i)
                self.main_ui.setFocus()
                return

        QMB.information(self.main_ui, self.tr('无搜索结果'), self.tr('未找到相关图片。'))
        self.main_ui.setFocus()

    def in_edit_mode(self):
        if self.task_root:
            if self.WorkMode == self.AllModes[0]:
                return True
            elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                if self.main_ui.radioButton_write.isChecked():
                    return True
        return False

    def init_button_group(self, buttons: QGroupBox, txt_path):  # 初始化类别按钮组
        buttons = buttons.layout()
        with open(txt_path, 'r', encoding='utf-8') as f:
            categories = [aa.split(',')[0] for aa in f.readlines()]

        for i in range(buttons.count()):
            item = buttons.itemAt(i)
            for j in range(item.count()):
                button = item.itemAt(j).widget()

                if categories:
                    cate = categories.pop(0)
                    button.setText(cate)
                else:
                    button.setText('-')

                clicked_signal = button.metaObject().method(37)  # 37为信号clicked的索引
                if not button.isSignalConnected(clicked_signal):  # 避免信号重复连接
                    button.clicked.connect(self.button_action)

    def load_classes(self):
        txt = self.file_select_dlg.getOpenFileName(self.main_ui, self.tr('选择txt'), filter='txt (*.txt)')[0]
        if txt:
            if self.WorkMode == self.AllModes[0]:
                self.reset_seg_widgets()
                self.init_button_group(self.main_ui.groupBox_1, txt)
            elif self.WorkMode == self.AllModes[1]:
                self.reset_seg_widgets()
                self.init_button_group(self.main_ui.groupBox_2, txt)
            elif self.WorkMode in self.AllModes[(2, 3, 4)]:
                self.main_ui.class_list.clear()
                self.window_select_class.clear()

                with open(txt, 'r', encoding='utf-8') as f:
                    classes = f.readlines()
                    classes = [aa.replace('，', ',').split(',')[0].strip() for aa in classes]

                for one in classes:
                    if one != '':
                        item, _ = self.main_ui.class_list.new_class_item(one)
                        self.window_select_class.add_item(item.clone())
                        self.main_ui.class_list.set_look(item)
                        self.main_ui.class_list.add_item(item)

        self.main_ui.setFocus()

    def load_one_file_dict(self):
        if not self.OneFileLabel:
            return True

        json_path = f'{self.get_root("version")}/labels.json'

        if osp.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.label_file_dict = json.load(f)
            except:
                QMB.critical(self.main_ui, self.tr('文件错误'), self.tr('"labels.json"读取失败，请检查文件！'))
                return

            record_imgs = sorted(list(self.label_file_dict['labels'].keys()))
            self_imgs = sorted([aa.split('/')[-1] for aa in self.imgs])

            miss_list = []
            for one in record_imgs:
                if one not in self_imgs:
                    miss_list.append(one)

            if len(miss_list) > 0:
                choice = QMB.question(self.main_ui, self.tr('图片列表不匹配'),
                                      self.tr('{}条标注记录未找到对应的"原图"，删除这些记录吗?').format(len(miss_list)))
                if choice == QMB.Yes:
                    for one in miss_list:
                        self.label_file_dict['labels'].pop(one)
        else:
            self.label_file_dict = {'task': self.task, 'work_mode': self.WorkMode, 'labels': {}}

        return True

    def load_pinned_images(self):  # todo --------------------
        json_path = f'{self.task_root}/{self.WorkMode}/pinned_images.json'
        if osp.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                content = json.load(f).get('images')
                if content:
                    self.pinned_imgs = content

    def lock_shape(self):
        cur_item = self.main_ui.shape_list.currentItem()
        if self.action_lock_shape.text() == self.tr('锁定标注'):
            item = self.main_ui.shape_list.has_locked_shape()
            if item:
                self.main_ui.shape_list.set_shape_unlocked(item)

            self.main_ui.shape_list.set_shape_locked(cur_item)
            self.main_ui.img_widget.set_shape_locked(True)
        else:
            self.main_ui.shape_list.set_shape_unlocked(cur_item)
            self.main_ui.img_widget.set_shape_locked(False)

        self.main_ui.setFocus()

    def log_info(self, text, mark_line=False):
        os.makedirs('log', exist_ok=True)
        if mark_line:
            mark_num = 60
        else:
            mark_num = 0

        with open(f'log/log_{self.log_created_time}.txt', 'a+', encoding='utf-8') as f:
            f.writelines('\n' + f'{get_datetime()} ' + '-' * mark_num + '\n')
            f.writelines(f'{text}\n')

    def log_sys_error(self, text):
        self.save_one_file_json(check_version=False)

        text = text.strip()
        if text:
            if len(self.sys_error_text) == 0:
                self.sys_error_text.append('\n' + f'{get_datetime()} ' + '-' * 50 + '\n')

            self.sys_error_text.append(text)

            if self.sys_error_text[-2].startswith(':'):
                show_info = ''.join(self.sys_error_text) + '\n'
                QMB.warning(self.main_ui, self.tr('系统错误'),
                            self.tr('<font color=red>{}</font><br>请反馈给开发者。').format(show_info))
                with open(f'log/log_{self.log_created_time}.txt', 'a+', encoding='utf-8') as f:
                    f.writelines(show_info)

                self.sys_error_text = []

    def look_or_not_look(self, double=False):
        self.main_ui.class_list.set_looking(double)
        self.main_ui.setFocus()

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
        # 单分类模式已完成后会出现获取不到marquee的情况
        cur_marquee = self.marquees_layout.itemAt(self.cur_mar_i).widget()
        if cur_marquee is not None:
            if '图片已删除' in self.imgs[self.cur_i] or self.EditImgMode:
                cur_marquee.set_stat('undo')
            else:
                stat = self.marquee_stat(self.imgs[self.cur_i])
                cur_marquee.set_stat(stat)

        if left:
            if self.cur_mar_i > 0:
                self.cur_mar_i -= 1
                self.marquees_layout.itemAt(self.cur_mar_i).widget().set_stat('doing')
            else:
                if self.cur_i > 0:
                    self.marquee_insert(first=True, last=False)
        elif right:
            if self.cur_mar_i < self.marquees_layout.count() - 2:
                self.cur_mar_i += 1
                self.marquees_layout.itemAt(self.cur_mar_i).widget().set_stat('doing')
            else:
                if self.cur_i < self.img_num - 1:
                    if self.marquees_layout.count() - 1 < self.marquee_num:
                        self.marquee_add()
                    else:
                        self.marquee_insert(last=True)

        self.main_ui.scrollArea.horizontalScrollBar().setValue(self.marquee_size * self.cur_mar_i)

    def marquee_show(self, info):
        img_path, show_png = info

        if self.WorkMode in self.AllModes[(2, 3, 4)]:
            if show_png:
                if self.WorkMode in self.AllModes[(2, 4)]:
                    classes = AllClasses.classes()
                    if len(classes) == 0:
                        QMB.warning(self.main_ui, self.tr('类别数量为0'), self.tr('当前类别数量为0，请先加载类别。'))
                        return

                    qimg_png = self.get_qimg_png(img_path)
                    if qimg_png:
                        self.window_marquee_label = BaseImgFrame(title=self.tr('标注图片'))
                        self.window_marquee_label.setWindowFlags(Qt.WindowStaysOnTopHint)
                        self.window_marquee_label.paint_img(qimg_png)
                        self.window_marquee_label.show()
            else:
                self.window_marquee_img = BaseImgFrame(title=self.tr('原始图片'))
                self.window_marquee_img.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.window_marquee_img.paint_img(QPixmap(img_path))
                self.window_marquee_img.show()

    def marquee_stat(self, path):  # 获取某个marquee的处理状态
        stat = 'undo'
        if self.WorkMode in self.AllModes[(0, 1)]:
            stat = 'done' if self.cls_has_classified() else 'undo'
        elif self.WorkMode in self.AllModes[(2, 3, 4)]:
            if self.OneFileLabel:
                img_name = path.split('/')[-1]
                if self.label_file_dict['labels'].get(img_name):
                    if self.label_file_dict['labels'][img_name]['polygons']:
                        stat = 'done'
            elif self.SeparateLabel:
                json_path = self.get_separate_label(path, 'json')
                if osp.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    stat = 'done' if content['polygons'] else 'undo'
        return stat

    def move_to_new_folder(self):
        path = self.file_select_dlg.getExistingDirectory(self.main_ui, self.tr('选择文件夹'))
        if path:
            self.del_img(path)

    def m_cls_to_button(self):  # 若已存在txt标注，直接显示在按钮上
        self.buttons_clear()

        lines = []
        img_name = self.current_img_name()
        if self.OneFileLabel:
            if self.label_file_dict['labels'].get(img_name):
                lines = self.label_file_dict['labels'][img_name]['class']
        elif self.SeparateLabel:
            txt_name = img_name[:-3] + 'txt'
            txt_path = f'{self.get_root("separate")}/{txt_name}'

            if os.path.isfile(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                lines = [aa.strip() for aa in lines]

        lines_copy = lines.copy()
        button_layout = self.main_ui.groupBox_2.layout()
        for one in lines:
            for i in range(button_layout.count()):
                item = button_layout.itemAt(i)
                for j in range(item.count()):
                    button = item.itemAt(j).widget()
                    if button.text() == one:
                        button.setStyleSheet('QPushButton { background-color: lightgreen }')
                        lines_copy.remove(one)

        if len(lines_copy):
            for category in lines_copy:
                Going = True
                for i in range(button_layout.count()):
                    item = button_layout.itemAt(i)
                    for j in range(item.count()):
                        button = item.itemAt(j).widget()
                        if Going and button.text() == '-':
                            button.setText(category)
                            button.setStyleSheet('QPushButton { background-color: lightgreen }')
                            Going = False

    def modify_shape_list_start(self):
        if self.main_ui.checkBox_shape_edit.isChecked():
            self.LabelUiCallByMo = True
            self.show_class_selection_list()

    def modify_shape_list_end(self, text):
        i = self.main_ui.shape_list.currentRow()
        item = self.main_ui.class_list.findItems(text, Qt.MatchExactly)
        if len(item):
            name = item[0].text()
            color = item[0].foreground().color()
        else:
            name = text
            item, color = self.main_ui.class_list.new_class_item(name)
            color = QColor(color)
            self.window_select_class.add_item(item.clone())
            self.main_ui.class_list.set_look(item)
            self.main_ui.class_list.add_item(item)
            self.sem_class_modified_tip()

        self.main_ui.img_widget.modify_polygon_class(i, name, color.name())
        old_item = self.main_ui.shape_list.currentItem()
        old_class = old_item.text()
        old_item.setText(name)
        old_item.setForeground(color)

        row = self.main_ui.shape_list.currentRow()
        lw = self.current_shape_info_widget()
        if lw is not None and lw.count():
            info_item = lw.item(row)
            new_text = info_item.text().replace(old_class, name)
            info_item.setText(new_text)
            info_item.setForeground(color)

        self.window_select_class.close()
        self.main_ui.setFocus()

    def oc_shape_info(self):
        if self.action_oc_shape_info.text() == self.tr('禁用（提高切图速度）'):
            self.clear_shape_info()
            self.action_oc_shape_info.setText(self.tr('启用（降低切图速度）'))
        elif self.action_oc_shape_info.text() == self.tr('启用（降低切图速度）'):
            self.action_oc_shape_info.setText(self.tr('禁用（提高切图速度）'))
        self.main_ui.setFocus()

    def open_task(self, new_task=''):
        if new_task:
            file_path, version, des_text = new_task
            self.main_ui.lineEdit_version.setText(version)
            version_path = f'{file_path}/{self.WorkMode}/{self.label_folder}/{version}'
            os.makedirs(version_path, exist_ok=True)
            with open(f'{version_path}/description.txt', 'w', encoding='utf-8') as f:
                f.writelines(des_text)
        else:
            file_path = self.file_select_dlg.getExistingDirectory(self.main_ui, self.tr('选择任务'))
            if file_path:
                imgs_path = f'{file_path}/{self.WorkMode}/{self.image_folder}'
                if not osp.exists(imgs_path):
                    QMB.warning(self, self.tr('未找到"原图"'),
                                self.tr('未找到"{}"文件夹，请新建任务。').format(imgs_path))
                    return
                else:
                    self.window_choose_version.get_versions(f'{file_path}/{self.WorkMode}/{self.label_folder}')
                    version = self.window_choose_version.exec()
                    if version:
                        self.main_ui.lineEdit_version.setText(version)
                    else:
                        return

        if os.path.isdir(file_path):
            if self.main_ui.lineEdit.text():
                self.save_backup_classes()
                self.save_one_file_json()

            self.reset_init_variables()
            self.set_buttons_checked()
            self.clear_shape_info()
            self.reset_seg_widgets()

            if self.prepare_self_imgs(file_path):
                self.task_root = file_path
                self.main_ui.lineEdit.setText(self.task_root)
                self.task = self.task_root.split('/')[-1]
                self.after_get_self_imgs()
                self.set_action_disabled()
                self.load_pinned_images()
                self.img_enhance_reset()
                if self.load_one_file_dict():
                    self.show_label_to_ui()
                    self.set_tv_label()
                    self.get_tv_num()
                    self.set_tv_bar()

            if self.WorkMode == self.AllModes[0] and self.OneFileLabel:
                self.thread_auto_save.start()

            self.log_info(f'task: {self.task}, work mode: {self.WorkMode}, '
                          f'one file: {self.OneFileLabel}, separate file: {self.SeparateLabel}')

    def paint_changed_cv2_img(self):
        height, width, depth = self.cv2_img_changed.shape
        qimg = QImage(self.cv2_img_changed.astype('uint8').data, width, height, width * depth, QImage.Format_RGB888)
        self.main_ui.img_widget.paint_img(qimg, re_center=False)

    def paint_ann_img(self):
        if self.task_root:
            img_name = self.current_img_name()
            ann_jpg = f'{self.get_root("ann")}/{img_name[:-4]}.jpg'
            if osp.exists(ann_jpg):
                self.main_ui.img_widget.set_ann_painted_img(ann_jpg)

    def pin_unpin_image(self):
        if self.task_root:
            img_name = self.current_img_name()
            if img_name in self.pinned_imgs:
                self.pinned_imgs.remove(img_name)
                self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_black.png'))
            else:
                self.pinned_imgs.append(img_name)
                self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_green.png'))

            json_dict = {'images': self.pinned_imgs}
            with open(f'{self.task_root}/{self.WorkMode}/pinned_images.json', 'w', encoding='utf-8') as f:
                json.dump(json_dict, f, sort_keys=False, ensure_ascii=False, indent=4)

    def polygons_to_img(self):
        self.main_ui.img_widget.clear_all_polygons()
        self.main_ui.shape_list.clear()

        img_path = self.imgs[self.cur_i]
        if '图片已删除' in img_path:
            return

        if self.OneFileLabel:
            img_name = img_path.split('/')[-1]
            img_dict = self.label_file_dict['labels'].get(img_name)
            if img_dict:
                polygons, img_h, img_w = img_dict['polygons'], img_dict['img_height'], img_dict['img_width']
                if polygons == ['bg']:
                    polygons = []
            else:
                return
        elif self.SeparateLabel:
            json_path = self.get_separate_label(img_path, 'json')
            if osp.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    polygons, img_h, img_w = content['polygons'], content['img_height'], content['img_width']
                    if polygons == ['bg']:
                        polygons = []
            else:
                return

        for one in polygons:
            cate = one['category']
            if cate in AllClasses.classes():
                item = self.main_ui.class_list.findItems(cate, Qt.MatchExactly)[0]
                one['qcolor'] = item.foreground().color().name()

            item, _ = self.main_ui.class_list.new_class_item(cate, color=one['qcolor'])
            self.main_ui.shape_list.add_item(item.clone())
            self.show_shape_info(one)

            if cate not in AllClasses.classes():
                self.window_select_class.add_item(item.clone())
                self.main_ui.class_list.set_look(item)
                self.main_ui.class_list.add_item(item)
                self.sem_class_modified_tip()

        # polygons的嵌套的数据结构导致数据容易发生原位修改，哪怕使用了.get()方法和函数传参也一样，具体原理未知
        self.main_ui.img_widget.prepare_polygons(deepcopy(polygons), img_h, img_w)

    def prepare_self_imgs(self, root_path):
        path = f'{root_path}/{self.WorkMode}/{self.image_folder}'
        if not os.path.isdir(path):
            QMB.warning(self.main_ui, self.tr('未找到文件夹'), self.tr('未找到 "{}" 文件夹。').format(path))
            return False

        self.imgs = glob_imgs(path)

        if self.WorkMode == self.AllModes[0]:
            version = self.current_version()
            cls_label_folders = f'{root_path}/{self.WorkMode}/{self.label_folder}/{version}/' + self.tr('独立标注')
            folder_imgs = glob_imgs(cls_label_folders, recursive=True)

            names = [aa.split('/')[-1] for aa in folder_imgs]
            for one in self.imgs:  # 剔除掉可能存在的重复的图片
                if one.split('/')[-1] not in names:
                    folder_imgs.append(one)

            self.imgs = folder_imgs

        return True

    def raise_label_mode_conflict(self):
        if self.task_root:
            # 加了QMB后，可以阻止点击QcheckBox时切换状态，原因未知
            QMB.critical(self.main_ui, self.tr('错误操作'),
                         self.tr('请误在标注途中切换标注模式，否则容易造成标注文件混乱！'))

    def random_train_val(self):
        if not self.has_img_root():
            return
        if not self.in_edit_mode():
            QMB.warning(self.main_ui, self.tr('模式错误'), self.tr('请先切换至编辑模式!'))
            return

        content, is_ok = self.input_dlg.getText(self.main_ui, self.tr('划分比例'),
                                                self.tr('请输入训练集和验证集的划分比例'),
                                                QLineEdit.Normal, text='7:1')
        if not is_ok:
            return
        content = content.replace('：', ':')
        content = [aa.strip() for aa in content.split(':')]
        if len(content) != 2:
            QMB.critical(self.main_ui, self.tr('格式错误'), self.tr('请输入正确的划分比例！'))
            return

        if self.SeparateLabel:
            choice = QMB.question(self.main_ui, self.tr('独立标注模式'),
                                  self.tr('"{0}"下的"imgs"和"labels"文件夹将被覆盖，继续吗？').format(
                                      self.get_root('tv')))
            if choice == QMB.Yes:
                if not self.OneFileLabel:
                    self.train_num, self.val_num = 0, 0

                tv_img_path, tv_label_path = f'{self.get_root("tv")}/imgs', f'{self.get_root("tv")}/labels'
                if osp.exists(tv_img_path):
                    shutil.rmtree(tv_img_path)
                if self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                    if osp.exists(tv_label_path):
                        shutil.rmtree(tv_label_path)

        shuffled_imgs = self.imgs.copy()
        shuffled_imgs = [one for one in shuffled_imgs if self.has_labeled(one)]
        random.shuffle(shuffled_imgs)
        img_num = len(shuffled_imgs)

        t_r, v_r = content
        t_r, v_r = int(t_r), int(v_r)
        t_num = int((t_r / (t_r + v_r)) * img_num)
        v_num = img_num - t_num

        for i in range(img_num):
            if i < t_num:
                self.add_to_train_val('train', shuffled_imgs[i])
            else:
                self.add_to_train_val('val', shuffled_imgs[i])

        QMB.information(self.main_ui, self.tr('已完成'),
                        self.tr('共划分{}张图片至训练集，{}张图片至验证集。').format(t_num, v_num))

    def remove_empty_cls_folder(self):
        if not self.WorkMode == self.AllModes[0]:
            return

        folders = glob.glob(f'{self.get_root("img")}/*')
        folders = [one for one in folders if osp.isdir(one)]

        for one in folders:
            if len(glob.glob(f'{one}/*')) == 0:
                shutil.rmtree(one)

        t_img_path = f'{self.get_root("tv")}/imgs/train'
        v_img_path = f'{self.get_root("tv")}/imgs/val'

        if osp.exists(t_img_path):
            for one in glob.glob(f'{t_img_path}/*'):
                if len(glob.glob(f'{one}/*')) == 0:
                    shutil.rmtree(one)
        if osp.exists(v_img_path):
            for one in glob.glob(f'{v_img_path}/*'):
                if len(glob.glob(f'{one}/*')) == 0:
                    shutil.rmtree(one)

    def remove_redu_files(self, files: list, title: str, text: str):
        choice = QMB.question(self.main_ui, title, text)
        if choice == QMB.Yes:
            for one in files:
                file_remove(one)

            QMB.information(self.main_ui, '清理完成', f'清理完成，共清理{len(files)}个文件。')
            return True
        return False

    def reset_init_variables(self):
        self.task_root = ''  # 图片根目录
        self.task = ''
        self.imgs = []
        self.pinned_imgs = []  # 收藏的图片
        self.label_file_dict = {}
        self.img_num = 0
        self.train_num, self.val_num = 0, 0
        self.cur_i = 0
        self.cur_mar_i = -1  # 当前小图的索引，最小有效值为0
        self.mcls_default_c = ''  # 多分类的默认类别
        self.cv2_img = None
        self.cv2_img_changed = None
        self.cls_op_track = []
        self.bottom_img_text = ''
        self.LookingAll = True
        self.looking_classes = []
        self.sys_error_text = []
        self.log_created_time = get_datetime().split(' ')[0]
        self.window_auto_infer_progress = None
        self.window_class_stat = None
        self.window_compare = None
        self.window_marquee_img = None
        self.window_marquee_label = None
        self.window_usp_progress = None

    def reset_seg_widgets(self):  # 清除控件上的所有标注图形，清空标注列表、类别字典
        self.main_ui.img_widget.clear_all_polygons()
        self.main_ui.class_list.clear()
        self.main_ui.shape_list.clear()
        self.window_select_class.clear()
        self.main_ui.img_widget.collection_window.ui.listWidget.clear()
        self.main_ui.img_widget.set_shape_locked(False)

    def save_ann_img(self):
        folder = f'{self.get_root("ann")}'
        os.makedirs(folder, exist_ok=True)
        img = self.main_ui.img_widget.get_ann_img()
        img_array = qimage_to_array(img)
        img_name = self.current_img_name()[:-4]
        save_path = f'{folder}/{img_name}.jpg'
        cv2.imencode('.jpg', img_array.astype('uint8'))[1].tofile(save_path)
        self.window_ann_saved.show(self.tr('图片保存于：{}。').format(save_path))

    def save_backup_classes(self):
        lines = ''
        classes = AllClasses.classes()

        if self.in_edit_mode() and len(classes):
            txt_path = self.get_root("version")
            os.makedirs(txt_path, exist_ok=True)

            for one_c in classes:
                lines += f'{one_c},\n'

            with open(f'{txt_path}/classes_backup.txt', 'w', encoding='utf-8') as f:
                f.writelines(lines)

    def save_det_seg(self):
        img_path = self.imgs[self.cur_i]
        if img_path == 'images/图片已删除.png':
            return

        img_w, img_h = QPixmap(img_path).size().toTuple()
        img_name = img_path.split('/')[-1]
        tv = self.current_tv()

        json_polygons = self.main_ui.img_widget.get_tuple_polygons()

        if self.WorkMode == self.AllModes[2] and self.main_ui.pushButton_bg.objectName() == 'bg':
            assert not json_polygons, 'json_polygons should be empty when label is bg!'
            json_polygons = ['bg']

        one_label = {'img_height': img_h, 'img_width': img_w, 'tv': tv, 'polygons': json_polygons}

        if self.OneFileLabel:
            if json_polygons:
                self.label_file_dict['labels'][img_name] = one_label
            else:
                if self.label_file_dict['labels'].get(img_name):
                    self.label_file_dict['labels'].pop(img_name)

        if self.SeparateLabel:
            label_path = f'{self.get_root("separate")}'
            os.makedirs(label_path, exist_ok=True)

            json_name = f'{img_name[:-4]}.json'
            png_name = f'{img_name[:-4]}.png'
            txt_name = f'{img_name[:-4]}.txt'
            json_path = f'{label_path}/{json_name}'
            png_path = f'{label_path}/{png_name}'
            txt_path = f'{label_path}/{txt_name}'
            tv_img = f'{self.get_root("tv")}/imgs/{tv}/{img_name}'
            tv_json = f'{self.get_root("tv")}/labels/{tv}/{json_name}'
            tv_png = f'{self.get_root("tv")}/labels/{tv}/{png_name}'
            tv_txt = f'{self.get_root("tv")}/labels/{tv}/{txt_name}'

            if json_polygons:
                if not self.version_remind():
                    return

                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(one_label, f, sort_keys=False, ensure_ascii=False, indent=4)
                if osp.exists(tv_json):
                    with open(tv_json, 'w', encoding='utf-8') as f:
                        json.dump(one_label, f, sort_keys=False, ensure_ascii=False, indent=4)

                if self.WorkMode == self.AllModes[2]:
                    if json_polygons == ['bg']:
                        json_polygons = []

                    seg_class_names = AllClasses.classes()
                    seg_mask = get_seg_mask(seg_class_names, json_polygons, img_h, img_w)
                    if seg_mask is not None:
                        cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(png_path)
                        if osp.exists(tv_png):
                            cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(tv_png)

                if self.WorkMode == self.AllModes[3]:
                    with open(txt_path, 'w') as f:
                        for one in json_polygons:
                            c_name = one['category']
                            [x1, y1], [x2, y2] = one['img_points']
                            f.writelines(f'{c_name} {x1} {y1} {x2} {y2}\n')
                    if osp.exists(tv_txt):
                        with open(tv_txt, 'w') as f:
                            for one in json_polygons:
                                c_name = one['category']
                                [x1, y1], [x2, y2] = one['img_points']
                                f.writelines(f'{c_name} {x1} {y1} {x2} {y2}\n')
            else:  # 若标注为空，则在训练集&验证集里剔除
                if osp.exists(tv_img):
                    if tv == 'train':
                        self.train_num -= 1
                    elif tv == 'val':
                        self.val_num -= 1
                    self.set_tv_bar()

                file_remove([tv_img, json_path, tv_json, png_path, tv_png, txt_path, tv_txt])

    def save_edited_img(self, save_all=False):
        if self.main_ui.radioButton_14.isChecked():
            suffix = '.jpg'
        elif self.main_ui.radioButton_15.isChecked():
            suffix = '.png'
        elif self.main_ui.radioButton_16.isChecked():
            suffix = '.bmp'

        if save_all:
            imgs_path = [aa for aa in self.imgs if aa != 'images/图片已删除.png']
            re = QMB.question(self.main_ui, self.tr('覆盖图片'),
                              self.tr('"{}"下的同名图片将被覆盖，继续吗？').format(self.task_root))
            if re != QMB.Yes:
                return
        else:
            if self.imgs[self.cur_i][-4:] == suffix:
                re = QMB.question(self.main_ui, self.tr('覆盖图片'),
                                  self.tr('"{}"将被覆盖，继续吗？').format(self.imgs[self.cur_i]))
                if re != QMB.Yes:
                    return

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

            if self.main_ui.checkBox_scale.isChecked():
                resize_w, resize_h = self.main_ui.spinBox_13.value(), self.main_ui.spinBox_14.value()
                if ori_w != resize_w or ori_h != resize_h:
                    if self.main_ui.radioButton_12.isChecked():
                        scale_alg = cv2.INTER_NEAREST
                    elif self.main_ui.radioButton_13.isChecked():
                        scale_alg = cv2.INTER_LINEAR
                    cv2_img = cv2.resize(cv2_img, (resize_w, resize_h), scale_alg)

            cv2.imencode(suffix, cv2_img.astype('uint8'))[1].tofile(one[:-4] + suffix)

        QMB.information(self.main_ui, self.tr('保存完成'), self.tr('保存完成，共{}张图片。').format(len(imgs_path)))

    def save_m_cls(self):
        img_name = self.current_img_name()
        if '图片已删除' in img_name:
            return

        lines = []
        tv = self.current_tv()
        button_layout = self.main_ui.groupBox_2.layout()
        for i in range(button_layout.count()):
            item = button_layout.itemAt(i)
            for j in range(item.count()):
                button = item.itemAt(j).widget()
                if button.palette().button().color().name() == '#90ee90':
                    cls = button.text()
                    lines.append(f'{cls}\n')

        if not lines and self.mcls_default_c != '':
            default_c = self.mcls_default_c.replace('，', ',')
            default_c = [one.strip() for one in default_c.split(',')]
            default_c = [f'{one}\n' for one in default_c]
            lines += default_c

        if self.OneFileLabel:
            if lines:
                labels = [aa.strip() for aa in lines]
                img_w, img_h = QPixmap(self.imgs[self.cur_i]).size().toTuple()
                one_label = {'img_height': img_h, 'img_width': img_w, 'tv': tv, 'class': labels}
                self.label_file_dict['labels'][img_name] = one_label
            else:
                if self.label_file_dict['labels'].get(img_name):
                    self.label_file_dict['labels'].pop(img_name)

        if self.SeparateLabel:
            label_path = f'{self.get_root("separate")}'
            os.makedirs(label_path, exist_ok=True)
            txt_name = img_name[:-3] + 'txt'
            txt_path = f'{label_path}/{txt_name}'
            tv_img = f'{self.get_root("tv")}/imgs/{tv}/{img_name}'
            tv_txt = f'{self.get_root("tv")}/labels/{tv}/{txt_name}'

            if lines:
                if not self.version_remind():
                    return

                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

                if osp.exists(tv_txt):
                    with open(tv_txt, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
            else:
                if osp.exists(tv_img):  # 若标注为空，则在训练集&验证集里剔除
                    if tv == 'train':
                        self.train_num -= 1
                    elif tv == 'val':
                        self.val_num -= 1
                    self.set_tv_bar()

                file_remove([tv_img, txt_path, tv_txt])

    def save_one_file_json(self, check_version=True):
        if self.in_edit_mode() and self.OneFileLabel and self.label_file_dict:
            if check_version:
                if not self.version_remind():
                    return

            dir_path = self.get_root("version")
            os.makedirs(dir_path, exist_ok=True)
            json_path = f'{dir_path}/labels.json'

            ori_dict = {}
            if osp.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    ori_dict = json.load(f)

            if ori_dict != self.label_file_dict:
                self.label_file_dict['classes'] = AllClasses.classes()
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(self.label_file_dict, f, sort_keys=False, ensure_ascii=False, indent=4)

                self.main_ui.label_path.setText(self.tr('"{}"已保存。').format(json_path))
                self.log_info('"labels.json" has been saved.')

    def save_one_shape(self, text):
        if self.LabelUiCallByMo:
            self.modify_shape_list_end(text)
            self.LabelUiCallByMo = False
        else:
            if self.in_edit_mode() and text:
                if text not in AllClasses.classes() and text != '':
                    item, color = self.main_ui.class_list.new_class_item(text)
                    self.window_select_class.add_item(item.clone())
                    self.main_ui.shape_list.add_item(item.clone())

                    self.main_ui.class_list.set_look(item)
                    self.main_ui.class_list.add_item(item)
                    self.sem_class_modified_tip()
                else:
                    item = self.main_ui.class_list.findItems(f'{text}', Qt.MatchExactly)[0].clone()
                    item_2 = item.clone()
                    item_2.setIcon(QIcon())
                    self.main_ui.shape_list.add_item(item_2)
                    color = item.foreground().color().name()

                self.main_ui.img_widget.one_polygon_done(color, text)
                self.show_shape_info(self.main_ui.img_widget.get_one_polygon(-1))

            self.window_select_class.close()

    def scan_img(self, last=False, next=False, count=1, from_jump=False):
        scan_start = time.time()

        if not self.task_root:
            return
        if self.cur_i < 0 or self.cur_i > self.img_num:
            QMB.critical(self.main_ui, self.tr('索引超限'), self.tr('当前图片索引为{}，超出限制！').format(self.cur_i))
            return

        if not self.EditImgMode:
            if not from_jump:
                part_scan = self.main_ui.comboBox.currentText()
                # 只看部分类别功能
                if self.WorkMode in self.AllModes[(2, 3, 4)]:
                    self.LookingAll = self.main_ui.class_list.looking_all()
                    self.looking_classes = self.main_ui.class_list.looking_classes()
                    if not self.LookingAll:
                        if part_scan == self.tr('浏览未标注'):
                            QMB.critical(self.main_ui, self.tr('功能冲突'),
                                         self.tr('浏览部分类别的功能和浏览未标注的功能冲突，请先关闭其中一项。'))
                            return

                        count = self.scan_part_classes(last=last, next=next)

                # 只看带标签图片功能  todo-------------------------
                if part_scan == self.tr('按标签浏览'):
                    count = self.scan_pinned_imgs(last=last, next=next)

                if part_scan == self.tr('浏览未标注'):
                    count = self.scan_unlabeled_imgs(last=last, next=next)

                if part_scan == self.tr('浏览未划分'):
                    count = self.scan_train_val_imgs(split='none', last=last, next=next)

                if part_scan == self.tr('浏览训练集'):
                    count = self.scan_train_val_imgs(split='train', last=last, next=next)

                if part_scan == self.tr('浏览验证集'):
                    count = self.scan_train_val_imgs(split='val', last=last, next=next)

            if self.in_edit_mode():
                if self.WorkMode == self.AllModes[1]:
                    self.save_m_cls()
                elif self.WorkMode in self.AllModes[(2, 3, 4)]:
                    self.save_det_seg()

        if last and 0 < self.cur_i <= self.img_num:
            for _ in range(count):
                self.marquee_move(left=True)
                self.cur_i -= 1

        elif next and self.cur_i < self.img_num - 1:
            for _ in range(count):
                self.marquee_move(right=True)
                self.cur_i += 1

        if 0 <= self.cur_i < self.img_num:
            self.main_ui.img_widget.set_shape_locked(False)
            self.show_img_status_info()
            self.show_label_to_ui()
            self.set_tv_label()
            if self.WorkMode in self.AllModes[(2, 4)]:
                self.go_next_marquee_window()
            if self.WorkMode == self.AllModes[2]:
                self.set_semantic_bg_when_scan()

            scan_time = (time.time() - scan_start) * 1000
            if scan_time < self.scan_delay:
                time.sleep((self.scan_delay - scan_time) / 1000)

    def scan_unlabeled_imgs(self, last=False, next=False):
        result = True
        i = self.cur_i
        while 0 <= i <= self.img_num - 1:
            if last:
                i -= 1
            elif next:
                i += 1

            if i == -1 or i == self.img_num:
                break

            if '图片已删除' in self.imgs[i]:
                continue

            if self.WorkMode in self.AllModes[(0, 1)]:
                result = self.cls_has_classified(self.imgs[i])
            elif self.WorkMode in self.AllModes[(2, 3, 4)]:
                if self.OneFileLabel:
                    result = self.label_file_dict['labels'].get(self.imgs[i].split('/')[-1])
                elif self.SeparateLabel:
                    json_path = self.get_separate_label(self.imgs[i], 'json')
                    result = osp.exists(json_path)

            if not result:
                break

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.cur_i)
        return count

    def scan_part_classes(self, last=False, next=False):  # 只浏览部分类别的标注的功能
        i = self.cur_i
        while 0 <= i <= self.img_num - 1:
            if last:
                i -= 1
            elif next:
                i += 1

            if i == -1 or i == self.img_num:
                break

            if self.has_looking_classes(self.imgs[i]):
                count = abs(i - self.cur_i)
                return count

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.cur_i)
        return count

    def scan_pinned_imgs(self, last=False, next=False):
        i = self.cur_i
        while 0 <= i <= self.img_num - 1:
            if last:
                i -= 1
            elif next:
                i += 1

            if i == -1 or i == self.img_num:
                break

            img_name = self.imgs[i].split('/')[-1]
            if img_name in self.pinned_imgs:
                count = abs(i - self.cur_i)
                return count

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.cur_i)
        return count

    def scan_train_val_imgs(self, split, last=False, next=False):
        i = self.cur_i
        while 0 <= i <= self.img_num - 1:
            if last:
                i -= 1
            elif next:
                i += 1

            if i == -1 or i == self.img_num:
                break

            tv = self.get_img_tv(self.imgs[i])

            if tv == split:
                if not self.LookingAll:
                    if self.has_looking_classes(self.imgs[i]):
                        count = abs(i - self.cur_i)
                        return count
                else:
                    count = abs(i - self.cur_i)
                    return count

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.cur_i)
        return count

    def sem_class_modified_tip(self):
        if self.WorkMode == self.AllModes[2] and self.SeparateLabel \
                and self.main_ui.radioButton_write.isChecked():
            if not self.window_sem_class_changed.DontShowAgain:
                self.window_sem_class_changed.show(self.tr('类别列表发生变化，以往的png标注可能需要更新。'))

    def set_action_disabled(self):
        self.action_load_cls_classes.setDisabled(self.task_root == '')
        self.action_export_cls_classes.setDisabled(self.task_root == '')
        self.action_load_seg_class.setDisabled(self.task_root == '')
        self.action_export_seg_class.setDisabled(self.task_root == '')

        stat = not self.main_ui.checkBox_shape_edit.isChecked()
        self.action_modify_one_class_jsons.setDisabled(stat)
        self.action_del_one_class_jsons.setDisabled(stat)
        self.action_modify_one_shape_class.setDisabled(stat)
        self.action_delete_one_shape.setDisabled(stat)
        self.action_delete_all.setDisabled(stat)
        self.action_lock_shape.setDisabled(stat)

    def set_buttons_checked(self):  # open_task和set_work_mode共同的按钮的setChecked操作在这设置
        self.main_ui.radioButton_read.setChecked(True)

    def set_hide_cross(self):
        self.main_ui.img_widget.set_hide_cross(self.main_ui.checkBox_hide_cross.isChecked())

    def set_img_edit_scale(self):
        enabled = self.main_ui.checkBox_scale.isChecked()
        self.main_ui.spinBox_13.setDisabled(not enabled)
        self.main_ui.spinBox_14.setDisabled(not enabled)
        self.main_ui.label_46.setDisabled(not enabled)
        self.main_ui.label_44.setDisabled(not enabled)
        self.main_ui.radioButton_12.setDisabled(not enabled)
        self.main_ui.radioButton_13.setDisabled(not enabled)

    def set_info_widget_selected(self):
        lw = self.current_shape_info_widget()
        if lw is not None and lw.count():
            row = self.main_ui.shape_list.currentRow()
            if lw.item(row):
                lw.item(row).setSelected(True)

    def set_language(self, language):
        # 不重启也可以实时翻译，但是这个问题无法解决，QAction需要在changeEvent里逐个添加翻译代码
        # https://forum.qt.io/topic/141742/how-to-translate-text-with-quiloader

        app = QApplication.instance()
        if language == 'CN' and self.language == 'EN':
            choice = QMB.question(self.main_ui, 'Switch to Chinese',
                                  'The app is going to restart, please ensure all work is saved, continue?')
            if choice == QMB.Yes:
                self.language = 'CN'
                app.exit(99)
        elif language == 'EN' and self.language == 'CN':
            choice = QMB.question(self.main_ui, '切换为英文', '软件将重新打开，请确保所有工作已保存，继续吗？')
            if choice == QMB.Yes:
                self.language = 'EN'
                app.exit(99)

    def set_m_cls_default_c(self):
        text, is_ok = QInputDialog().getText(self, self.tr('默认类别'), self.tr('请输入类别名称'),
                                             QLineEdit.Normal, text=self.mcls_default_c)
        if is_ok:
            self.mcls_default_c = text

    def set_one_file_label(self):
        self.OneFileLabel = self.main_ui.checkBox_one_label.isChecked()
        self.main_ui.pushButton_cls_back.setDisabled(self.OneFileLabel)
        if not self.SeparateLabel and not self.OneFileLabel:
            QMB.warning(self.main_ui, self.tr('未选择标注模式'), self.tr('请选择至少一种标注文件模式！'))
            self.main_ui.checkBox_one_label.setChecked(True)

    def set_read_mode(self):
        if self.OneFileLabel:
            if self.WorkMode == self.AllModes[0]:
                self.thread_auto_save.start()
            elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                if self.main_ui.radioButton_read.isChecked():
                    self.thread_auto_save.terminate()
                else:
                    self.thread_auto_save.start()
        else:
            self.thread_auto_save.terminate()

        if self.WorkMode in self.AllModes[(2, 3, 4)]:
            if self.main_ui.radioButton_read.isChecked():
                self.main_ui.checkBox_shape_edit.setChecked(False)
                self.main_ui.pushButton_bg.setDisabled(True)

            self.main_ui.checkBox_shape_edit.setDisabled(self.main_ui.radioButton_read.isChecked())

    def set_scan_delay(self):
        delay, is_ok = self.input_dlg.getInt(self.main_ui, self.tr('切图延时'), self.tr('单位：ms'), 0, 0, 9999, 100)
        if is_ok:
            self.scan_delay = delay

    def set_scan_mode(self):
        self.main_ui.setFocus()

    def set_seg_lists(self):
        self.main_ui.class_list.set_name('class')
        self.main_ui.shape_list.set_name('shape')
        self.main_ui.shape_list.setVisible(False)
        self.main_ui.tag_list.setVisible(False)

        for button in [self.main_ui.pushButton_shape_list, self.main_ui.pushButton_tag_list]:
            sh = button.styleSheet()
            sh1, sh2 = sh.split('background-color')
            new_sh = sh1 + 'background-color: rgb(220, 220, 220);'
            button.setStyleSheet(new_sh)

    def set_semantic_bg_when_press(self):
        if self.main_ui.pushButton_bg.objectName() == 'non_bg':
            self.main_ui.pushButton_bg.setObjectName('bg')
            self.main_ui.pushButton_bg.setIcon(QIcon('images/bg_label'))
        elif self.main_ui.pushButton_bg.objectName() == 'bg':
            self.main_ui.pushButton_bg.setObjectName('non_bg')
            self.main_ui.pushButton_bg.setIcon(QIcon('images/non_bg_label'))

    def set_semantic_bg_when_scan(self):
        img_path = self.imgs[self.cur_i]
        if self.EditImgMode or '图片已删除' in img_path:
            return

        img_name = img_path.split('/')[-1]
        check_stat = self.main_ui.pushButton_bg.objectName() == 'bg' if self.in_edit_mode() else False
        if self.OneFileLabel:
            img_dict = self.label_file_dict['labels'].get(img_name)
            if img_dict:  # 在编辑模式下如果未标注就继承上次的isChecked()
                if img_dict['polygons'] == ['bg']:
                    check_stat = True
                else:
                    check_stat = False
        elif self.SeparateLabel:
            json_path = self.get_separate_label(img_path, 'json')
            if osp.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if content['polygons'] == ['bg']:
                        check_stat = True
                    else:
                        check_stat = False

        if check_stat:
            self.main_ui.pushButton_bg.setObjectName('bg')
            self.main_ui.pushButton_bg.setIcon(QIcon('images/bg_label'))
        else:
            self.main_ui.pushButton_bg.setObjectName('non_bg')
            self.main_ui.pushButton_bg.setIcon(QIcon('images/non_bg_label'))

    def set_separate_label(self):
        self.SeparateLabel = self.main_ui.checkBox_separate_label.isChecked()
        self.main_ui.radioButton_read.setDisabled(self.WorkMode == self.AllModes[0] and not self.SeparateLabel)
        self.main_ui.radioButton_write.setDisabled(self.WorkMode == self.AllModes[0] and not self.SeparateLabel)

        if self.WorkMode == self.AllModes[2]:
            self.main_ui.pushButton_update_png.setDisabled(not self.SeparateLabel)

        if not self.SeparateLabel and not self.OneFileLabel:
            QMB.warning(self.main_ui, self.tr('未选择标注模式'), self.tr('请选择至少一种标注文件模式！'))
            self.main_ui.checkBox_one_label.setChecked(True)

    def set_shape_edit_mode(self):
        stat = self.main_ui.checkBox_shape_edit.isChecked()
        self.main_ui.img_widget.set_tool_mode(shape_edit=stat)
        self.set_action_disabled()

    def set_tool_mode(self):
        self.main_ui.img_widget.clear_scaled_img(to_undo=False)
        self.main_ui.img_widget.clear_all_polygons()
        draw = self.main_ui.toolBox.currentIndex() == 0
        ann = self.main_ui.toolBox.currentIndex() == 1 and self.task_root
        shape_edit = self.main_ui.toolBox.currentIndex() == 0 and self.main_ui.checkBox_shape_edit.isChecked()
        self.main_ui.img_widget.set_tool_mode(draw, shape_edit, ann)

        if self.main_ui.toolBox.currentIndex() == 1:
            self.paint_ann_img()

    def set_tv_bar(self):
        total_num = self.train_num + self.val_num
        if total_num:
            self.main_ui.label_train.set_tv(self.train_num, self.val_num)
            self.main_ui.label_val.set_tv(self.train_num, self.val_num)

    def set_tv_label(self):
        if self.EditImgMode:
            return

        img_name = self.current_img_name()
        if self.OneFileLabel:
            if self.label_file_dict['labels'].get(img_name):
                tv = self.label_file_dict['labels'][img_name]['tv']
                if tv == 'train':
                    self.main_ui.label_train_val.set_train()
                elif tv == 'val':
                    self.main_ui.label_train_val.set_val()
                else:
                    self.main_ui.label_train_val.set_none()
            else:
                self.main_ui.label_train_val.set_none()
        elif self.SeparateLabel:
            if self.WorkMode == self.AllModes[0]:
                c_name = self.cls_has_classified()
                if osp.exists(f'{self.get_root("tv")}/imgs/train/{c_name}/{img_name}'):
                    self.main_ui.label_train_val.set_train()
                elif osp.exists(f'{self.get_root("tv")}/imgs/val/{c_name}/{img_name}'):
                    self.main_ui.label_train_val.set_val()
                else:
                    self.main_ui.label_train_val.set_none()
            elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
                if osp.exists(f'{self.get_root("tv")}/imgs/train/{img_name}'):
                    self.main_ui.label_train_val.set_train()
                elif osp.exists(f'{self.get_root("tv")}/imgs/val/{img_name}'):
                    self.main_ui.label_train_val.set_val()
                else:
                    self.main_ui.label_train_val.set_none()

    def set_work_mode(self):
        self.save_backup_classes()
        self.save_one_file_json()

        self.main_ui.lineEdit.clear()
        self.main_ui.comboBox_2.setCurrentIndex(0)
        self.main_ui.comboBox_2.setDisabled(False)
        self.main_ui.label_train.setText(' train: 0')
        self.main_ui.label_train.setStyleSheet('border-top-left-radius: 4px;'
                                               'border-bottom-left-radius: 4px;'
                                               'background-color: rgb(200, 200, 200);')
        self.main_ui.label_val.setText('val: 0 ')
        self.main_ui.label_val.setStyleSheet('border-top-right-radius: 4px;'
                                             'border-bottom-right-radius: 4px;'
                                             'background-color: rgb(200, 200, 200);')
        self.reset_init_variables()
        self.set_buttons_checked()
        self.set_action_disabled()
        self.reset_seg_widgets()
        self.set_tool_mode()
        self.clear_shape_info()
        self.clear_marquee_layout()
        self.img_enhance_reset()

        tab_index = self.main_ui.tabWidget.currentIndex()
        self.WorkMode = self.main_ui.tabWidget.tabText(tab_index)

        if self.WorkMode != self.AllModes[0]:
            self.main_ui.radioButton_read.setText(self.tr('只读'))
            self.main_ui.radioButton_write.setText(self.tr('编辑'))
            self.main_ui.checkBox_separate_label.setText(self.tr('独立标注模式'))
            self.main_ui.radioButton_read.setDisabled(False)
            self.main_ui.radioButton_write.setDisabled(False)

        if self.WorkMode == self.AllModes[0]:
            self.main_ui.radioButton_read.setText(self.tr('剪切'))
            self.main_ui.radioButton_write.setText(self.tr('复制'))
            self.main_ui.radioButton_read.setDisabled(self.main_ui.checkBox_one_label.isChecked())
            self.main_ui.radioButton_write.setDisabled(self.main_ui.checkBox_one_label.isChecked())
            self.main_ui.checkBox_separate_label.setText(self.tr('划分至文件夹'))
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_task_mode(cls=True)
        elif self.WorkMode == self.AllModes[1]:
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_task_mode(m_cls=True)
        elif self.WorkMode == self.AllModes[3]:
            self.main_ui.img_widget.reset_cursor()
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.comboBox_2.setCurrentIndex(1)
                self.main_ui.comboBox_2.setDisabled(True)
                self.main_ui.img_widget.set_task_mode(det=True)
        elif self.WorkMode in self.AllModes[(2, 4)]:
            if self.main_ui.toolBox.currentIndex() == 0:
                self.main_ui.img_widget.set_task_mode(seg=True)

        self.main_ui.page_4.setDisabled(tab_index == 0 or tab_index == 1)

        stat = self.main_ui.radioButton_read.isChecked() or tab_index == 0 or tab_index == 1
        self.main_ui.checkBox_shape_edit.setChecked(False)
        self.main_ui.checkBox_shape_edit.setDisabled(stat)
        self.main_ui.pushButton_auto_infer.setDisabled(tab_index == 0 or tab_index == 1)

        self.main_ui.img_widget.paint_img('images/bg.png')
        self.main_ui.img_widget.clear_all_polygons()

    def show_class_selection_list(self):
        self.window_select_class.show_at(self.frameGeometry())

    def show_class_statistic(self):
        self.thread_cs = ClassStatistics(self.WorkMode, self.img_num, AllClasses.classes(), self.OneFileLabel,
                                         deepcopy(self.label_file_dict), self.SeparateLabel, self, self.language)

        self.thread_cs.start()
        self.show_waiting_label()

    def show_class_statistic_done(self, info):
        self.waiting_label.stop()
        self.waiting_label.close()
        self.window_class_stat = ClassStatWidget(info)
        self.window_class_stat.resize(self.window_class_stat.class_list.size())
        self.window_class_stat.show()

    def show_compare_img(self):
        path = self.file_select_dlg.getOpenFileName(self.main_ui, self.tr('选择图片'),
                                                    filter=self.tr('图片类型 (*.png *.jpg *.bmp)'))[0]
        if path:
            self.window_compare = BaseImgFrame(title=self.tr('图片窗口'))
            self.window_compare.paint_img(path)
            self.window_compare.show()

    def show_img_status_info(self):
        path = self.imgs[self.cur_i]
        self.cv2_img = cv2.imdecode(np.fromfile(path, dtype='uint8'), cv2.IMREAD_COLOR)
        self.cv2_img = cv2.cvtColor(self.cv2_img, cv2.COLOR_BGR2RGB)
        self.cv2_img_changed = self.cv2_img

        br_v = self.main_ui.horizontalSlider.value()
        co_v = self.main_ui.horizontalSlider_2.value() / 100
        pil_v = self.main_ui.horizontalSlider_3.value() / 100

        if pil_v == 1.:
            if br_v != 0. or co_v != 1.:
                self.cv2_img_changed = (self.cv2_img.astype('float32') + br_v) * co_v
                self.cv2_img_changed = np.clip(self.cv2_img_changed, a_min=0., a_max=255.)
        else:
            if pil_v != 1.:
                img = Image.fromarray(self.cv2_img)
                contrast_enhancer = ImageEnhance.Contrast(img)
                contrast_img = contrast_enhancer.enhance(pil_v)
                self.cv2_img_changed = np.array(contrast_img)

        h_flip, v_flip = self.main_ui.pushButton_82.isChecked(), self.main_ui.pushButton_83.isChecked()
        self.img_flip(h_flip=h_flip, v_flip=v_flip, do_paint=False)
        self.img_rotate(do_paint=False)

        height, width, depth = self.cv2_img_changed.shape
        qimg = QImage(self.cv2_img_changed.astype('uint8').data, width, height, width * depth, QImage.Format_RGB888)
        self.main_ui.img_widget.paint_img(qimg)

        if path == 'images/图片已删除.png':
            self.main_ui.label_path.setText(self.tr('图片已删除。'))
        else:
            self.main_ui.label_index.setText(f'<font color=violet>{self.cur_i + 1}</font>/{self.img_num}')
            self.bottom_img_text = path
            self.main_ui.label_path.setTextFormat(Qt.PlainText)
            self.main_ui.label_path.setText(uniform_path(self.bottom_img_text))
            img_w, img_h = self.main_ui.img_widget.img_size()
            c_time, m_time = get_file_cmtime(path)
            self.main_ui.label_img_info.setText('宽: {}, 高: {}<br>创建: {}, 修改: {}'.
                                                format(img_h, img_w, c_time, m_time))

            img_name = path.split('/')[-1]
            if img_name in self.pinned_imgs:
                self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_green.png'))
            else:
                self.main_ui.pushButton_pin.setIcon(QIcon('images/pin_black.png'))

            self.paint_ann_img()

    def show_label_to_ui(self):
        if not self.EditImgMode:
            if self.WorkMode == self.AllModes[0]:
                self.cls_to_button()
            elif self.WorkMode == self.AllModes[1]:
                self.m_cls_to_button()
            elif self.WorkMode in self.AllModes[(2, 3, 4)]:
                self.clear_shape_info()
                self.polygons_to_img()

    def show_menu(self, menu):  # 在鼠标位置显示菜单
        if menu.title() == 'label_list_menu':
            item = self.main_ui.shape_list.currentItem()
            if item is not None:
                if item.icon().cacheKey() == 0:
                    self.action_lock_shape.setText(self.tr('锁定标注'))
                else:
                    self.action_lock_shape.setText(self.tr('取消锁定'))

        menu.exec(QCursor.pos())

    def show_shape_info(self, polygon):
        if self.action_oc_shape_info.text() == self.tr('启用（降低切图速度）'):
            return

        lw = self.current_shape_info_widget()
        if lw is not None:
            item = QListWidgetItem()
            item.setText(self.get_info_text(polygon))
            color = QColor(polygon['qcolor'])
            item.setForeground(color)
            lw.addItem(item)

    def show_task_window(self):
        self.window_build_task.set_work_mode_img_folder(self.WorkMode, self.image_folder)
        self.window_build_task.show()

    def show_waiting_label(self):
        self.waiting_label = WaitingLabel(self, self.tr('等待中'))
        self.waiting_label.show_at(self.frameGeometry())

    def show_xy_color(self, info):
        x, y, r, g, b = info
        self.main_ui.label_xyrgb.setText(f'X: {x}, Y: {y} <br>'  # &nbsp; 加入空格
                                         f'<font color=red> R: {r}, </font>'
                                         f'<font color=green> G: {g}, </font>'
                                         f'<font color=blue> B: {b} </font>')

    def undo_painting(self):
        self.main_ui.img_widget.undo_stack.undo()

    def update_class_list_num(self, num):
        signal = self.sender()

        if signal.name == 'class':
            self.main_ui.pushButton_class_list.setText(self.tr('类别列表（{}）').format(num))
        elif signal.name == 'shape':
            self.main_ui.pushButton_shape_list.setText(self.tr('标注列表（{}）').format(num))
            if self.WorkMode == self.AllModes[2]:
                self.main_ui.pushButton_bg.setDisabled(not self.in_edit_mode() or (num > 0))

    def update_progress_value(self, info):
        class_name, value = info
        if class_name is UpdateSemanticPngs:
            self.window_usp_progress.set_value(value)

    def update_progress_text(self, info):
        class_name, text = info
        if class_name is UpdateSemanticPngs:
            self.window_usp_progress.set_text(text)

    def update_sem_pngs(self):
        classes = AllClasses.classes()
        if not classes:
            QMB.warning(None, self.tr('类别列表为空'), self.tr('请先加载类别。'))
            signal_usp_done.send(False)
            return

        self.thread_usp = UpdateSemanticPngs(self.imgs, classes, self)
        self.thread_usp.start()
        self.window_usp_progress = ProgressWindow(title=self.tr('PNG更新'), text_prefix=self.tr('更新PNG标注中：'))
        self.window_usp_progress.show()

    def update_sem_pngs_done(self, info):
        done, num = info
        if done:
            self.window_usp_progress.set_text(self.tr('{}张，已完成。').format(num))

    def update_shape_info_text(self, i):
        if self.action_oc_shape_info.text() == self.tr('启用（降低切图速度）'):
            return

        lw = self.current_shape_info_widget()
        if lw is not None:
            text = self.get_info_text(self.main_ui.img_widget.get_one_polygon(i))
            lw.item(i).setText(text)

    def version_remind(self):
        version = self.current_version()
        self.window_version_remind.set_dont_show_flag(version)
        self.window_version_remind.show(self.tr('保存标注中，以版本"{}"保存吗？').format(version))
        if not self.window_version_remind.result():
            return False

        version_path = self.get_root('version')
        txt_path = f'{version_path}/description.txt'
        if osp.exists(txt_path):
            return True
        else:
            text, is_ok = self.input_dlg.getText(self.main_ui, self.tr(f'版本描述'),
                                                 self.tr('请输入版本描述,可直接点击"确定"跳过。'), QLineEdit.Normal)
            if is_ok:
                os.makedirs(version_path, exist_ok=True)
                with open(f'{version_path}/description.txt', 'w', encoding='utf-8') as f:
                    f.writelines(text)
                return True
            return False

# doing----------
# todo: 标注文件加入版本管理？
# todo: 统计信息 加入未标注 未划分 图片标签统计  导出类别统计txt？
# todo: 类别统计，长类别名 对不齐  用textbrowser？
# doing----------

# todo: shape的交集，并集、差集  环形支持多形状组合以及多孔洞环形
# todo: 像素标注支持粗细调节
# todo: 合并labels.json
# todo: auto inference 全功能  支持 ONNX、openvino、（opencv接口？ 自写接口？）
# todo：按shape 的tag浏览


# todo: pin 功能 扩展为tag功能
# todo: 视频标注 全功能
# todo: ubuntu 用 docker?
# todo: 摄像头 实时检测与标注？
# todo: 旋转目标检测？
# todo: 伪标注合成全功能

# todo: shape list drag

# todo: marquee进度条同步(搁置) https://forum.qt.io/topic/141592/can-not-move-horizontalscrollbar-to-the-rightmost-side
# todo: ubuntu 部分弹出窗口不在屏幕中心位置
# todo: ubuntu 按钮右键时同时弹出上层容器的右键菜单
# todo: win11测试
# todo: 完善log

# 未解决的问题
# https://forum.qt.io/topic/141592/can-not-move-horizontalscrollbar-to-the-rightmost-side
# https://forum.qt.io/topic/141742/how-to-translate-text-with-quiloader
