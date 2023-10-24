#!/usr/bin/env python 
# -*- coding:utf-8 -*-

def button_action(self):
    if not self.task_root:
        return
    button = self.sender()
    c_name = button.text()
    img_path = self.imgs[self.__cur_i]
    img_name = img_path.split('/')[-1]
    if img_path == 'images/图片已删除.png':
        return

    if self.WorkMode == self.AllModes[0]:
        if self.task_root and c_name != '-':
            # self.cv2_img_changed = None

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
                        self.imgs[self.__cur_i] = f'{label_path}/{img_name}'  # 随着图片路径变化而变化
                        self.cls_op_track.append(('re_cls', self.__cur_i, self.cur_mar_i, img_path, label_path))
                        self.show_label_to_ui()

                        QMB.information(self.ui, self.tr('移动图片'),
                                        self.tr('{}已从<font color=red>{}</font>移动至<font color=red>{}</font>。')
                                        .format(img_name, old_class, c_name))
                else:
                    if self.ui.radioButton_read.isChecked():  # cut
                        self.file_move(img_path, label_path)
                        self.cls_op_track.append(('cut', self.__cur_i, self.cur_mar_i, img_path, label_path))
                    elif self.ui.radioButton_write.isChecked():  # copy
                        self.file_copy(img_path, label_path)
                        self.cls_op_track.append(('copy', self.__cur_i, self.cur_mar_i, img_path, label_path))

                    self.imgs[self.__cur_i] = f'{label_path}/{img_name}'  # 随着图片路径变化而变化

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
            QMB.warning(self.ui, self.tr('模式错误'), self.tr('请先切换至编辑模式!'))


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
        QMB.information(self.ui, self.tr('撤销操作'), self.tr('已撤销: ') +
                        f'{img_name}, {ori_path} --> {cur_path}。')

        self.remove_empty_cls_folder()


def check_dataset(self):
    if self.check_warnings('task'):
        if self.check_labels():
            self.check_train_val_set()


def check_labels(self):
    if self.OneFileLabel:
        redu_num, unla_num = 0, 0
        redu_list, unla_list = [], []
        img_names = [aa.split('/')[-1] for aa in self.imgs]

        for one in self.label_file_dict['labels'].keys():
            if one not in img_names:
                redu_list.append(one)
                redu_num += 1

        QMB.information(self.ui, self.tr('统一标注模式'),
                        self.tr('{}条标注记录找不到对应"原图"。').format(redu_num))

        if redu_num > 0:
            choice = QMB.question(self.ui, self.tr('统一标注模式'),
                                  self.tr('清理找不到对应"原图"的标注记录吗？'))
            if choice == QMB.Yes:
                for one in redu_list:
                    self.label_file_dict['labels'].pop(one)

                QMB.information(self.ui, self.tr('统一标注模式'), self.tr('共清理{}条记录。').format(redu_num))

        for i, one in enumerate(img_names):
            if not self.label_file_dict['labels'].get(one):
                unla_list.append(self.imgs[i])
                unla_num += 1

        QMB.information(self.ui, self.tr('统一标注模式'), self.tr('{}张"原图"未标注。').format(unla_num))

        if unla_num > 0:
            if self.remove_redu_files(unla_list, self.tr('统一标注模式'), self.tr('清理未标注的"原图"吗？')):
                QMB.information(self.ui, self.tr('统一标注模式'), self.tr('清理"原图"后需要重新打开目录。'))
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

            QMB.information(self.ui, self.tr('独立标注模式'), self.tr('{}张"原图"未标注。').format(unla_num))
        elif self.WorkMode in self.AllModes[(1, 2, 3, 4)]:
            label_files = glob_labels(f'{self.get_root("separate")}')
            unla_list, redu_list = two_way_check(self.imgs, label_files)
            unla_num, redu_num = len(unla_list), len(redu_list)

            QMB.information(self.ui, self.tr('独立标注模式'),
                            self.tr('{}个标注文件找不到对应的"原图"，{}张"原图"未标注。').format(redu_num, unla_num))

            if redu_num > 0:
                self.remove_redu_files(redu_list, self.tr('独立标注模式'),
                                       self.tr('清理找不到对应"原图"的标注文件吗？'))

        if unla_num > 0:
            if self.remove_redu_files(unla_list, self.tr('独立标注模式'), self.tr('清理未标注的"原图"吗？')):
                QMB.information(self.ui, self.tr('独立标注模式'), self.tr('清理"原图"后需要重新打开目录。'))
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

        QMB.information(self.ui, self.tr('独立标注模式'),
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
            choice = QMB.question(self.ui, self.tr('独立标注模式'),
                                  self.tr('训练集和验证集有{}张重复的图片，清理<font color=red>'
                                          '训练集</font>中的这些图片吗？').format(dupli_num))
            if choice == QMB.Yes:
                for one in t_imgs:
                    if one.split('/')[-1] in dupli_names:
                        file_remove(one)

                QMB.information(self.ui, self.tr('独立标注模式'),
                                self.tr('共清理{}个文件。').format(dupli_num))
                t_imgs = glob_imgs(f'{self.get_root("tv")}/imgs/train', self.WorkMode == self.AllModes[0])
                self.train_num = len(t_imgs)
                self.set_tv_bar()

            if choice == QMB.No:
                choice = QMB.question(self.ui, self.tr('独立标注模式'),
                                      self.tr('训练集和验证集有{}张重复的图片，清理<font color=red>'
                                              '验证集</font>中的这些图片吗？').format(dupli_num))
                if choice == QMB.Yes:
                    for one in v_imgs:
                        if one.split('/')[-1] in dupli_names:
                            file_remove(one)

                    QMB.information(self.ui, self.tr('独立标注模式'),
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

            QMB.information(self.ui, self.tr('独立标注模式'),
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


def cls_has_classified(self, img_path=None):  # 查看单分类，多分类模式下，图片是否已分类
    path = img_path if img_path else self.imgs[self.__cur_i]
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


def file_copy(self, src_path, dst_path):
    new_file_path = osp.join(dst_path, src_path.split('/')[-1])
    if self.del_existed_file(src_path, new_file_path):
        shutil.copy(src_path, dst_path)


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
