import pdb
import random, shutil, cv2, json, time, git

from copy import deepcopy
from PIL import ImageEnhance
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QFileDialog, QInputDialog, QLineEdit, QColorDialog, QListWidgetItem, \
    QApplication
from PySide6.QtWidgets import QMessageBox as QMB
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QCursor, QColor, QFontMetrics
from need.main_utils import *
from need.custom_widgets import *
from need.custom_threads import *
from need.custom_signals import ErrorSignal
from need.algorithms import get_seg_mask
from need.functions import *
from need.utils import MonitorVariable, INS_all_classes
from need.SharedWidgetStatFlags import stat_flags


# noinspection PyUnresolvedReferences
# !!!控件若是通过触发再初始化创建，要注意控件对象被释放后，内存是否还占用的问题，若控件一开始就先初始化好就可以避免这个问题!!!
class HHL_MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr('花火标注'))
        self.setWindowIcon(QIcon('images/icon.png'))
        self.setFocusPolicy(Qt.StrongFocus)
        self.loader = QUiLoader()
        register_custom_widgets(self.loader)
        self.ui = self.loader.load('main_window.ui')  # 主界面
        self.setCentralWidget(self.ui)
        self.resize(1280, 920)

        with open('project.json', 'r', encoding='utf-8') as f:
            self.language = json.load(f)['language']

        self.image_folder = self.tr('原图')
        self.label_folder = self.tr('标注')
        self.tv_folder = self.tr('训练集&验证集')
        self.ann_folder = self.tr('注释图片')
        self.OneFileLabel = True
        self.SeparateLabel = False
        self.LabelUiCallByMo = False  # 用于区分self.label_ui是由新标注唤起还是由修改标注唤起
        self.signal_error2app = ErrorSignal()
        self.task_cfg = {'one_file': True, 'separate_file': False, 'task_desc': '', 'img_classes': {},
                         'img_tags': {}, 'obj_classes': {}, 'obj_tags': {}, 'version_head': '',
                         'tracked_files': ['task_cfg.json', self.label_folder]}

        # self.thread_auto_save = AutoSave(5 * 60)  # 5min
        self.file_select_dlg = QFileDialog(self)
        self.input_dlg = QInputDialog(self)
        self.color_dlg = QColorDialog(self)

        self.mor_vars = MonitorVariable(self.ui)
        init_custom_widgets(self)
        self.init_variables()
        self.reset_init_variables()
        init_menu(self)
        self.obj_info_show_set()
        self.set_action_disabled()
        connect_signals(self)
        self.log_info('Application opened.', mark_line=True)

        self.center_img = self.ui.graphicsView.img_area

    def closeEvent(self, e):
        close_sub_windows(self)
        # self.save_one_file_json()
        # self.thread_auto_save.terminate()

        with open('project.json', 'w', encoding='utf-8') as f:
            json.dump({'language': self.language}, f, sort_keys=False, ensure_ascii=False, indent=4)

        self.task_cfg_export()
        self.log_info('Application closed.', mark_line=True)
        self.close()
        self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            cursor_pos = self.mapFromGlobal(QCursor.pos()).toTuple()
            w, h = self.ui.graphicsView.width(), self.ui.graphicsView.height()
            if (0 < cursor_pos[0] < w + 10) and (0 < cursor_pos[1] < h + 20):
                if self.check_warnings('edit_mode'):
                    self.center_img.focus_set_img_area(ctrl_press=True)
        else:
            if event.key() == Qt.Key_A:
                if self.check_warnings('selecting_cate_tag'):
                    self.scan_img(last=True)
            elif event.key() == Qt.Key_D:
                if self.check_warnings('selecting_cate_tag'):
                    self.scan_img(next=True)
            elif event.key() == Qt.Key_Return:
                if self.ui.jump_to.spinBox.hasFocus():
                    self.img_jump()

    def moveEvent(self, event):
        if self.window_shape_combo.isVisible():
            self.window_shape_combo.move_to(self.pos() + self.shape_combo_offset)

    def resizeEvent(self, event):
        font_metrics = QFontMetrics(self.ui.label_path.font())
        str_w = font_metrics.size(0, self.bottom_img_text).width()
        label_w = self.ui.label_path.width()

        if str_w > label_w - 12:  # 左下角信息自动省略
            elideNote = font_metrics.elidedText(self.bottom_img_text, Qt.ElideRight, label_w)
            self.ui.label_path.setText(elideNote)

    def wheelEvent(self, event):
        if self.check_warnings('selecting_cate_tag'):
            e_x, e_y = event.position().toTuple()
            tl_x, tl_y = self.ui.groupBox.pos().toTuple()
            bl_x, bl_y = self.ui.groupBox_2.pos().toTuple()

            if e_x > tl_x + 10 and (tl_y + 20 < e_y < bl_y - 10):
                pos = self.ui.mapToGlobal(self.ui.groupBox_2.pos() + QPoint(10, -70))

                if event.angleDelta().y() > 0:
                    self.ui.radioButton_read.setChecked(True)
                    self.widget_read_edit.set_pixmap_pos('images/read_edit_info/switch_to_read.png', pos)
                else:
                    self.ui.radioButton_write.setChecked(True)
                    self.widget_read_edit.set_pixmap_pos('images/read_edit_info/switch_to_edit.png', pos)

                self.widget_read_edit.show()
                self.activateWindow()

    @property
    def cur_i(self):
        return self.__cur_i

    def about_hhl(self):
        ui = CustomMessageBox('about', self.tr('关于花火标注'), hide_dsa=True)
        ui.add_text(self.tr('版本1.0.0。\n'
                            '\n'
                            '花火标注是一款使用PySide6开发的多功能标注工具，支持包括单类别分类、多类别分类、语义分割、目标检测和实例分割在内的5种计算'
                            '机视觉任务的数据标注。花火标注还支持自动标注、数据集管理、伪标注合成等多种功能，可以帮助您更加方便、高效得训练AI模型。\n'
                            '\n'
                            '花火标注采用GNU GPL许可证，您可以随意使用该工具。但在未取得作者许可的情况下，请勿使用该软件进行商业行为。\n'))
        ui.show(clear_old=False)

    def add_buttons(self):
        widget = self.sender()

        if widget.objectName() == 'pushButton_img_cate_add':
            self.ui.img_cate_buttons.add_button(is_enable=stat_flags.HHL_Edit_Mode)
        elif widget.objectName() == 'pushButton_img_tag_add':
            self.ui.img_tag_buttons.add_button(is_enable=stat_flags.HHL_Edit_Mode)
        elif widget.objectName() == 'pushButton_obj_cate_add':
            self.ui.obj_cate_buttons.add_button()
        elif widget.objectName() == 'pushButton_obj_tag_add':
            self.ui.obj_tag_buttons.add_button()

    def add_to_train_val(self, dst_part, img_path=None, pass_one_file=False, pass_separate_file=False):
        if not self.check_warnings(['task', 'edit_mode']):
            return

        if img_path is None:  # 直接由按钮触发
            cur_path = self.imgs[self.__cur_i]
        else:
            cur_path = img_path

        if '图片已删除' in cur_path:
            return

        img_name = cur_path.split('/')[-1]
        tv_tag = ['train', 'val']
        tv_tag.remove(dst_part)
        opp_part = tv_tag[0]

        if not self.has_labeled(cur_path):
            QMB.warning(self.ui, self.tr('图片无标注'), self.tr('当前图片尚未标注!'))
            return

        if self.OneFileLabel and not pass_one_file:
            img_tv = self.label_file_dict['labels'][img_name]['tv']

            if img_tv == 'train' and dst_part == 'val':
                self.mor_vars.train_num -= 1
                self.mor_vars.val_num += 1
            elif img_tv == 'val' and dst_part == 'train':
                self.mor_vars.train_num += 1
                self.mor_vars.val_num -= 1
            elif img_tv == 'none':
                if dst_part == 'train':
                    self.mor_vars.train_num += 1
                elif dst_part == 'val':
                    self.mor_vars.val_num += 1

            self.label_file_dict['labels'][img_name]['tv'] = dst_part

        if self.SeparateLabel and not pass_separate_file:
            tv_img_path = f'{self.get_root("tv")}/imgs/{dst_part}'
            os.makedirs(tv_img_path, exist_ok=True)

            tv_label_path = f'{self.get_root("tv")}/labels/{dst_part}'
            os.makedirs(tv_label_path, exist_ok=True)

            if img_path is None and self.current_tv() == opp_part:
                opp_img_path = tv_img_path.replace(dst_part, opp_part) + f'/{img_name}'
                file_remove(opp_img_path)
                file_remove(opp_img_path.replace('imgs', 'labels')[:-3] + 'json')

                if not self.OneFileLabel:
                    if opp_part == 'train':
                        self.mor_vars.train_num -= 1
                    elif opp_part == 'val':
                        self.mor_vars.val_num -= 1

            shutil.copy(cur_path, tv_img_path)
            shutil.copy(self.get_separate_label(cur_path, 'json'), tv_label_path)

            if not self.OneFileLabel:
                if dst_part == 'train':
                    self.mor_vars.train_num += 1
                elif dst_part == 'val':
                    self.mor_vars.val_num += 1

        self.set_tv_label()

    def auto_in(self):
        return

        os.makedirs(f'{self.task_root}/实例分割/自动标注', exist_ok=True)
        classes = INS_all_classes.classes()
        if len(classes) == 0:
            QMB.critical(self.ui, '未找到类别名称', '当前类别数量为0，请先加载类别。')
            return

        QMB.information(self.ui, '加载onnx文件', '请选择一个onnx文件。')

        onnx_file = self.file_select_dlg.getOpenFileName(self.ui, '选择ONNX文件', filter='onnx (*.onnx)')[0]
        if not onnx_file:
            return
        re = QMB.question(self.ui, '自动推理',
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
            QMB.critical(self.ui, '输入错误', f'模型只能有一个输入，实际检测到{len(inputs)}个输入。')
            return

        in_type, in_shape, in_name = inputs[0].type, tuple(inputs[0].shape), inputs[0].name
        if in_type != 'tensor(uint8)':
            QMB.critical(self.ui, '输入错误', f'模型输入的类型必须为tensor(uint8)，实际为{in_type}。')
            return

        QMB.information(self.ui, '图片形状不匹配',
                        f'模型输入尺寸：{in_shape}，如果图片尺寸不匹配，图片将自动调整至需要的尺寸。')

        content, is_ok = self.input_dlg.getText(self.ui, f'请输入DP抽稀算法阈值, 轮廓点数最小值、最大值',
                                                '请输入整数，阈值越高，抽稀后轮廓点数越少，反之越多，默认为(2, 4, 50)',
                                                QLineEdit.Normal, text='2, 4, 50')
        if is_ok:
            try:
                dp_para = content.replace('，', ',').split(',')
                dp_para = [float(one.strip()) for one in dp_para]
            except:
                QMB.critical(self.ui, '格式错误', f'请输入正确的格式，参照：2, 4, 40。')
                return
        else:
            return

        content, is_ok = self.input_dlg.getText(self.ui, f'请输入面积过滤阈值',
                                                '面积为目标区域对应的像素数量，低于阈值的目标将被过滤， 默认为16',
                                                QLineEdit.Normal, text='16')
        if is_ok:
            try:
                filter_area = int(content.strip())
            except:
                QMB.critical(self.ui, '格式错误', f'请输入正确的格式，参照：16。')
                return
        else:
            return

        self.window_auto_infer_progress.show()

        self.inference_thread = RunInference(sess, self.imgs, INS_all_classes.classes(), dp_para, filter_area)
        self.inference_thread.start()

    def auto_inference(self):
        classes = INS_all_classes.classes()
        if not classes:
            QMB.warning(None, self.tr('类别数量为0'), self.tr('当前类别数量为0，请先加载类别。'))
            return

        self.window_auto_infer = AutoInfer(self.WorkMode, self.get_root('version'))
        self.window_auto_infer.show()

    def auto_save(self):
        pass
        # self.save_one_file_json()

    def cate_button_update(self, from_where):  # 按钮状态发生变化时，实时更新并保存task_cfg
        if from_where in ('ImgCateButton', 'img_cate_buttons'):
            self.task_cfg['img_classes'] = self.ui.img_cate_buttons.button_stat
        elif from_where in ('ImgTagButton', 'img_tag_buttons'):
            self.task_cfg['img_tags'] = self.ui.img_tag_buttons.button_stat
        elif from_where in ('ObjCateButton', 'obj_cate_buttons'):
            self.task_cfg['obj_classes'] = self.ui.obj_cate_buttons.button_stat
        elif from_where in ('ObjTagButton', 'obj_tag_buttons'):
            self.task_cfg['obj_tags'] = self.ui.obj_tag_buttons.button_stat
        else:
            raise TypeError(f'Unsupport button type: "{from_where}".')

        self.task_cfg_export()

    # done--------------------------
    def change_cross_color(self):
        if self.color_dlg.exec() == QColorDialog.Accepted:
            color = self.color_dlg.selectedColor()
            r, g, b = color.red(), color.green(), color.blue()
            cross = cv2.imread('images/cross_line.png', cv2.IMREAD_UNCHANGED)
            h, w = cross.shape[:2]
            new_color = np.ones((h, w, 4), dtype='uint8') * np.array([[r, g, b, 255]], dtype='uint8')
            mask = (cross[:, :, 2] != 0).astype('uint8')
            mask = np.repeat(mask[:, :, None], 4, axis=2)
            new_color *= mask
            self.ui.pushButton_cross_color.setIcon(QIcon(QPixmap(array_to_qimg(new_color))))
            self.center_img.change_pen(det_cross_color=QColor(color.name()))

    def change_font_color(self):
        if self.color_dlg.exec() == QColorDialog.Accepted:
            color = self.color_dlg.selectedColor()
            self.ui.pushButton_font_color.setStyleSheet('QPushButton { color: %s }' % color.name())
            self.center_img.change_font(ann_font_color=QColor(color.name()))

    def change_font_size(self):
        self.center_img.change_font(ann_font_size=self.ui.spinBox_fontsize.value())

    def change_one_class_category(self):
        new_c, ok = self.input_dlg.getText(self.ui, self.tr('修改类别'), self.tr('请输入类别名称'),
                                           QLineEdit.Normal)
        if ok:
            new_c = new_c.strip()
            cur_c = self.ui.class_list.currentItem().text()
            re = QMB.question(self.ui, self.tr('修改类别'),
                              self.tr('确定将所有<font color=red>{}</font>修改为'
                                      '<font color=red>{}</font>吗？').format(cur_c, new_c))
            if re == QMB.Yes:
                self.thread_cocc = ChangeOneClassCategory(self.imgs, self.WorkMode, self.OneFileLabel,
                                                          self.SeparateLabel, deepcopy(self.label_file_dict),
                                                          INS_all_classes.classes(), cur_c, new_c, self)
                self.thread_cocc.start()
                self.show_waiting_label()

    def change_one_class_category_done(self, info):
        done, new_c = info
        if done:
            if self.OneFileLabel:
                self.label_file_dict = self.thread_cocc.label_file_dict

            if new_c in INS_all_classes.classes():
                self.ui.class_list.del_row(self.ui.class_list.currentRow())
            else:
                self.ui.class_list.modify_cur_c(new_c)

            QMB.information(self.ui, self.tr('修改完成'), self.tr('已完成, 类别列表已备份，请重新打开目录。'))

        self.waiting_label.stop()
        self.waiting_label.close()

    def change_pen_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            if self.ui.toolBox.currentIndex() == 0:
                self.center_img.change_pen(seg_pen_color=QColor(color.name()))
            elif self.ui.toolBox.currentIndex() == 1:
                self.center_img.change_pen(ann_pen_color=QColor(color.name()))

    def change_pen_size(self):
        if self.ui.toolBox.currentIndex() == 0:
            self.center_img.change_pen(seg_pen_size=self.ui.spinBox_thickness.value())
        elif self.ui.toolBox.currentIndex() == 1:
            self.center_img.change_pen(ann_pen_size=self.ui.spinBox_thickness2.value())

    def check_warnings(self, names: Union[list[str], str]):
        if type(names) == str:
            names = [names]

        for one in names:
            if one == 'task':
                if not self.task_root:
                    QMB.information(self, self.tr('未加载任务'), self.tr('请先加载任务。'))
                    return False
            elif one == 'edit_mode':
                if not self.ui.radioButton_write.isChecked():
                    QMB.information(self, self.tr('模式错误'), self.tr('请先切换至编辑模式。'))
                    return False
            elif one == 'sem_bg':
                if self.ui.checkBox_sem_bg.isChecked():
                    QMB.warning(self.ui, self.tr('已作为背景'), self.tr('当前图片已作为语义分割背景。'))
                    return False
            elif one == 'git':
                if self.repo is None:
                    QMB.warning(self.ui, self.tr('Git初始化失败'), self.tr('Git初始化失败，请检查Git客户端是否已安装。'))
                    return False
            elif one == 'cate_selected':
                if 'null' not in str(self.ui.pushButton_waiting_cate.icon()):  # 通过icon来判断是哪个实例调用了这个函数
                    if not self.ui.obj_cate_buttons.selected_buttons():
                        QMB.critical(self, self.tr('类别未选择！'), self.tr('请选择至少一个类别！'))
                        return False
            elif one == 'selecting_cate_tag':
                if self.ui.pushButton_waiting_cate.isVisible() or self.ui.pushButton_waiting_tag.isVisible():
                    QMB.warning(self, self.tr('标注未完成！'), self.tr('请先完成当前图形的标注。'))
                    return False
            else:
                raise TypeError('Unsupported warning.')
        return True

    def clear_painted_img(self):
        self.center_img.clear_scaled_img(to_undo=True)

    def cls_to_button(self):
        self.buttons_clear()
        category = self.cls_has_classified()
        has_this_class = False
        if category:
            button_layout = self.ui.groupBox_1.layout()
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

    def current_img_name(self):
        return self.imgs[self.__cur_i].split('/')[-1]

    def current_tv(self):
        return self.ui.label_train_val.text()

    def del_all_shapes(self, del_all=True):
        if del_all:
            self.center_img.clear_all_polygons()
            self.ui.obj_list.clear()
        else:
            self.center_img.del_polygons()

        self.ui.setFocus()

    def del_existed_file(self, cur_path, file_path):
        if cur_path == file_path:
            raise SystemError('func: del_existed_file, 路径相同, 请检查。')

        if osp.exists(file_path):
            choice = QMB.question(self.ui, self.tr('文件已存在'), self.tr('{}已存在，要覆盖吗？').format(file_path))
            if choice == QMB.Yes:
                os.remove(file_path)
                return True
            elif choice == QMB.No:  # 右上角关闭按钮也返回QMB.No
                return False
        else:
            return True

    def del_img(self, dst_path=None):
        assert 0 <= self.__cur_i < len(self.imgs), 'Error, 0 <= self.__cur_i < len(self.imgs) not satisfied.'

        img_path = self.imgs[self.__cur_i]
        img_name = img_path.split('/')[-1]
        if '图片已删除' in img_name:
            return

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
            if file_remove(f'{self.get_root("tv")}/imgs/train/{img_name}'):
                self.mor_vars.train_num -= 1
            if file_remove(f'{self.get_root("tv")}/imgs/val/{img_name}'):
                self.mor_vars.val_num -= 1

            path_del_label = f'{self.task_root}/deleted/{self.WorkMode}/{self.label_folder}'
            os.makedirs(path_del_label, exist_ok=True)

            json_path = self.get_separate_label(img_path, 'json')
            t_json_path = f'{self.get_root("tv")}/labels/train/{json_path.split("/")[-1]}'
            v_json_path = f'{self.get_root("tv")}/labels/val/{json_path.split("/")[-1]}'

            if osp.exists(json_path):
                self.file_move(json_path, path_del_label)
                file_remove([t_json_path, v_json_path])

        self.imgs[self.__cur_i] = 'images/图片已删除.png'  # 将删除的图片替换为背景图片
        self.show_img_status_info()
        self.ui.listWidget_imgs_flow.set_cur_deleted()
        self.go_next_img()

    def del_shape(self, i):
        self.ui.obj_list.del_row(i)
        if self.ui.listWidget_obj_info.count():
            self.ui.listWidget_obj_info.takeItem(i)

    def delete_one_class_jsons(self):
        c_name = self.ui.class_list.currentItem().text()
        re = QMB.question(self.ui, self.tr('删除类别'), self.tr('确定删除所有<font color=red>{}</font>标注吗？')
                          .format(c_name))

        if re == QMB.Yes:
            # 删除某一类后，若图片无标注，则对应的标注文件会删除，原图不会，train和val里的对应图片和标注都会删除
            self.thread_docl = DeleteOneClassLabels(self.imgs, self.WorkMode, self.OneFileLabel,
                                                    self.SeparateLabel, deepcopy(self.label_file_dict),
                                                    INS_all_classes.classes(), c_name, self)
            self.thread_docl.start()
            self.show_waiting_label()

    def delete_one_class_jsons_done(self, done):
        if done:
            if self.OneFileLabel:
                self.label_file_dict = self.thread_docl.label_file_dict

            self.ui.class_list.del_row(self.ui.class_list.currentRow())

            QMB.information(self.ui, self.tr('删除完成'), self.tr('已完成, 类别列表已备份，请重新打开目录。'))

        self.waiting_label.stop()
        self.waiting_label.close()

    def edit_img(self):
        self.dialog_img_edit.exec()

    def file_move(self, src_path, dst_dir):
        new_file_path = osp.join(dst_dir, src_path.split('/')[-1])
        if self.del_existed_file(src_path, new_file_path):
            shutil.move(src_path, dst_dir)

    def flow_move(self, left=False, right=False):  # 该函数以及其调用的函数都不能去改变self.__cur_i
        if '图片已删除' in self.imgs[self.__cur_i]:
            self.ui.listWidget_imgs_flow.set_cur_stat('undo')
        else:
            stat = self.flow_stat(self.imgs[self.__cur_i])
            self.ui.listWidget_imgs_flow.set_cur_stat(stat)

        img_path = ''
        if left:
            if self.__cur_i > 0:
                img_path = self.imgs[self.__cur_i - 1]
        elif right:
            if self.__cur_i < self.img_num - 1:
                img_path = self.imgs[self.__cur_i + 1]

        if img_path:
            self.ui.listWidget_imgs_flow.img_flowing(img_path, left, right)

    def flow_show(self, info):
        img_path, show_png = info

        if show_png:
            classes = INS_all_classes.classes()
            if len(classes) == 0:
                QMB.warning(self.ui, self.tr('类别数量为0'), self.tr('当前类别数量为0，请先加载类别。'))
                return

            qimg_png = self.get_qimg_png(img_path)
            if qimg_png:
                self.window_flow_label.paint_img(qimg_png, img_path)
                self.window_flow_label.show()

        else:
            if (pixmap := img_path2_qpixmap(img_path)) is not None:
                self.window_flow_img.paint_img(pixmap, img_path)
                self.window_flow_img.show()

    def flow_stat(self, path):  # 获取某个子图的处理状态  #todo-------------
        stat = 'undo'
        # if self.OneFileLabel:
        #     img_name = path.split('/')[-1]
        #     if self.label_file_dict['labels'].get(img_name):
        #         if self.label_file_dict['labels'][img_name]['polygons']:
        #             stat = 'done'
        # elif self.SeparateLabel:
        #     json_path = self.get_separate_label(path, 'json')
        #     if osp.exists(json_path):
        #         with open(json_path, 'r', encoding='utf-8') as f:
        #             content = json.load(f)
        #         stat = 'done' if content['polygons'] else 'undo'
        return stat

    def fold_buttons(self):  # done ------------------------------
        visible = True
        widget = self.sender()

        if widget.objectName() == 'pushButton_img_cate':
            visible = self.ui.img_cate_buttons.isVisible()
            self.ui.img_cate_buttons.setVisible(not visible)
            self.ui.pushButton_img_cate_add.setDisabled(visible)
        elif widget.objectName() == 'pushButton_img_tag':
            visible = self.ui.img_tag_buttons.isVisible()
            self.ui.img_tag_buttons.setVisible(not visible)
            self.ui.pushButton_img_tag_add.setDisabled(visible)
        elif widget.objectName() == 'pushButton_obj_cate':
            visible = self.ui.obj_cate_buttons.isVisible()
            self.ui.obj_cate_buttons.setVisible(not visible)
            self.ui.pushButton_obj_cate_add.setDisabled(visible)
            self.ui.pushButton_waiting_cate.set_activated(not visible)
        elif widget.objectName() == 'pushButton_obj_tag':
            visible = self.ui.obj_tag_buttons.isVisible()
            self.ui.obj_tag_buttons.setVisible(not visible)
            self.ui.pushButton_obj_tag_add.setDisabled(visible)
            self.ui.pushButton_waiting_tag.set_activated(not visible)

        if visible:
            widget.setIcon(QIcon('images/direction/down.png'))
        else:
            widget.setIcon(QIcon('images/direction/up.png'))

    def generate_train(self):
        if not self.check_warnings(['task', 'edit_mode']):
            return

        if self.OneFileLabel:
            for k, v in self.label_file_dict['labels'].items():
                if v['tv'] != 'val':
                    img_path = f'{self.get_root("img")}/{k}'
                    self.add_to_train_val('train', img_path, pass_separate_file=True)

        if self.SeparateLabel:
            choice = QMB.question(self.ui, self.tr('独立标注模式'), self.tr('训练集将被覆盖，继续吗？'))
            if choice == QMB.Yes:
                if not self.OneFileLabel:
                    self.mor_vars.train_num = 0

                if osp.exists(f'{self.get_root("tv")}/imgs/train'):
                    shutil.rmtree(f'{self.get_root("tv")}/imgs/train')
                if osp.exists(f'{self.get_root("tv")}/labels/train'):
                    shutil.rmtree(f'{self.get_root("tv")}/labels/train')

                val_img_list = glob_imgs(f'{self.get_root("tv")}/imgs/val')
                val_img_list = [one.split('/')[-1] for one in val_img_list]
                for one in self.imgs:
                    if self.has_labeled(one) and one.split('/')[-1] not in val_img_list:
                        self.add_to_train_val('train', one, pass_one_file=True)

        QMB.information(self.ui, self.tr('已完成'), self.tr('已完成。'))

    def get_img_tv(self, img_path):
        img_name = img_path.split('/')[-1]
        if self.OneFileLabel:
            if self.label_file_dict['labels'].get(img_name):
                return self.label_file_dict['labels'][img_name]['tv']
            else:
                return 'none'
        elif self.SeparateLabel:
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
            img_path = self.imgs[self.__cur_i]
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
        classes = INS_all_classes.classes()
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

        if seg_mask is not None:  # todo：增加界面设置，颜色是按类区分还是目标区分
            if self.WorkMode == self.AllModes[2]:
                png_img = seg_mask * int(255 / len(classes))
                return array_to_qimg(png_img)
            elif self.WorkMode == self.AllModes[4]:
                color = np.random.randint(20, 255, size=(100, 3), dtype='uint8')
                color[0, :] *= 0
                png_img = color[seg_mask]
                return array_to_qimg(png_img)
        else:
            return None

    def get_root(self, root):
        if root == 'img':
            return f'{self.task_root}/{self.image_folder}'
        elif root == 'label':
            return f'{self.task_root}/{self.label_folder}'
        elif root == 'tv':
            return f'{self.task_root}/{self.tv_folder}'
        elif root == 'ann':
            return f'{self.task_root}/{self.ann_folder}'

    def get_separate_label(self, img_path, suffix):
        label_root = self.get_root('label')
        img_pure_name = img_path.split('/')[-1][:-4]
        return f'{label_root}/{img_pure_name}.{suffix}'

    def get_tv_num(self):
        if self.OneFileLabel:
            self.mor_vars.train_num, self.mor_vars.val_num = 0, 0
            for one in self.label_file_dict['labels'].values():
                if one['tv'] == 'train':
                    self.mor_vars.train_num += 1
                elif one['tv'] == 'val':
                    self.mor_vars.val_num += 1
        elif self.SeparateLabel:
            self.mor_vars.train_num = len(glob_imgs(f'{self.get_root("tv")}/imgs/train'))
            self.mor_vars.val_num = len(glob_imgs(f'{self.get_root("tv")}/imgs/val'))

    def graphics_reset(self):  # 清空所有任务相关的控件
        self.ui.obj_list.clear()
        self.center_img.clear_all_polygons()
        self.center_img.collection_window.ui.listWidget.clear()
        self.center_img.reset_cursor()
        self.center_img.set_shape_locked(False)
        self.ui.listWidget_imgs_flow.clear()
        self.ui.label_train.setText(' train: 0')
        self.ui.label_train.setStyleSheet('border-top-left-radius: 4px;'
                                          'border-bottom-left-radius: 4px;'
                                          'background-color: rgb(200, 200, 200);')
        self.ui.label_val.setText('val: 0 ')
        self.ui.label_val.setStyleSheet('border-top-right-radius: 4px;'
                                        'border-bottom-right-radius: 4px;'
                                        'background-color: rgb(200, 200, 200);')

        self.ui.radioButton_read.setChecked(True)
        self.ui.obj_list.edit_button.setChecked(False)
        self.ui.obj_list.edit_button.setDisabled(not stat_flags.HHL_Edit_Mode)

        self.obj_info_show_set()
        self.set_action_disabled()
        self.img_enhance_reset()

    def go_next_img(self):
        self.flow_move(right=True)

        if self.__cur_i < self.img_num - 1:
            self.__cur_i += 1
            self.show_img_status_info()
            self.show_label_to_ui()
            self.set_tv_label()
        else:
            self.show_label_to_ui()
            self.set_tv_label()
            self.ui.listWidget_imgs_flow.set_cur_stat('done')
            self.__cur_i += 1
            self.ui.label_path.setText(self.tr('已完成。'))
            QMB.information(self.ui, self.tr('已完成'), self.tr('已完成。'))

    def go_next_sub_window(self):
        img_path = self.imgs[self.__cur_i]
        # if self.window_flow_label:
        #     qimg_png = self.get_qimg_png(img_path)
        #     if qimg_png:
        #         self.window_flow_label.paint_img(qimg_png, img_path)
        # if self.window_flow_img:
        #     if (pixmap := img_path2_qpixmap(img_path)) is not None:
        #         self.window_flow_img.paint_img(pixmap, img_path)

    def has_labeled(self, img_path):
        img_name = img_path.split('/')[-1]
        if self.OneFileLabel:
            if self.label_file_dict['labels'].get(img_name):
                return True
            return False
        elif self.SeparateLabel:
            json_path = self.get_separate_label(img_path, 'json')
            if osp.exists(json_path):
                return True
            return False

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
        self.ui.horizontalSlider_3.setValue(100)

        brightness_v = self.ui.horizontalSlider.value()
        self.ui.label_3.setText(str(brightness_v))
        contrast_v = self.ui.horizontalSlider_2.value() / 100
        self.ui.label_4.setText(str(contrast_v))

        if len(self.imgs):
            self.cv2_img_changed = (self.cv2_img.astype('float32') + brightness_v) * contrast_v
            self.cv2_img_changed = np.clip(self.cv2_img_changed, a_min=0., a_max=255.)
            self.center_img.paint_img(array_to_qimg(self.cv2_img_changed),
                                      re_center=False, img_info_update=False)

    def img_enhance_reset(self):
        self.ui.pushButton_82.setChecked(False)
        self.ui.pushButton_83.setChecked(False)
        self.ui.pushButton_81.setText(' 0°')
        self.ui.pushButton_81.setChecked(False)
        self.ui.horizontalSlider.setValue(0)  # setValue 自动触发valueChanged信号
        self.ui.horizontalSlider_2.setValue(100)
        self.ui.horizontalSlider_3.setValue(100)

    def img_flip(self, h_flip=False, v_flip=False, do_paint=True):
        if len(self.imgs) and self.cv2_img_changed is not None:
            if h_flip:
                self.cv2_img_changed = cv2.flip(self.cv2_img_changed, 1)
            if v_flip:
                self.cv2_img_changed = cv2.flip(self.cv2_img_changed, 0)

            if do_paint:
                self.center_img.paint_img(array_to_qimg(self.cv2_img_changed),
                                          re_center=False, img_info_update=False)

    def img_jump(self, i=None):
        if i:
            index = i
        else:
            value = self.ui.jump_to.spinBox.value()
            value = max(1, min(self.img_num, value))
            self.ui.jump_to.spinBox.setValue(value)
            index = value - 1

        if index < self.__cur_i:
            self.scan_img(last=True, count=self.__cur_i - index, from_jump=True)

        elif index > self.__cur_i:
            self.scan_img(next=True, count=index - self.__cur_i, from_jump=True)

    def img_pil_contrast(self):
        self.ui.horizontalSlider.setValue(0)
        self.ui.horizontalSlider_2.setValue(100)

        value = self.ui.horizontalSlider_3.value() / 100
        self.ui.label_26.setText(str(value))

        if len(self.imgs):
            img = Image.fromarray(self.cv2_img)
            contrast_enhancer = ImageEnhance.Contrast(img)
            contrast_img = contrast_enhancer.enhance(value)
            self.cv2_img_changed = np.array(contrast_img)
            self.center_img.paint_img(array_to_qimg(self.cv2_img_changed),
                                      re_center=False, img_info_update=False)

    def img_rotate(self, do_paint=True):
        if len(self.imgs) and self.cv2_img_changed is not None:
            old_degree = int(self.ui.pushButton_81.text().strip().removesuffix('°'))
            if do_paint:
                self.cv2_img_changed = cv2.rotate(self.cv2_img_changed, cv2.ROTATE_90_CLOCKWISE)
                new_degree = f' {(old_degree + 90) % 360}°'
                self.ui.pushButton_81.setText(new_degree)
                self.ui.pushButton_81.setChecked(new_degree != ' 0°')
                self.center_img.paint_img(array_to_qimg(self.cv2_img_changed),
                                          re_center=False, img_info_update=False)
            else:
                for i in range(old_degree // 90):
                    self.cv2_img_changed = cv2.rotate(self.cv2_img_changed, cv2.ROTATE_90_CLOCKWISE)

    def img_size_info_update(self, wh: tuple):
        ori_h, ori_w = self.cv2_img.shape[:2]
        text = self.tr(f'宽: {ori_w}, 高: {ori_h}')
        scale = int(round(wh[0] / ori_w * 100))
        text += f' ({wh[0]}, {wh[1]}, {scale}%)'
        self.ui.label_size_info.setText(text)

    def img_time_info_update(self, img_path):
        c_time, m_time = get_file_cmtime(img_path)
        self.ui.label_time_info.setText(self.tr(f'创建: {c_time}, 修改: {m_time}'))

    def img_xy_color_update(self, info):
        x, y, r, g, b = info
        self.ui.label_xyrgb.setText(f'X: {x}, Y: {y} <br>'  # &nbsp; 加入空格
                                    f'<font color=red> R: {r}, </font>'
                                    f'<font color=green> G: {g}, </font>'
                                    f'<font color=blue> B: {b} </font>')

    def img_search(self):
        text = self.ui.lineEdit_search.text()
        for i, img in enumerate(self.imgs):
            if text in img:
                self.img_jump(i)
                self.ui.setFocus()
                return

        QMB.information(self.ui, self.tr('无搜索结果'), self.tr('未找到相关图片。'))
        self.ui.setFocus()

    def init_widgets_wrt_task(self):
        self.ui.checkBox_one_label.setChecked(self.task_cfg['one_file'])
        self.ui.checkBox_separate_label.setChecked(self.task_cfg['separate_file'])
        self.ui.textBrowser_task_desc.setText(self.task_cfg['task_desc'])
        self.ui.img_cate_buttons.init_buttons(self.task_cfg['img_classes'])
        self.ui.img_tag_buttons.init_buttons(self.task_cfg['img_tags'])
        self.ui.obj_cate_buttons.init_buttons(self.task_cfg['obj_classes'])
        if self.ui.obj_cate_buttons.names():
            self.ui.pushButton_waiting_cate.set_activated(True)
        self.ui.obj_tag_buttons.init_buttons(self.task_cfg['obj_tags'])
        if self.ui.obj_tag_buttons.names():
            self.ui.pushButton_waiting_tag.set_activated(True)
        self.ui.lineEdit_version.setText(self.task_cfg['version_head'])

    def init_variables(self):  # 程序运行后仅初始化一次的变量
        self.shape_combo_offset = QPoint(0, 0)
        self.scan_delay = 0

    def load_one_file_dict(self):
        if not self.OneFileLabel:
            return True

        json_path = f'{self.get_root("version")}/labels.json'

        if osp.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.label_file_dict = json.load(f)
            except:
                QMB.critical(self.ui, self.tr('文件错误'), self.tr('"labels.json"读取失败，请检查文件！'))
                return

            record_imgs = sorted(list(self.label_file_dict['labels'].keys()))
            self_imgs = sorted([aa.split('/')[-1] for aa in self.imgs])

            miss_list = []
            for one in record_imgs:
                if one not in self_imgs:
                    miss_list.append(one)

            if len(miss_list) > 0:
                choice = QMB.question(self.ui, self.tr('图片列表不匹配'),
                                      self.tr('{}条标注记录未找到对应的"原图"，删除这些记录吗?').format(len(miss_list)))
                if choice == QMB.Yes:
                    for one in miss_list:
                        self.label_file_dict['labels'].pop(one)
        else:
            self.label_file_dict = {'task': self.task, 'labels': {}}

        return True

    def lock_shape(self):
        cur_item = self.ui.obj_list.currentItem()
        if self.action_lock_shape.text() == self.tr('锁定标注'):
            item = self.ui.obj_list.has_locked_shape()
            if item:
                self.ui.obj_list.set_shape_unlocked(item)

            self.ui.obj_list.set_shape_locked(cur_item)
            self.center_img.set_shape_locked(True)
        else:
            self.ui.obj_list.set_shape_unlocked(cur_item)
            self.center_img.set_shape_locked(False)

        self.ui.setFocus()

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
        # self.save_one_file_json(check_version=False)

        text = text.strip()
        if text:
            if len(self.sys_error_text) == 0:
                self.sys_error_text.append('\n' + f'{get_datetime()} ' + '-' * 50 + '\n')

            if text != '^':
                self.sys_error_text.append(text)

            if self.sys_error_text[-2].startswith(':'):
                show_info = ''.join(self.sys_error_text) + '\n'
                QMB.warning(self.ui, self.tr('系统错误'),
                            self.tr('<font color=red>{}</font><br>请反馈给开发者。').format(show_info))
                with open(f'log/log_{self.log_created_time}.txt', 'a+', encoding='utf-8') as f:
                    f.writelines(show_info)

                self.sys_error_text = []

    def move_to_new_folder(self):
        path = self.file_select_dlg.getExistingDirectory(self.ui, self.tr('选择文件夹'))
        if path:
            self.del_img(path)

    def modify_obj_list_start(self):
        if self.ui.obj_list.edit_button.isChecked():
            self.LabelUiCallByMo = True

    def modify_obj_list_end(self, text):
        i = self.ui.obj_list.currentRow()
        item = self.ui.class_list.findItems(text, Qt.MatchExactly)
        if len(item):
            name = item[0].text()
            color = item[0].foreground().color()
        else:
            name = text
            item, color = self.ui.class_list.new_class_item(name)
            color = QColor(color)
            self.ui.class_list.set_look(item)
            self.ui.class_list.add_item(item)
            self.sem_class_modified_tip()

        self.center_img.modify_polygon_class(i, name, color.name())
        old_item = self.ui.obj_list.currentItem()
        old_class = old_item.text()
        old_item.setText(name)
        old_item.setForeground(color)

        row = self.ui.obj_list.currentRow()

        if self.ui.listWidget_obj_info.count():
            info_item = self.ui.listWidget_obj_info.item(row)
            new_text = info_item.text().replace(old_class, name)
            info_item.setText(new_text)
            info_item.setForeground(color)

        self.ui.setFocus()

    def new_img_window(self, path=''):
        if not path:
            path = self.file_select_dlg.getOpenFileName(self, self.tr('选择图片'),
                                                        filter=self.tr('图片类型 (*.png *.jpg *.bmp)'))[0]
        if path:
            # if (pixmap := img_path2_qpixmap(path)) is not None:
            #     window_new_img = BaseImgWindow(self, title=self.tr('图片窗口'))
            #     window_new_img.setAttribute(Qt.WA_DeleteOnClose)
            #     window_new_img.paint_img(pixmap, path)
            #     window_new_img.show()

            window_new_img = BaseImgWindow(self, title=self.tr('图片窗口'))
            window_new_img.setAttribute(Qt.WA_DeleteOnClose)
            qpixmap = img_path2_qpixmap(path)
            if qpixmap is not None:
                window_new_img.paint_img(qpixmap, path)
                window_new_img.show()

    def obj_info_show_set(self):
        self.ui.listWidget_obj_info.setVisible(self.ui.checkBox_hide_obj_info.isChecked())

    def oc_shape_info(self):
        if self.action_oc_shape_info.text() == self.tr('禁用（提高切图速度）'):
            self.clear_shape_info()
            self.action_oc_shape_info.setText(self.tr('启用（降低切图速度）'))
        elif self.action_oc_shape_info.text() == self.tr('启用（降低切图速度）'):
            self.action_oc_shape_info.setText(self.tr('禁用（提高切图速度）'))
        self.ui.setFocus()

    def paint_ann_img(self):
        if self.task_root:
            img_name = self.current_img_name()
            ann_jpg = f'{self.get_root("ann")}/{img_name[:-4]}.jpg'
            if osp.exists(ann_jpg):
                self.center_img.set_ann_painted_img(ann_jpg)

    def raise_label_mode_conflict(self):  # done----------------------------
        if self.task_root:
            # 加了QMB后，可以阻止点击QcheckBox时切换状态，原因未知
            QMB.critical(self.ui, self.tr('错误操作'), self.tr('请勿在标注途中切换标注模式，否则容易造成标注文件混乱！'))

    def random_train_val(self):
        if not self.check_warnings(['task', 'edit_mode']):
            return

        content, is_ok = self.input_dlg.getText(self.ui, self.tr('划分比例'), self.tr('请输入训练集和验证集的划分比例'),
                                                QLineEdit.Normal, text='7:1')
        if not is_ok:
            return
        content = content.replace('：', ':')
        content = [aa.strip() for aa in content.split(':')]
        if len(content) != 2:
            QMB.critical(self.ui, self.tr('格式错误'), self.tr('请输入正确的划分比例！'))
            return

        if self.SeparateLabel:
            choice = QMB.question(self.ui, self.tr('独立标注模式'),
                                  self.tr('"{0}"下的"imgs"和"labels"文件夹将被覆盖，继续吗？').format(
                                      self.get_root('tv')))
            if choice == QMB.Yes:
                if not self.OneFileLabel:
                    self.mor_vars.train_num, self.mor_vars.val_num = 0, 0

                tv_img_path, tv_label_path = f'{self.get_root("tv")}/imgs', f'{self.get_root("tv")}/labels'
                if osp.exists(tv_img_path):
                    shutil.rmtree(tv_img_path)
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

        QMB.information(self.ui, self.tr('已完成'),
                        self.tr('共划分{}张图片至训练集，{}张图片至验证集。').format(t_num, v_num))

    def remove_redu_files(self, files: list, title: str, text: str):
        choice = QMB.question(self.ui, title, text)
        if choice == QMB.Yes:
            for one in files:
                file_remove(one)

            QMB.information(self.ui, '清理完成', f'清理完成，共清理{len(files)}个文件。')
            return True
        return False

    def reset_init_variables(self):  # 在程序运行时或打开新的任务时需要重置的变量
        self.task_root = ''  # 图片根目录
        self.task = ''
        self.__cur_i = 0
        self.imgs = []
        self.img_num = 0
        self.mor_vars.train_num, self.mor_vars.val_num = 0, 0
        self.bookmark_list = []
        self.bottom_img_text = ''
        self.cv2_img = None
        self.cv2_img_changed = None
        self.label_file_dict = {}
        self.LookingAll = True
        self.looking_classes = []
        self.log_created_time = get_datetime().split(' ')[0]
        self.sys_error_text = []

    def save_ann_img(self):
        folder = f'{self.get_root("ann")}'
        os.makedirs(folder, exist_ok=True)
        img = self.center_img.get_ann_img()
        img_array = qimage_to_array(img)
        img_name = self.current_img_name()[:-4]
        save_path = f'{folder}/{img_name}.jpg'
        cv2.imencode('.jpg', img_array.astype('uint8'))[1].tofile(save_path)
        self.window_ann_saved.show(self.tr('图片保存于：{}。').format(save_path))

    def save_label(self):
        img_path = self.imgs[self.__cur_i]
        if img_path == 'images/图片已删除.png':
            return

        img_w, img_h = QPixmap(img_path).size().toTuple()
        img_name = img_path.split('/')[-1]
        tv = self.current_tv()

        shape_json = self.center_img.get_tuple_shapes()

        # if self.ui.pushButton_bg.objectName() == 'bg':
        #     assert not shape_json, 'shape_json should be empty when label is bg!'
        #     shape_json = ['bg']

        one_label = {'img_height': img_h, 'img_width': img_w, 'train_val': tv, 'img_classes': '',
                     'img_tags': '', 'object_num': len(shape_json), 'objects': shape_json}

        if self.OneFileLabel:
            if shape_json:
                self.label_file_dict['labels'][img_name] = one_label
            else:
                if self.label_file_dict['labels'].get(img_name):
                    self.label_file_dict['labels'].pop(img_name)

        if self.SeparateLabel:
            label_path = f'{self.get_root("separate")}'
            os.makedirs(label_path, exist_ok=True)

            json_name = f'{img_name[:-4]}.json'
            json_path = f'{label_path}/{json_name}'
            tv_img = f'{self.get_root("tv")}/imgs/{tv}/{img_name}'
            tv_json = f'{self.get_root("tv")}/labels/{tv}/{json_name}'

            if shape_json:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(one_label, f, sort_keys=False, ensure_ascii=False, indent=4)
                if osp.exists(tv_json):
                    with open(tv_json, 'w', encoding='utf-8') as f:
                        json.dump(one_label, f, sort_keys=False, ensure_ascii=False, indent=4)

                # if self.WorkMode == self.AllModes[2]:
                #     if shape_json == ['bg']:
                #         shape_json = []
                #
                #     seg_class_names = INS_all_classes.classes()
                #     seg_mask = get_seg_mask(seg_class_names, shape_json, img_h, img_w)
                #     if seg_mask is not None:
                #         cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(png_path)
                #         if osp.exists(tv_png):
                #             cv2.imencode('.png', seg_mask.astype('uint8'))[1].tofile(tv_png)

            else:  # 若标注为空，则在训练集&验证集里剔除
                if osp.exists(tv_img):
                    if tv == 'train':
                        self.mor_vars.train_num -= 1
                    elif tv == 'val':
                        self.mor_vars.val_num -= 1

                file_remove([tv_img, json_path, tv_json])

    def save_one_file_json(self, check_version=True):
        if self.ui.radioButton_write.isChecked() and self.OneFileLabel and self.label_file_dict:
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
                self.label_file_dict['classes'] = INS_all_classes.classes()
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(self.label_file_dict, f, sort_keys=False, ensure_ascii=False, indent=4)

                self.ui.label_path.setText(self.tr('"{}"已保存。').format(json_path))
                self.log_info('"labels.json" has been saved.')

    def scan_img(self, last=False, next=False, count=1, from_jump=False):
        scan_start = time.time()

        if not self.task_root:
            return
        if self.__cur_i < 0 or self.__cur_i > self.img_num:
            QMB.critical(self.ui, self.tr('索引超限'), self.tr('当前图片索引为{}，超出限制！').format(self.__cur_i))
            return

        # if not from_jump:
        #     part_scan = self.ui.comboBox.currentText()
        #     # 只看部分类别功能
        #     if self.WorkMode in self.AllModes[(2, 3, 4)]:
        #         self.LookingAll = self.ui.class_list.looking_all()
        #         self.looking_classes = self.ui.class_list.looking_classes()
        #         if not self.LookingAll:
        #             if part_scan == self.tr('浏览未标注'):
        #                 QMB.critical(self.ui, self.tr('功能冲突'),
        #                              self.tr('浏览部分类别的功能和浏览未标注的功能冲突，请先关闭其中一项。'))
        #                 return
        #
        #             count = self.scan_part_classes(last=last, next=next)
        #
        #     # 只看带标签图片功能  todo-------------------------
        #     if part_scan == self.tr('按标签浏览'):
        #         count = self.scan_pinned_imgs(last=last, next=next)
        #
        #     if part_scan == self.tr('浏览未标注'):
        #         count = self.scan_unlabeled_imgs(last=last, next=next)
        #
        #     if part_scan == self.tr('浏览未划分'):
        #         count = self.scan_train_val_imgs(split='none', last=last, next=next)
        #
        #     if part_scan == self.tr('浏览训练集'):
        #         count = self.scan_train_val_imgs(split='train', last=last, next=next)
        #
        #     if part_scan == self.tr('浏览验证集'):
        #         count = self.scan_train_val_imgs(split='val', last=last, next=next)

        if self.ui.radioButton_write.isChecked():
            pass
            # self.save_label()

        if last and 0 < self.__cur_i <= self.img_num:
            for _ in range(count):
                self.flow_move(left=True)
                self.__cur_i -= 1

        elif next and self.__cur_i < self.img_num - 1:
            for _ in range(count):
                self.flow_move(right=True)
                self.__cur_i += 1

        if 0 <= self.__cur_i < self.img_num:
            # self.center_img.set_shape_locked(False)
            self.show_img_status_info()
            # self.shape_to_img()

            # self.set_tv_label()
            # if self.WorkMode in self.AllModes[(2, 4)]:
            #     self.go_next_flow_window()

            scan_time = (time.time() - scan_start) * 1000
            if scan_time < self.scan_delay:
                time.sleep((self.scan_delay - scan_time) / 1000)

    def scan_unlabeled_imgs(self, last=False, next=False):
        result = True
        i = self.__cur_i
        while 0 <= i <= self.img_num - 1:
            if last:
                i -= 1
            elif next:
                i += 1

            if i == -1 or i == self.img_num:
                break

            if '图片已删除' in self.imgs[i]:
                continue

            if self.OneFileLabel:
                result = self.label_file_dict['labels'].get(self.imgs[i].split('/')[-1])
            elif self.SeparateLabel:
                json_path = self.get_separate_label(self.imgs[i], 'json')
                result = osp.exists(json_path)

            if not result:
                break

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.__cur_i)
        return count

    def scan_part_classes(self, last=False, next=False):  # 只浏览部分类别的标注的功能
        i = self.__cur_i
        while 0 <= i <= self.img_num - 1:
            if last:
                i -= 1
            elif next:
                i += 1

            if i == -1 or i == self.img_num:
                break

            if self.has_looking_classes(self.imgs[i]):
                count = abs(i - self.__cur_i)
                return count

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.__cur_i)
        return count

    def scan_pinned_imgs(self, last=False, next=False):
        i = self.__cur_i
        while 0 <= i <= self.img_num - 1:
            if last:
                i -= 1
            elif next:
                i += 1

            if i == -1 or i == self.img_num:
                break

            img_name = self.imgs[i].split('/')[-1]
            if img_name in self.pinned_imgs:
                count = abs(i - self.__cur_i)
                return count

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.__cur_i)
        return count

    def scan_train_val_imgs(self, split, last=False, next=False):
        i = self.__cur_i
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
                        count = abs(i - self.__cur_i)
                        return count
                else:
                    count = abs(i - self.__cur_i)
                    return count

        i = min(max(0, i), self.img_num - 1)
        count = abs(i - self.__cur_i)
        return count

    def select_cate_tag_after(self):
        if self.LabelUiCallByMo:
            self.modify_obj_list_end(text)
            self.LabelUiCallByMo = False
        else:
            if self.ui.radioButton_write.isChecked():
                obj_done, tag_done = False, False
                assert self.ui.obj_cate_buttons.isVisible(), 'obj_cate_buttons must be visible after one shape drawed.'
                if self.ui.pushButton_waiting_cate.has_confirmed():
                    obj_done = True
                    self.ui.obj_cate_buttons.set_obj_select_stat(before_select=False)
                if ((self.ui.obj_tag_buttons.isVisible() and self.ui.pushButton_waiting_tag.has_confirmed())
                        or not self.ui.obj_tag_buttons.isVisible()):
                    tag_done = True
                    self.ui.obj_tag_buttons.set_obj_select_stat(before_select=False)

                if obj_done and tag_done:
                    cates = self.ui.obj_cate_buttons.selected_buttons()
                    color = self.ui.obj_cate_buttons.color(cates[0])
                    self.ui.obj_list.add_item(', '.join(cates), color)
                    tags = self.ui.obj_tag_buttons.selected_buttons()
                    self.center_img.save_one_shape(cates, tags, color)
                    self.ui.comboBox_2.setDisabled(False)
                    # self.show_shape_info(self.center_img.get_one_polygon(-1))

    def select_cate_tag_before(self):
        self.ui.comboBox_2.setDisabled(True)

        self.ui.obj_cate_buttons.set_obj_select_stat(before_select=True)
        self.ui.obj_tag_buttons.set_obj_select_stat(before_select=True)
        if not self.ui.obj_cate_buttons.isVisible():
            self.ui.pushButton_obj_cate.click()

    def sem_class_modified_tip(self):
        if self.SeparateLabel and self.ui.radioButton_write.isChecked():
            if not self.window_sem_class_changed.DontShowAgain:
                self.window_sem_class_changed.show(self.tr('类别数量发生变化，用于语义分割任务的PNG标注可能需要更新。'))

    def send_auto_infer_imgs(self, infer_all):
        imgs = self.imgs if infer_all else [self.imgs[self.__cur_i]]
        self.window_auto_infer.receive_imgs(imgs)

    def set_action_disabled(self):
        pass
        # stat = not self.ui.checkBox_shape_edit.isChecked()
        # self.action_modify_one_class_jsons.setDisabled(stat)
        # self.action_del_one_class_jsons.setDisabled(stat)
        # self.action_modify_one_shape_class.setDisabled(stat)
        # self.action_delete_one_shape.setDisabled(stat)
        # self.action_delete_all.setDisabled(stat)
        # self.action_lock_shape.setDisabled(stat)

    def set_hide_cross(self):  # done ---------------------------------------
        hide = not self.ui.checkBox_hide_cross.isChecked()
        self.center_img.set_hide_cross(hide)
        self.ui.pushButton_cross_color.setDisabled(hide)

    def set_info_widget_selected(self):
        if self.ui.listWidget_obj_info.count():
            row = self.ui.obj_list.currentRow()
            if self.ui.listWidget_obj_info.item(row):
                self.ui.listWidget_obj_info.item(row).setSelected(True)

    def set_language(self, language):  # done-----------------------
        # 不重启也可以实时翻译，但是这个问题无法解决，QAction需要在changeEvent里逐个添加翻译代码
        # https://forum.qt.io/topic/141742/how-to-translate-text-with-quiloader

        app = QApplication.instance()
        if language == 'CN' and self.language == 'EN':
            choice = QMB.question(self.ui, 'Switch to Chinese',
                                  'The app is going to restart, please ensure all work is saved, continue?')
            if choice == QMB.Yes:
                self.language = 'CN'
                app.exit(99)
        elif language == 'EN' and self.language == 'CN':
            choice = QMB.question(self.ui, '切换为英文', '软件将重新打开，请确保所有工作已保存，继续吗？')
            if choice == QMB.Yes:
                self.language = 'EN'
                app.exit(99)

    def set_one_file_label(self, by_click=False):
        if by_click:
            self.OneFileLabel = self.ui.checkBox_one_label.isChecked()
            if not self.SeparateLabel and not self.OneFileLabel:
                QMB.warning(self.ui, self.tr('未选择标注模式'), self.tr('请选择至少一种标注模式！'))
                self.ui.checkBox_one_label.setChecked(True)

            self.task_cfg['one_file'] = self.OneFileLabel
            self.task_cfg_export()

    def set_edit_mode(self):
        # if self.OneFileLabel:
        #     if self.ui.radioButton_read.isChecked():
        #         self.thread_auto_save.terminate()
        #     else:
        #         self.thread_auto_save.start()
        # else:
        #     self.thread_auto_save.terminate()

        stat_flags.HHL_Edit_Mode = self.ui.radioButton_write.isChecked()
        if not stat_flags.HHL_Edit_Mode:
            self.ui.obj_list.edit_button.setChecked(stat_flags.HHL_Edit_Mode)

        self.ui.obj_list.edit_button.setDisabled(not stat_flags.HHL_Edit_Mode)
        self.ui.img_cate_buttons.reset_img_select_enable(stat_flags.HHL_Edit_Mode)
        self.ui.img_tag_buttons.reset_img_select_enable(stat_flags.HHL_Edit_Mode)

    def set_scan_delay(self):
        delay, is_ok = self.input_dlg.getInt(self.ui, self.tr('切图延时'), self.tr('单位：ms'),
                                             self.scan_delay, 0, 9999, 100)
        if is_ok:
            self.scan_delay = delay

    def set_scan_mode(self):
        self.ui.setFocus()

    def set_sem_bg(self):
        if not self.ui.obj_cate_buttons.has_button('as_sem_bg'):
            self.ui.obj_cate_buttons.add_button('as_sem_bg')

        button = self.ui.obj_cate_buttons.get_button('as_sem_bg')
        if button:
            button.set_as_default()

    def set_separate_label(self, by_click=False):
        if by_click:
            self.SeparateLabel = self.ui.checkBox_separate_label.isChecked()
            if not self.SeparateLabel and not self.OneFileLabel:
                QMB.warning(self.ui, self.tr('未选择标注模式'), self.tr('请选择至少一种标注模式！'))
                self.ui.checkBox_one_label.setChecked(True)

            self.task_cfg['separate_file'] = self.SeparateLabel
            self.task_cfg_export()

    def set_shape_edit_mode(self):
        stat = self.ui.obj_list.edit_button.isChecked()
        self.center_img.set_tool_mode(shape_edit=stat)
        self.set_action_disabled()

    def set_tool_mode(self):
        self.center_img.clear_scaled_img(to_undo=False)
        self.center_img.clear_all_polygons()
        draw = self.task_root and self.ui.toolBox.currentIndex() == 0
        shape_edit = draw and self.ui.obj_list.edit_button.isChecked()
        ann = self.task_root and self.ui.toolBox.currentIndex() == 1
        self.center_img.set_tool_mode(draw, shape_edit, ann)

        if self.ui.toolBox.currentIndex() == 1:
            self.paint_ann_img()

    def set_tv_label(self):
        img_name = self.current_img_name()
        if self.OneFileLabel:
            if self.label_file_dict['labels'].get(img_name):
                tv = self.label_file_dict['labels'][img_name]['tv']
                if tv == 'train':
                    self.ui.label_train_val.set_train()
                elif tv == 'val':
                    self.ui.label_train_val.set_val()
                else:
                    self.ui.label_train_val.set_none()
            else:
                self.ui.label_train_val.set_none()
        elif self.SeparateLabel:
            if osp.exists(f'{self.get_root("tv")}/imgs/train/{img_name}'):
                self.ui.label_train_val.set_train()
            elif osp.exists(f'{self.get_root("tv")}/imgs/val/{img_name}'):
                self.ui.label_train_val.set_val()
            else:
                self.ui.label_train_val.set_none()

    def shape_to_img(self):
        # self.clear_shape_info()
        self.center_img.clear_all_polygons()
        self.ui.obj_list.clear()

        img_path = self.imgs[self.__cur_i]
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
            if cate in INS_all_classes.classes():
                item = self.ui.class_list.findItems(cate, Qt.MatchExactly)[0]
                one['qcolor'] = item.foreground().color().name()

            item, _ = self.ui.class_list.new_class_item(cate, color=one['qcolor'])
            self.ui.obj_list.add_item(item.clone())
            self.show_shape_info(one)

            if cate not in INS_all_classes.classes():
                self.ui.class_list.set_look(item)
                self.ui.class_list.add_item(item)
                self.sem_class_modified_tip()

        # polygons的嵌套的数据结构导致数据容易发生原位修改，哪怕使用了.get()方法和函数传参也一样，具体原理未知
        self.center_img.prepare_polygons(deepcopy(polygons), img_h, img_w)

    def shape_type_change(self):
        text = self.ui.comboBox_2.currentText()
        self.center_img.change_shape_type(text)

        if text == self.tr('组合'):
            pos = self.ui.line_9.mapToGlobal(QPoint(0, 0)) + QPoint(0, 10)
            self.shape_combo_offset = pos - self.pos()
            self.window_shape_combo.show_at(pos)

    def shape_type_reset(self):
        if self.ui.comboBox_2.currentIndex() == 4:
            self.ui.comboBox_2.setCurrentIndex(0)

    def show_bookmark(self):
        if 0 <= self.__cur_i < self.img_num:
            if self.__cur_i in self.bookmark_list:
                self.bookmark_list.remove(self.__cur_i)
            else:
                self.bookmark_list.append(self.__cur_i)
        self.ui.graphicsView.show_bookmark()

    def show_class_statistic(self):
        self.thread_cs = ClassStatistics(self.WorkMode, self.img_num, INS_all_classes.classes(), self.OneFileLabel,
                                         deepcopy(self.label_file_dict), self.SeparateLabel, self, self.language)
        self.thread_cs.start()
        self.show_waiting_label()

    def show_class_statistic_done(self, info):
        self.waiting_label.stop()
        self.waiting_label.close()
        self.window_class_stat = ClassStatWidget(add_info=info, version_path=self.get_root('version'))
        self.window_class_stat.show()

    def show_img_status_info(self):
        if (path := self.imgs[self.__cur_i]) == 'images/图片已删除.png':
            self.ui.label_path.setText(self.tr('图片已删除。'))
        else:
            if (img_array := get_rotated_img_array(path)) is None:
                return

            self.cv2_img = img_array
            self.cv2_img_changed = self.cv2_img

            br_v = self.ui.horizontalSlider.value()
            co_v = self.ui.horizontalSlider_2.value() / 100
            pil_v = self.ui.horizontalSlider_3.value() / 100

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

            h_flip, v_flip = self.ui.pushButton_82.isChecked(), self.ui.pushButton_83.isChecked()
            self.img_flip(h_flip=h_flip, v_flip=v_flip, do_paint=False)
            self.img_rotate(do_paint=False)
            self.center_img.paint_img(array_to_qimg(self.cv2_img_changed), path)

            self.ui.label_index.setText(f'<font color=violet>{self.__cur_i + 1}</font>/{self.img_num}')
            self.bottom_img_text = path
            self.ui.label_path.setTextFormat(Qt.PlainText)
            self.ui.label_path.setText(uniform_path(self.bottom_img_text))
            # self.paint_ann_img()  todo: 何时该画ann_img

    def show_menu(self, menu):  # 在鼠标位置显示菜单
        if menu.title() == 'label_list_menu':
            item = self.ui.obj_list.currentItem()
            if item is not None:
                if item.icon().cacheKey() == 0:
                    self.action_lock_shape.setText(self.tr('锁定标注'))
                else:
                    self.action_lock_shape.setText(self.tr('取消锁定'))

        menu.exec(QCursor.pos())

    def show_shape_info(self, polygon):
        if self.action_oc_shape_info.text() == self.tr('启用（降低切图速度）'):
            return

        item = QListWidgetItem()
        item.setText(self.get_info_text(polygon))
        color = QColor(polygon['qcolor'])
        item.setForeground(color)
        self.ui.listWidget_obj_info.addItem(item)

    def show_task_window(self):
        self.window_build_task.show(self.image_folder)

    def show_waiting_label(self):
        self.waiting_label = WaitingLabel(self, self.tr('等待中'))
        self.waiting_label.show_at(self.frameGeometry())

    def task_cfg_export(self):
        if self.task:
            with open(f'{self.task_root}/task_cfg.json', 'w', encoding='utf-8') as f:
                json.dump(self.task_cfg, f, sort_keys=False, ensure_ascii=False, indent=4)

    def task_cfg_import(self):
        if not self.check_warnings('task'):
            return

        if osp.exists(f'{self.task_root}/task_cfg.json'):
            with open(f'{self.task_root}/task_cfg.json', 'r', encoding='utf-8') as f:
                self.task_cfg = json.load(f)

            self.init_widgets_wrt_task()

    def task_desc_edit(self, text='', from_build=False):  # 记录任务描述，self.task_cfg['task_desc']
        if from_build:  # 如果创建新任务，则需要确保会保存一个task_cfg.json
            self.ui.textBrowser_task_desc.setText(text)
            self.task_cfg['task_desc'] = text
            self.task_cfg_export()
        else:
            if text != self.task_cfg['task_desc']:
                self.task_cfg['task_desc'] = text
                self.task_cfg_export()

    def task_open(self):
        file_path = self.file_select_dlg.getExistingDirectory(self.ui, self.tr('选择任务'))
        if file_path:
            imgs_path = f'{file_path}/{self.image_folder}'
            if not osp.exists(imgs_path):
                QMB.warning(self, self.tr('未找到"原图"'),
                            self.tr('未找到"{}"文件夹，请新建任务。').format(imgs_path))
                return

        self.task_opened(file_path)

    def task_opened(self, file_path):
        if os.path.isdir(file_path):
            # if self.ui.lineEdit.text():
            #     self.save_one_file_json()

            self.reset_init_variables()
            self.task_root = file_path
            self.ui.lineEdit.setText(self.task_root)
            self.task = self.task_root.split('/')[-1]

            self.graphics_reset()
            self.task_cfg_import()

            self.imgs = glob_imgs(f'{self.task_root}/{self.image_folder}')
            self.img_num = len(self.imgs)

            if not self.img_num:
                return

            self.ui.listWidget_imgs_flow.add_img(self.imgs[self.__cur_i])  # 打开任务后显示第一个流水子图
            self.show_img_status_info()

            self.set_tool_mode()
            # self.clear_shape_info()

            # if self.load_one_file_dict():
            #     self.show_label_to_ui()
            #     self.set_tv_label()
            #     self.get_tv_num()
            #
            # if self.OneFileLabel:
            #     self.thread_auto_save.start()

            try:  # 可能没装Git客户端
                self.repo = git.Repo.init(self.task_root)
            except:
                self.repo = None

            self.log_info(f'task: {self.task}, one file: {self.OneFileLabel}, separate file: {self.SeparateLabel}')

    def update_button_num(self, info):
        name, num = info
        if name == 'img_cate_buttons':
            self.ui.pushButton_img_cate.setText(self.tr('图片类别') + f' ({num})')
        elif name == 'img_tag_buttons':
            self.ui.pushButton_img_tag.setText(self.tr('图片标签') + f' ({num})')
        elif name == 'obj_cate_buttons':
            self.ui.pushButton_obj_cate.setText(self.tr('目标类别') + f' ({num})')
        elif name == 'obj_tag_buttons':
            self.ui.pushButton_obj_tag.setText(self.tr('目标标签') + f' ({num})')

    def update_sem_pngs(self):
        classes = INS_all_classes.classes()
        if not classes:
            QMB.warning(None, self.tr('类别数量为0'), self.tr('当前类别数量为0，请先加载类别。'))
            return

        self.thread_usp = UpdateSemanticPngs(self.imgs, classes, self)
        self.thread_usp.start()
        self.window_usp_progress = ProgressWindow(title=self.tr('PNG更新'), text_prefix=self.tr('更新PNG标注中：'))
        self.window_usp_progress.show()

    def update_shape_info_text(self, i):
        pass
        # if self.action_oc_shape_info.text() == self.tr('启用（降低切图速度）'):
        #     return
        #
        # text = self.get_info_text(self.center_img.get_one_polygon(i))
        # self.ui.listWidget_obj_info.item(i).setText(text)

    def version_add(self):
        # x, y = self.ui.line_9.pos().toTuple()
        # x = x + self.ui.line_9.width() - 70
        # y = y - 10
        #
        # self.bu.show_at(self.ui.line_9.parent().mapToGlobal(QPoint(x, y)))
        # return

        if not self.check_warnings(['task', 'git']):
            return

        if 'working tree clean' in self.repo.git.status():
            QMB.information(self, self.tr('无变化'), self.tr('没有文件发生变化，无需记录。'))
            return

        name, is_ok = self.input_dlg.getText(self, self.tr('版本名称'), self.tr('请输入记录的版本名称。'))

        if is_ok:
            if 'No commits yet' not in self.repo.git.status():
                if name in self.repo.git.log('--pretty=format:%s').split('\n'):
                    QMB.information(self, self.tr('版本名称'), self.tr('当前版本名称已存在，请更换。'))
                    return

            files = uniform_path(glob.glob(f'{self.task_root}/*'))
            existed_files = sorted([one.split('/')[-1] for one in files])

            # repo.index.add(['new.txt'])
            # repo.index.remove(['old.txt'])
            # repo.index.commit('this is a test')

            for one in existed_files:
                if one in self.task_cfg['tracked_files']:
                    self.repo.git.add(one)
                else:
                    if osp.isdir(f'{self.task_root}/{one}'):
                        one = f'{one}/*'

                    try:  # 删除不在repo.untracked_files里的文件会报错，利用try-except直接跳过
                        self.repo.git.rm('-r', '--cached', one)
                    except:
                        pass

            if 'nothing added to commit but' in self.repo.git.status():
                QMB.information(self, self.tr('文件未修改'), self.tr('没有追踪中的文件发生修改，无需记录。'))
            else:
                self.ui.lineEdit_version.setText(name)
                self.task_cfg['version_head'] = name  # head变化，重新导出一次cfg
                self.task_cfg_export()

                if 'task_cfg.json' in self.task_cfg['tracked_files']:
                    self.repo.git.add(f'{self.task_root}/task_cfg.json')

                self.repo.git.commit('-m', name)
                log = self.repo.git.log('--pretty=format:%cs, %s').split('\n')[0]
                QMB.information(self, self.tr('已记录'), self.tr('已记录') + ': ' + log)

    def version_change(self):
        if self.check_warnings(['task', 'git']):
            if self.dialog_version_change is None:
                self.dialog_version_change = SingleSelectList(self.ui, self.tr('版本选择'),
                                                              self.tr('请选择需要切换的版本'))
                self.dialog_version_change.resize(300, 350)

            stat_dict = {}
            if self.repo is not None and 'No commits yet' not in self.repo.git.status():
                all_commits = [one for one in self.repo.git.reflog().split('\n') if 'reset: moving' not in one]
                hash_ids = [one[:7] for one in all_commits]
                commit_names = [one.split('commit: ')[-1] for one in all_commits]
                commit_names[-1] = commit_names[-1].split('commit (initial): ')[-1]
                commit_dates = [self.repo.commit(one).authored_datetime.strftime('%Y-%m-%d-%H') for one in hash_ids]
                assert len(hash_ids) == len(commit_names), 'Bug, len(hash_ids) != len(commit_names)!'

                head_name = self.repo.head.commit.message.strip()
                for i in range(len(commit_names)):
                    text = f'{commit_dates[i]}, {commit_names[i]}'
                    if head_name == commit_names[i]:
                        stat_dict[text] = True
                    else:
                        stat_dict[text] = False

            self.dialog_version_change.show_with(stat_dict)  # 会在此阻塞住

            if stat_dict and self.dialog_version_change.CloseByOK:
                dst_name = ''
                for name, stat in self.dialog_version_change.select_stat.items():
                    if stat:
                        dst_name = name
                        break

                for i, name in enumerate(commit_names):
                    if name in dst_name:
                        self.repo.git.reset('--hard', hash_ids[i][:16])
                        self.task_opened(self.ui.lineEdit.text())
                        QMB.information(self, self.tr('已切换'), self.tr(f'已切换至：{name}'))
                        break

    def version_tracked_files_set(self):
        if self.check_warnings(['task', 'git']):
            if self.dialog_tracked_files is None:
                self.dialog_tracked_files = BaseSelectList(self.ui, self.tr('配置记录文件'),
                                                           self.tr('请选择需要记录的文件'))

            files = uniform_path(glob.glob(f'{self.task_root}/*'))
            existed_files = sorted([one.split('/')[-1] for one in files])

            stat_dict = {}
            tracked_files = self.task_cfg['tracked_files']

            for one in tracked_files:
                if one in existed_files:
                    stat_dict[one] = True

            for one in existed_files:
                if one not in tracked_files:
                    stat_dict[one] = False

            self.dialog_tracked_files.show_with(stat_dict)  # 会在此阻塞住

            if self.dialog_tracked_files.CloseByOK:
                new_tracked_files = []
                for name, stat in self.dialog_tracked_files.select_stat.items():
                    if stat:
                        new_tracked_files.append(name)

                self.task_cfg['tracked_files'] = new_tracked_files
                self.task_cfg_export()

# todo: 新架构-----------------------------------------
# todo：多分类设置  独占组
# todo: 7. 类别统计因此也要重做，用QtableWidget
# todo: 10. 程序配置记录文件
# todo: 11. 图库统计,检查图库,检查训练集，验证集合并为一个功能（可导出一份统计记录）
# todo: cvat式的标注修改
# todo:  标注批量删除功能
# todo: 标注的快速复制 粘贴功能，带快捷键
# todo: auto inference 全功能  支持 ONNX、openvino、（opencv接口？ 自写接口？）
# todo: shape的交集、差集  环形支持多形状组合以及多孔洞环形
# todo: 伪标注合成全功能    金字塔融合(https://blog.csdn.net/qq_45717425/article/details/122638358)
# todo：导出coco、voc等格式的数据结构
# todo: 版本记录，切换有点慢，是否需要加入请等待窗口
# todo: 超大图片的显示需要支持吗
# todo: 新建的图片窗口 根据展示的图像尺寸  自适应大小

# todo: 像素指针根据背景自动变色
# todo: 新架构-----------------------------------------

# todo: log自动清理
# todo: 合并labels.json
# todo: 视频标注 全功能
# todo: 动画? 主要用于控件的隐藏、折叠，参考流式布局？
# todo: 摄像头 实时检测与标注？
# todo: 旋转目标检测？
# todo: QColorDialog可以使用翻译吗？
# todo: 设置Qmessagebox的字体大小

# keep update---------------------
# todo: 完善log

# 搁置-------------------
# todo: ubuntu 部分弹出窗口不在屏幕中心位置
# todo: ubuntu 按钮右键时同时弹出上层容器的右键菜单
# todo: https://forum.qt.io/topic/141742/how-to-translate-text-with-quiloader
