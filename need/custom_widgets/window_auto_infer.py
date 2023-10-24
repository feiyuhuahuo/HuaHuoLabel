#!/usr/bin/env python 
# -*- coding:utf-8 -*-
import pdb
import onnxruntime as ort
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QFileDialog
from PySide6.QtWidgets import QMessageBox as QMB
from .widget_progress_bar import ProgressWindow
from need.custom_signals import BoolSignal
from need.custom_threads.auto_inference import RunInference
from need.utils import INS_all_classes

signal_request_imgs = BoolSignal()


class AutoInfer(QMainWindow):
    def __init__(self, work_mode, version_root):
        super().__init__()
        loader = QUiLoader()
        self.ui = loader.load('auto_infer.ui')
        self.auto_folder = self.tr('自动标注')
        self.file_dlg = QFileDialog()
        self.WorkMode = work_mode
        self.sess = None
        self.imgs = []
        self.version_root = version_root
        self.InputCorrect = False
        self.OutputCorrect = False
        self.ui.pushButton_load_model.clicked.connect(self.load_model)
        self.ui.pushButton_detect_one.clicked.connect(lambda: self.do_inference(False))
        self.ui.pushButton_detect_all.clicked.connect(lambda: self.do_inference(True))

        if self.WorkMode in ('单分类', 'Single Cls'):
            self.ui.stackedWidget.setCurrentIndex(0)
        elif self.WorkMode in ('多分类', 'Multi Cls'):
            self.ui.stackedWidget.setCurrentIndex(1)
        elif self.WorkMode in ('目标检测', 'Obj Det'):
            self.ui.stackedWidget.setCurrentIndex(2)
        elif self.WorkMode in ('语义分割', 'Sem Seg', '实例分割', 'Ins Seg'):
            self.ui.stackedWidget.setCurrentIndex(3)

        self.ui.textBrowser_3.append(self.tr('目前只支持单张图片推理。'))
        if self.ui.checkBox.isChecked():
            self.ui.textBrowser_3.append(self.tr('自动缩放已启用，如果图片尺寸不匹配，将自动调整至需要的尺寸。'))
        self.ui.textBrowser_3.append(self.tr('模式：{}').format(work_mode))
        classes = AllClasses.classes()
        self.ui.textBrowser_3.append(self.tr('类别：{}, 数量：{}').format(', '.join(classes), len(classes)))
        self.head_text = self.ui.textBrowser_3.document().toPlainText()

    def close(self):
        self.ui.close()

    def load_model(self):
        model_file = self.file_dlg.getOpenFileName(self.ui, '选择模型文件', filter='模型文件 (*.onnx *.ir)')[0]
        if model_file:
            self.ui.textBrowser.clear()
            self.ui.textBrowser_2.clear()
            self.ui.textBrowser_3.clear()
            self.ui.textBrowser_3.append(self.head_text)
            self.InputCorrect = False
            self.OutputCorrect = False
            self.ui.lineEdit.setText(model_file)

            if model_file.endswith('onnx'):
                try:
                    self.sess = ort.InferenceSession(model_file, providers=["CUDAExecutionProvider"])
                    device_id = self.sess._provider_options['CUDAExecutionProvider']['device_id']
                    self.ui.textBrowser_3.append(self.tr('GPU id: {}').format(device_id))
                    self.window_progress = ProgressWindow(title='推理中', text_prefix='使用GPU推理中：')
                except:
                    self.sess = ort.InferenceSession(model_file, providers=["CPUExecutionProvider"])
                    self.window_progress = ProgressWindow(title='推理中', text_prefix='使用CPU推理中：')

                self.inputs = self.sess.get_inputs()
                self.outputs = self.sess.get_outputs()

            elif model_file.endswith('ir'):
                pass
            else:
                raise NotImplementedError(f'"{model_file.split(".")[-1]}" format is not supported yet.')

            self.check_inputs()
            self.check_outputs()

    def check_inputs(self):
        if len(self.inputs) > 1:
            QMB.critical(self.ui, self.tr('输入错误'),
                         self.tr('模型只能有一个输入，实际有{}个输入。').format(len(self.inputs)))
            return

        name, type, shape = self.tr('输入'), self.inputs[0].type, tuple(self.inputs[0].shape)
        if not self.dim_error(name, 3, len(shape), shape):
            return
        if not self.dtype_error(name, 'tensor(uint8)', type):
            return
        if not self.channel_error(name, 3, shape[2], 2):
            return

        self.InputCorrect = True

    def check_outputs(self):
        if self.WorkMode in ('单分类', 'Single Cls', '多分类', 'Multi Cls'):
            if len(self.outputs) > 1:
                QMB.critical(self.ui, self.tr('输出错误'),
                             self.tr('"{}"模式只能有一个输出，实际有{}个输出。').format(self.WorkMode, len(self.outputs)))
                return

            name, type, shape = self.tr('输出'), self.outputs[0].type, tuple(self.outputs[0].shape)
            if not self.dim_error(name, 2, len(shape), shape):
                return
            if not self.dtype_error(name, 'tensor(float)', type):
                return
            if not self.class_error(name, len(AllClasses), shape[1]):
                return

        elif self.WorkMode in ('语义分割', 'Sem Seg'):
            pass
        elif self.WorkMode in ('目标检测', 'Obj Det', '实例分割', 'Ins Seg'):
            pass

        self.OutputCorrect = True

    def class_error(self, name, expected, actual):
        if actual != expected:
            QMB.critical(self.ui, self.tr('{}类别数量错误').format(name),
                         self.tr('{}的类别数量必须为{}，实际为{}。').format(name, expected, actual))
            return False
        return True

    def channel_error(self, name, expected, actual, ch_index):
        if actual != expected:
            QMB.critical(self.ui, self.tr('{}通道错误').format(name),
                         self.tr('{}的第{}维必须为{}通道，实际为{}通道。').format(name, ch_index, expected, actual))
            return False
        return True

    def dim_error(self, name, expected, actual, shape):
        if actual != expected:
            QMB.critical(self.ui, self.tr('{}维度错误').format(name),
                         self.tr('{}必须为{}维，实际为{}维。').format(name, expected, actual))
            return False

        if name == self.tr('输入'):
            self.ui.textBrowser.append(self.tr('尺寸：{}').format(shape))
        elif name == self.tr('输出'):
            self.ui.textBrowser_2.append(self.tr('尺寸：{}').format(shape))

        return True

    def dtype_error(self, name, expected, actual):
        if actual != expected:
            QMB.critical(self.ui, self.tr('{}数据类型错误').format(name),
                         self.tr('{}的数据类型必须为{}，实际为{}。').format(name, expected, actual))
            return False

        if name == self.tr('输入'):
            self.ui.textBrowser.append(self.tr('数据类型：{}').format(actual))
        elif name == self.tr('输出'):
            self.ui.textBrowser_2.append(self.tr('数据类型：{}').format(actual))

        return True

    def do_inference(self, infer_all):
        if not self.InputCorrect or not self.OutputCorrect:
            QMB.critical(self.ui, self.tr('输入输出错误'), self.tr('输入输出存在错误，请检查'))
            return

        signal_request_imgs.send(infer_all)
        meta_paras = self.get_meta_paras()
        self.window_progress.show()
        self.infer_thread = RunInference(self.WorkMode, self.sess, self.imgs, meta_paras)
        self.infer_thread.start()

    def get_meta_paras(self):
        meta_dict = {}
        if self.WorkMode in ('单分类', 'Single Cls'):
            meta_dict['score_thre'] = self.ui.doubleSpinBox_11.value()
        elif self.WorkMode in ('多分类', 'Multi Cls'):
            pass
        elif self.WorkMode in ('目标检测', 'Obj Det'):
            pass
        elif self.WorkMode in ('语义分割', 'Sem Seg', '实例分割', 'Ins Seg'):
            pass

        return meta_dict

    def receive_imgs(self, imgs):
        assert type(imgs) == list, 'Error, auto infer imgs should be list.'
        self.imgs = imgs

    def show(self):
        self.ui.show()


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication()
    aa = AutoInfer()
    aa.show()
    app.exec()
