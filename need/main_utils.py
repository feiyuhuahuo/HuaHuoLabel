#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import sys

# 超过50行的规则、重复代码可放在这里，减轻main.py的代码行数
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction, QIcon, Qt
from need.custom_widgets import *
from need.custom_threads import *


# -----------------------------每个自定义控件都要留意其内存占用情况，留意其内存是否需要自动回收-----------------------------
# 1.使用QUiLoader加载的自定义控件，在关闭后有可能造成内存泄露的问题, 时刻注意哪些控件是非初始化、临时的、有可能多个出现的，
# 此类控件要测试在关闭后其内存释放情况。
# 2.使用lambda作为槽函数也会造成控件无法被自动垃圾回收，从而内存泄露
# https://forum.qt.io/topic/152101/memory-can-not-release-correctly-because-of-using-lambda-as-slot/12
# 3.QPixmap在图片很大时，会极其占用内存
def connect_signals(main_window):
    main_window.ui.checkBox_hide_obj_info.toggled.connect(main_window.obj_info_show_set)
    main_window.ui.checkBox_hide_cross.clicked.connect(main_window.set_hide_cross)
    main_window.ui.checkBox_one_label.pressed.connect(main_window.raise_label_mode_conflict)
    main_window.ui.checkBox_one_label.toggled.connect(lambda: main_window.set_one_file_label(by_click=True))
    main_window.ui.checkBox_separate_label.pressed.connect(main_window.raise_label_mode_conflict)
    main_window.ui.checkBox_separate_label.toggled.connect(lambda: main_window.set_separate_label(by_click=True))
    main_window.ui.checkBox_sem_bg.toggled.connect(main_window.set_sem_bg)

    main_window.ui.comboBox.currentIndexChanged.connect(main_window.set_scan_mode)
    main_window.ui.comboBox_2.currentIndexChanged.connect(main_window.shape_type_change)

    main_window.ui.horizontalSlider.valueChanged.connect(main_window.img_enhance)
    main_window.ui.horizontalSlider_2.valueChanged.connect(main_window.img_enhance)
    main_window.ui.horizontalSlider_3.valueChanged.connect(main_window.img_pil_contrast)

    main_window.ui.lineEdit_search.search_btn.clicked.connect(main_window.img_search)

    # main_window.ui.obj_list.itemSelectionChanged.connect(main_window.set_info_widget_selected)

    # main_window.ui.pushButton_35.clicked.connect(main_window.ui.graphicsView.img_area.undo)
    main_window.ui.pushButton_36.clicked.connect(main_window.save_ann_img)
    main_window.ui.pushButton_40.clicked.connect(main_window.clear_painted_img)
    main_window.ui.pushButton_81.clicked.connect(lambda: main_window.img_rotate(do_paint=True))
    main_window.ui.pushButton_82.clicked.connect(lambda: main_window.img_flip(h_flip=True, do_paint=True))
    main_window.ui.pushButton_83.clicked.connect(lambda: main_window.img_flip(v_flip=True, do_paint=True))
    main_window.ui.pushButton_84.clicked.connect(main_window.img_enhance_reset)
    main_window.ui.pushButton_add_version.clicked.connect(main_window.version_add)
    main_window.ui.pushButton_auto_infer.clicked.connect(main_window.auto_inference)
    main_window.ui.pushButton_bookmark.pressed.connect(main_window.show_bookmark)
    main_window.ui.pushButton_build_task.pressed.connect(main_window.show_task_window)
    # main_window.ui.pushButton_check_label.clicked.connect(main_window.check_dataset)
    main_window.ui.pushButton_cross_color.clicked.connect(main_window.change_cross_color)
    main_window.ui.pushButton_delay.clicked.connect(main_window.set_scan_delay)
    main_window.ui.pushButton_delete.clicked.connect(lambda: main_window.del_img(None))
    main_window.ui.pushButton_font_color.clicked.connect(main_window.change_font_color)
    main_window.ui.pushButton_generate_train.clicked.connect(main_window.generate_train)
    main_window.ui.pushButton_goto_train.clicked.connect(lambda: main_window.add_to_train_val(dst_part='train'))
    main_window.ui.pushButton_goto_val.clicked.connect(lambda: main_window.add_to_train_val(dst_part='val'))
    main_window.ui.pushButton_img_cate.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_img_tag.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_img_cate_add.clicked.connect(main_window.add_buttons)
    main_window.ui.pushButton_img_tag_add.clicked.connect(main_window.add_buttons)
    main_window.ui.pushButton_img_edit.clicked.connect(main_window.edit_img)
    main_window.ui.pushButton_img_window.clicked.connect(main_window.new_img_window)
    main_window.ui.pushButton_obj_cate.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_obj_tag.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_obj_cate_add.clicked.connect(main_window.add_buttons)
    main_window.ui.pushButton_obj_tag_add.clicked.connect(main_window.add_buttons)
    main_window.ui.pushButton_open_task.clicked.connect(main_window.task_open)
    main_window.ui.pushButton_pen_color.clicked.connect(main_window.change_pen_color)
    main_window.ui.pushButton_pen_color_2.clicked.connect(main_window.change_pen_color)
    main_window.ui.pushButton_random_split.clicked.connect(main_window.random_train_val)
    main_window.ui.pushButton_select_version.clicked.connect(main_window.version_change)
    main_window.ui.pushButton_stat.clicked.connect(main_window.show_class_statistic)
    main_window.ui.pushButton_tracked_files.clicked.connect(main_window.version_tracked_files_set)

    main_window.ui.jump_to.pushButton_jump.clicked.connect(main_window.img_jump)
    main_window.ui.scan_buttons.pushButton_last.clicked.connect(lambda: main_window.scan_img(last=True))
    main_window.ui.scan_buttons.pushButton_next.clicked.connect(lambda: main_window.scan_img(next=True))
    main_window.ui.obj_list.edit_button.toggled.connect(main_window.set_shape_edit_mode)
    # main_window.ui.pushButton_bg.pressed.connect(main_window.set_semantic_bg_when_press)

    # main_window.ui.pushButton_update_png.clicked.connect(main_window.update_sem_pngs)

    main_window.ui.radioButton_read.toggled.connect(main_window.set_edit_mode)

    main_window.ui.spinBox_thickness.spinBox.valueChanged.connect(main_window.change_pen_size)
    main_window.ui.spinBox_fontsize.spinBox.valueChanged.connect(main_window.change_font_size)
    main_window.ui.spinBox_thickness2.spinBox.valueChanged.connect(main_window.change_pen_size)

    main_window.ui.toolBox.currentChanged.connect(main_window.set_tool_mode)

    main_window.ui.graphicsView.img_area.signal_xy_color2ui.signal.connect(main_window.img_xy_color_update)
    main_window.ui.graphicsView.img_area.signal_img_time2ui.signal.connect(main_window.img_time_info_update)
    main_window.ui.graphicsView.img_area.signal_img_size2ui.signal.connect(main_window.img_size_info_update)
    sys.stderr = main_window.signal_error2app
    sys.stderr.signal.connect(main_window.log_sys_error)

    signal_auto_save.signal.connect(main_window.auto_save)
    signal_cocc_done.signal.connect(main_window.change_one_class_category_done)
    signal_docl_done.signal.connect(main_window.delete_one_class_jsons_done)
    # signal_one_collection_done.signal.connect(main_window.select_cate_tag)
    signal_button_selected_done.signal.connect(main_window.select_cate_tag_after)
    signal_shape_info_update.signal.connect(main_window.update_shape_info_text)
    signal_show_label_img.signal.connect(main_window.flow_show)
    signal_show_plain_img.signal.connect(main_window.flow_show)
    signal_stat_info.signal.connect(main_window.show_class_statistic_done)
    signal_request_imgs.signal.connect(main_window.send_auto_infer_imgs)
    signal_update_button_num.signal.connect(main_window.update_button_num)


def init_menu(main_win):
    main_win.menu_set_shape_info = QMenu(main_win)
    main_win.action_oc_shape_info = QAction(main_win.tr('禁用（提高切图速度）'), main_win)
    main_win.action_oc_shape_info.triggered.connect(main_win.oc_shape_info)
    main_win.menu_set_shape_info.addAction(main_win.action_oc_shape_info)

    main_win.ui.action_cn.triggered.connect(lambda: main_win.set_language('CN'))
    main_win.ui.action_en.triggered.connect(lambda: main_win.set_language('EN'))
    main_win.ui.action_about.triggered.connect(main_win.about_hhl)


def init_custom_widgets(main_window):
    main_window.dialog_img_edit = ImgEdit(main_window)
    main_window.window_build_task = BuildTask(main_window)
    main_window.window_shape_combo = ShapeCombo(main_window)
    main_window.pushbutton_waiting = PushButtonWaiting(main_window)
    main_window.window_sem_class_changed = CustomMessageBox('information', main_window.tr('类别列表变化'))
    main_window.window_ann_saved = CustomMessageBox('information', main_window.tr('已保存'))
    main_window.window_large_img_warn = CustomMessageBox('information', main_window.tr('图片过大'))
    main_window.widget_read_edit = ReadEditInfo()
    main_window.window_flow_label = BaseImgWindow(title=main_window.tr('标注图片'))
    main_window.window_flow_label.setWindowFlags(Qt.WindowStaysOnTopHint)
    main_window.window_flow_img = BaseImgWindow(title=main_window.tr('原始图片'))
    main_window.window_flow_img.setWindowFlags(Qt.WindowStaysOnTopHint)
    main_window.dialog_tracked_files = None
    main_window.dialog_version_change = None

    # self.window_auto_infer_progress = None
    # self.window_class_stat = None
    # self.window_usp_progress = None
    # self.window_auto_infer = None
    main_window.ui.spinBox_thickness.set_default('images/thickness.png', 1, 20, 2)
    main_window.ui.spinBox_thickness2.set_default('images/thickness.png', 1, 20, 3)
    main_window.ui.spinBox_fontsize.set_default('images/font_size.png', 1, 50, 20, padding_icon=2)


def close_sub_windows(main_window):
    main_window.window_build_task.close()
    # if main_window.window_new_img:
    #     main_window.window_new_img.close()
    main_window.window_flow_img.close()
    main_window.window_flow_label.close()
    # if main_window.window_class_stat:
    #     main_window.window_class_stat.close()
    # if main_window.window_usp_progress:
    #     main_window.window_usp_progress.close()
    # if main_window.window_auto_infer:
    #     main_window.window_auto_infer.close()
    # if main_window.window_auto_infer_progress:
    #     main_window.window_auto_infer_progress.close()


def register_custom_widgets(loader):
    loader.registerCustomWidget(BaseButtonGroup)
    loader.registerCustomWidget(CenterImgView)
    loader.registerCustomWidget(LabelTrainVal)
    loader.registerCustomWidget(LabelTrainBar)
    loader.registerCustomWidget(LabelValBar)
    loader.registerCustomWidget(IconSpin)
    loader.registerCustomWidget(ImgsFlow)
    loader.registerCustomWidget(ImgTagList)
    loader.registerCustomWidget(JumpToImg)
    loader.registerCustomWidget(ObjList)
    loader.registerCustomWidget(PushButtonWaiting)
    loader.registerCustomWidget(SearchBox)
    loader.registerCustomWidget(ScanButton)
    loader.registerCustomWidget(TaskDescBrowser)
