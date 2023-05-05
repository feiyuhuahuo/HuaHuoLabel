#!/usr/bin/env python 
# -*- coding:utf-8 -*-

# 超过50行的规则、重复代码可放在这里，减轻main.py的代码行数
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction
from need.custom_widgets import *
from need.custom_threads import *


def connect_all_other_signals(main_window):
    main_window.ui.checkBox_hide_cross.clicked.connect(main_window.set_hide_cross)
    main_window.ui.checkBox_one_label.pressed.connect(main_window.raise_label_mode_conflict)
    main_window.ui.checkBox_one_label.toggled.connect(main_window.set_one_file_label)
    main_window.ui.checkBox_separate_label.pressed.connect(main_window.raise_label_mode_conflict)
    main_window.ui.checkBox_separate_label.toggled.connect(main_window.set_separate_label)
    main_window.ui.checkBox_shape_edit.toggled.connect(main_window.set_shape_edit_mode)

    main_window.ui.comboBox.currentIndexChanged.connect(main_window.set_scan_mode)
    main_window.ui.comboBox_2.currentIndexChanged.connect(main_window.change_shape_type)

    main_window.ui.horizontalSlider.valueChanged.connect(main_window.img_enhance)
    main_window.ui.horizontalSlider_2.valueChanged.connect(main_window.img_enhance)
    main_window.ui.horizontalSlider_3.valueChanged.connect(main_window.img_pil_contrast)

    main_window.ui.lineEdit_search.search_btn.clicked.connect(main_window.img_search)

    # main_window.ui.class_list.itemClicked.connect(lambda: main_window.look_or_not_look(double=False))
    # main_window.ui.class_list.itemDoubleClicked.connect(lambda: main_window.look_or_not_look(double=True))
    main_window.ui.shape_list.itemSelectionChanged.connect(main_window.set_info_widget_selected)

    main_window.ui.pushButton_img_cate.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_img_tag.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_obj_cate.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_obj_tag.clicked.connect(main_window.fold_buttons)
    main_window.ui.pushButton_img_cate_add.clicked.connect(main_window.add_buttons)
    main_window.ui.pushButton_img_tag_add.clicked.connect(main_window.add_buttons)
    main_window.ui.pushButton_obj_cate_add.clicked.connect(main_window.add_buttons)
    main_window.ui.pushButton_obj_tag_add.clicked.connect(main_window.add_buttons)

    main_window.ui.pushButton_35.clicked.connect(main_window.undo_painting)
    main_window.ui.pushButton_36.clicked.connect(main_window.save_ann_img)
    main_window.ui.pushButton_40.clicked.connect(main_window.clear_painted_img)
    # main_window.ui.pushButton_50.clicked.connect(main_window.set_m_cls_default_c)
    main_window.ui.pushButton_81.clicked.connect(lambda: main_window.img_rotate(do_paint=True))
    main_window.ui.pushButton_82.clicked.connect(lambda: main_window.img_flip(h_flip=True, do_paint=True))
    main_window.ui.pushButton_83.clicked.connect(lambda: main_window.img_flip(v_flip=True, do_paint=True))
    main_window.ui.pushButton_84.clicked.connect(main_window.img_enhance_reset)
    main_window.ui.pushButton_auto_infer.clicked.connect(main_window.auto_inference)
    # main_window.ui.pushButton_bg.pressed.connect(main_window.set_semantic_bg_when_press)
    main_window.ui.pushButton_bookmark.pressed.connect(main_window.show_bookmark)
    main_window.ui.pushButton_build_task.pressed.connect(main_window.show_task_window)
    main_window.ui.pushButton_check_label.clicked.connect(main_window.check_dataset)
    # main_window.ui.pushButton_cls_back.clicked.connect(main_window.cls_back)
    main_window.ui.pushButton_cross_color.clicked.connect(main_window.change_cross_color)
    main_window.ui.pushButton_delay.clicked.connect(main_window.set_scan_delay)
    main_window.ui.pushButton_delete.clicked.connect(lambda: main_window.del_img(None))
    main_window.ui.pushButton_font_color.clicked.connect(main_window.change_font_color)
    main_window.ui.pushButton_generate_train.clicked.connect(main_window.generate_train)
    main_window.ui.pushButton_goto_train.clicked.connect(lambda: main_window.add_to_train_val(dst_part='train'))
    main_window.ui.pushButton_goto_val.clicked.connect(lambda: main_window.add_to_train_val(dst_part='val'))
    main_window.ui.pushButton_img_edit.clicked.connect(main_window.edit_img)
    main_window.ui.pushButton_img_window.clicked.connect(main_window.new_img_window)
    main_window.ui.jump_to.pushButton_jump.clicked.connect(main_window.img_jump)
    main_window.ui.scan_buttons.pushButton_last.clicked.connect(lambda: main_window.scan_img(last=True))
    main_window.ui.scan_buttons.pushButton_next.clicked.connect(lambda: main_window.scan_img(next=True))
    main_window.ui.pushButton_random_split.clicked.connect(main_window.random_train_val)
    main_window.ui.pushButton_open_task.clicked.connect(main_window.open_task)
    main_window.ui.pushButton_pen_color.clicked.connect(main_window.change_pen_color)
    main_window.ui.pushButton_pen_color_2.clicked.connect(main_window.change_pen_color)
    # main_window.ui.pushButton_pin.clicked.connect(main_window.pin_unpin_image)
    main_window.ui.pushButton_shape_list.clicked.connect(main_window.fold_list)
    main_window.ui.pushButton_stat.clicked.connect(main_window.show_class_statistic)
    # main_window.ui.pushButton_update_png.clicked.connect(main_window.update_sem_pngs)

    main_window.ui.radioButton_read.toggled.connect(main_window.set_read_mode)

    # main_window.ui.spinBox.valueChanged.connect(main_window.change_pen_size)
    # main_window.ui.spinBox_5.valueChanged.connect(main_window.change_font_size)
    # main_window.ui.spinBox_6.valueChanged.connect(main_window.change_pen_size)

    # main_window.ui.tabWidget.currentChanged.connect(main_window.set_work_mode)

    main_window.ui.toolBox.currentChanged.connect(main_window.set_tool_mode)

    signal_auto_save.signal.connect(main_window.save_one_file_json)
    signal_check_draw_enable.signal.connect(main_window.check_draw_enable)
    signal_cocc_done.signal.connect(main_window.change_one_class_category_done)
    signal_docl_done.signal.connect(main_window.delete_one_class_jsons_done)
    signal_del_shape.signal.connect(main_window.del_shape)
    signal_move2new_folder.signal.connect(main_window.move_to_new_folder)
    signal_one_collection_done.signal.connect(main_window.save_one_shape)
    signal_open_label_window.signal.connect(main_window.show_class_selection_list)
    signal_shape_info_update.signal.connect(main_window.update_shape_info_text)
    signal_show_label_img.signal.connect(main_window.marquee_show)
    signal_show_plain_img.signal.connect(main_window.marquee_show)
    signal_stat_info.signal.connect(main_window.show_class_statistic_done)
    signal_update_num.signal.connect(main_window.update_class_list_num)
    signal_xy_color2ui.signal.connect(main_window.show_xy_color)
    signal_send_imgs.signal.connect(main_window.open_task)
    signal_request_imgs.signal.connect(main_window.send_auto_infer_imgs)


def init_menu(main_win):
    main_win.menu_task = QMenu(main_win)
    main_win.action_load_cls_classes = QAction(main_win.tr('加载类别'), main_win)
    main_win.action_load_cls_classes.triggered.connect(main_win.load_classes)
    main_win.menu_task.addAction(main_win.action_load_cls_classes)
    main_win.action_export_cls_classes = QAction(main_win.tr('导出类别'), main_win)
    main_win.action_export_cls_classes.triggered.connect(main_win.export_classes)
    main_win.menu_task.addAction(main_win.action_export_cls_classes)

    main_win.ui.groupBox_1.customContextMenuRequested.connect(
        lambda: main_win.show_menu(main_win.menu_task))
    main_win.ui.groupBox_2.customContextMenuRequested.connect(
        lambda: main_win.show_menu(main_win.menu_task))

    main_win.menu_seg_class = QMenu(main_win)
    main_win.action_load_seg_class = QAction(main_win.tr('加载类别'), main_win)
    main_win.action_load_seg_class.triggered.connect(main_win.load_classes)
    main_win.menu_seg_class.addAction(main_win.action_load_seg_class)
    main_win.action_export_seg_class = QAction(main_win.tr('导出类别'), main_win)
    main_win.action_export_seg_class.triggered.connect(main_win.export_classes)
    main_win.menu_seg_class.addAction(main_win.action_export_seg_class)
    main_win.action_modify_one_class_jsons = QAction(main_win.tr('修改类别'), main_win)
    main_win.action_modify_one_class_jsons.triggered.connect(main_win.change_one_class_category)
    main_win.menu_seg_class.addAction(main_win.action_modify_one_class_jsons)
    main_win.action_del_one_class_jsons = QAction(main_win.tr('删除类别'), main_win)
    main_win.action_del_one_class_jsons.triggered.connect(main_win.delete_one_class_jsons)
    main_win.menu_seg_class.addAction(main_win.action_del_one_class_jsons)

    main_win.menu_seg_annotation = QMenu(title='label_list_menu', parent=main_win)
    main_win.ui.shape_list.customContextMenuRequested.connect(
        lambda: main_win.show_menu(main_win.menu_seg_annotation))
    main_win.action_modify_one_shape_class = QAction(main_win.tr('修改类别'), main_win)
    main_win.action_modify_one_shape_class.triggered.connect(main_win.modify_shape_list_start)
    main_win.action_delete_one_shape = QAction(main_win.tr('删除标注'), main_win)
    main_win.action_delete_one_shape.triggered.connect(lambda: main_win.del_all_shapes(False))
    main_win.action_delete_all = QAction(main_win.tr('全部删除'), main_win)
    main_win.action_delete_all.triggered.connect(lambda: main_win.del_all_shapes(True))
    main_win.action_lock_shape = QAction(main_win.tr('锁定标注'), main_win)
    main_win.action_lock_shape.triggered.connect(main_win.lock_shape)
    main_win.menu_seg_annotation.addAction(main_win.action_modify_one_shape_class)
    main_win.menu_seg_annotation.addAction(main_win.action_delete_one_shape)
    main_win.menu_seg_annotation.addAction(main_win.action_delete_all)
    main_win.menu_seg_annotation.addAction(main_win.action_lock_shape)

    main_win.menu_set_shape_info = QMenu(main_win)
    main_win.action_oc_shape_info = QAction(main_win.tr('禁用（提高切图速度）'), main_win)
    main_win.action_oc_shape_info.triggered.connect(main_win.oc_shape_info)
    main_win.menu_set_shape_info.addAction(main_win.action_oc_shape_info)

    main_win.ui.action_cn.triggered.connect(lambda: main_win.set_language('CN'))
    main_win.ui.action_en.triggered.connect(lambda: main_win.set_language('EN'))
    main_win.ui.action_about.triggered.connect(main_win.about_hhl)


def init_custom_widgets(main_window):
    main_window.window_build_task = BuildTask()
    main_window.window_img_edit = ImgEdit(main_window)
    main_window.window_sem_class_changed = CustomMessageBox('information', main_window.tr('类别列表变化'))
    main_window.window_ann_saved = CustomMessageBox('information', main_window.tr('已保存'))
    main_window.window_version_remind = CustomMessageBox('question', main_window.tr('版本提醒'))
    main_window.window_choose_version = ChooseVersion(main_window.ui)
    main_window.marquees = Marquees(main_window)
    main_window.ui.scrollArea.setWidget(main_window.marquees)
    main_window.ui.spinBox_thickness.set_default('images/thickness.png', 1, 20, 1)
    main_window.ui.spinBox_thickness2.set_default('images/thickness.png', 1, 20, 3)
    main_window.ui.spinBox_fontsize.set_default('images/font_size.png', 1, 50, 20, padding_icon=2)


def register_custom_widgets(main_window):
    main_window.loader.registerCustomWidget(CenterImgView)
    main_window.loader.registerCustomWidget(ClassListWidget)
    main_window.loader.registerCustomWidget(ShapeListWidget)
    main_window.loader.registerCustomWidget(ButtonWithHoverWindow)
    main_window.loader.registerCustomWidget(SearchBox)
    main_window.loader.registerCustomWidget(ScanButton)
    main_window.loader.registerCustomWidget(LabelTrainVal)
    main_window.loader.registerCustomWidget(LabelTrainBar)
    main_window.loader.registerCustomWidget(LabelValBar)
    main_window.loader.registerCustomWidget(ImgTagList)
    main_window.loader.registerCustomWidget(JumpToImg)
    main_window.loader.registerCustomWidget(ImgCateButtons)
    main_window.loader.registerCustomWidget(ObjList)
    main_window.loader.registerCustomWidget(IconSpin)
