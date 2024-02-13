
#!/usr/bin/python3

import os
import sys
import time

from PIL import Image
from PyQt5.QtCore import Qt, QSize, QSettings, pyqtSignal, QObject, QStandardPaths, QThread
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
                              QHBoxLayout, QFileDialog, QDialogButtonBox, QLabel, QListWidget,
                              QComboBox, QMessageBox, QListWidgetItem, QDialog,
                              QGridLayout, QDesktopWidget, QProgressBar, QGroupBox,
                              QRadioButton, QTreeView, QFileSystemModel, QScrollArea)

PREVIEW_IMAGE_WIDTH = 200
PREVIEW_IMAGE_HEIGHT = 200
MARGIN = 10

class FolderView(QWidget):
    default_root_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_me()

    def init_me(self):
        self.model = QFileSystemModel()
        self.default_root_changed.connect(self.update_path_label)
        script_directory = os.path.dirname(os.path.abspath(__file__))
        self.index = self.model.setRootPath(script_directory)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setCurrentIndex(self.index)
        self.tree.setRootIndex(self.index)

        self.filesystem_panel_label = QLabel("File System: ", self)
        self.filesystem_path_label = QLabel(f"Current File System Path: {script_directory}", self)

        self.change_dir_btn = QPushButton('Change Directory', self)
        self.change_dir_btn.clicked.connect(self.change_directory)

        self.saved_queue_list = QListWidget(self)

        window_layout = QVBoxLayout()
        window_layout.addWidget(self.filesystem_panel_label)
        window_layout.addWidget(self.filesystem_path_label)
        window_layout.addWidget(self.change_dir_btn)
        window_layout.addWidget(self.tree)
        self.setLayout(window_layout)

    def on_tree_view_clicked(self, index):
        self.default_root_changed.emit(self.model.filePath(index))

    def update_path_label(self, path):
        self.filesystem_path_label.setText(f"Current File System Path: {path}")

    def change_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.set_root(directory)
            self.default_root_changed.emit(directory)
            self.update_path_label(directory)

    def set_script_directory(self):
        script_directory = os.path.dirname(os.path.abspath(__file__))
        self.set_root(script_directory)

    def set_root(self, path):
        if len(path) == 0:
            self.model.setRootPath(QStandardPaths.standardLocations(QStandardPaths.HomeLocation)[0])
            self.tree.setRootIndex(self.index)
        else:
            new_index = self.model.index(path)
            self.tree.setRootIndex(new_index)
            self.tree.setCurrentIndex(new_index)

class Worker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, str)

    def __init__(self, filePaths, processing_mode, save_directory, scale_factor, convert_from_format, convert_to_format,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filePaths = filePaths
        self.processing_mode = processing_mode
        self.save_directory = save_directory
        self.scale_factor = scale_factor
        self.convert_from_format = convert_from_format
        self.convert_to_format = convert_to_format

    def run(self):
        # BUG HERE - duplicates (doubles) the amount of filePaths -> processes both info panel AND processing
        # queue files when it should only do processing queue files
        total_files = len(self.filePaths)
        for i, file_path in enumerate(self.filePaths):
            try:
                original_file_path = file_path

                if self.processing_mode == 'upscale':
                    operation_suffix = f"_upscaled{self.scale_factor}"
                    self.upscale_image(file_path)
                elif self.processing_mode == 'downscale':
                    operation_suffix = f"_downscaled{self.scale_factor}"
                    self.downscale_image(file_path)
                elif self.processing_mode == 'convert':
                    operation_suffix = f"_converted{self.convert_from_format}_to_{self.convert_to_format}"
                    self.convert_image(file_path)
                else:
                    operation_suffix = ""

                self.finished.emit(original_file_path, operation_suffix)

            except Exception as e:
                print(f"An error occurred while processing {file_path}: {e}")

            progress_percent = int(((i + 1) / total_files) * 100)
            self.progress.emit(progress_percent)

    def upscale_image(self, file_path):
        with Image.open(file_path) as img:
            scale = float(self.scale_factor.rstrip('x'))
            new_dimensions = (int(img.width * scale), int(img.height * scale))
            upscaled_img = img.resize(new_dimensions, Image.LANCZOS)

            new_file_name = f"upscaled_{os.path.basename(file_path)}"
            target_path = os.path.join(self.save_directory, new_file_name)
            upscaled_img.save(target_path)

    def downscale_image(self, file_path):
        with Image.open(file_path) as img:
            scale = float(self.scale_factor.rstrip('x'))
            new_dimensions = (int(img.width / scale), int(img.height / scale))
            downscaled_img = img.resize(new_dimensions, Image.LANCZOS)

            new_file_name = f"downscaled_{os.path.basename(file_path)}"
            target_path = os.path.join(self.save_directory, new_file_name)
            downscaled_img.save(target_path)

    def convert_image(self, file_path):
        with Image.open(file_path) as img:
            new_file_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.{self.convert_to_format}"
            target_path = os.path.join(self.save_directory, new_file_name)
            img.save(target_path)

    def get_new_file_path(self, file_path, suffix):
        base, ext = os.path.splitext(file_path)
        new_file_name = f"{base}{suffix}{ext}"
        new_file_path = os.path.join(self.save_directory, new_file_name)
        return new_file_path

class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processing_mode = None
        self.filesystem_panel = FolderView()
        self.filesystem_panel.default_root_changed.connect(self.ask_set_default_root)
        self.settings = QSettings("User", "PyImgScale")
        self.filePaths = []
        self.scale_factor = "1.0x"
        self.convert_from_format = "png"
        self.convert_to_format = "png"
        self.initUI()

        self.worker = None

        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

    def initUI(self):
        self.setWindowTitle("PyImgScale")
        self.setGeometry(0, 0, 1280, 720)
        self.resize(self.settings.value("size", QSize(1280, 720)))
        self.save_directory = None

        main_layout = QHBoxLayout()

        self.filesystem_panel = FolderView()
        main_layout.addWidget(self.filesystem_panel, 2)

        center_layout = QVBoxLayout()
        center_layout.addWidget(self.create_process_settings_layout())
        center_layout.addWidget(self.create_scale_settings_layout())
        center_layout.addWidget(self.create_save_dir_settings_layout())
        center_layout.addWidget(self.create_type_processing_buttons_layout())
        center_layout.addWidget(self.create_eta_label())
        center_layout.addWidget(self.create_process_button())
        center_layout.addWidget(self.create_file_info_panel_layout())
        center_layout.addWidget(self.create_processing_queue_control_panel_layout())
        center_layout.addWidget(self.create_image_preview_section_layout())
        main_layout.addLayout(center_layout, 2)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.create_saved_queue_panel_layout())
        main_layout.addLayout(right_layout, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def create_saved_queue_panel_layout(self):
        save_group = QGroupBox("Saved Queue: ", self)
        save_group_layout = QVBoxLayout()

        self.saved_queue_list = QListWidget(self)
        save_group_layout.addWidget(self.saved_queue_list)

        save_group.setLayout(save_group_layout)
        return save_group

    def create_process_settings_layout(self):
        p_group = QGroupBox("Processing Options: ", self)
        p_layout = QHBoxLayout()

        self.process_option_combo = QComboBox(self)
        self.process_option_combo.addItems(["Single File", "Multiple Files", "Directory"])
        p_layout.addWidget(QLabel("Process Option:"))
        p_layout.addWidget(self.process_option_combo)

        self.open_save_dir_combo = QComboBox(self)
        self.open_save_dir_combo.addItems(["Yes", "No"])
        p_layout.addWidget(QLabel("Open Save Directory After Processing?"))
        p_layout.addWidget(self.open_save_dir_combo)

        p_group.setLayout(p_layout)
        return p_group

    def create_scale_settings_layout(self):
        h_group = QGroupBox("Scale Settings: ", self)
        h_layout = QHBoxLayout()

        self.scale_factor_combo = QComboBox(self)
        self.scale_factor_combo.addItems(["1.5x", "2x", "4x", "6x", "8x"])
        self.scale_factor = self.scale_factor_combo.itemText(0)
        self.scale_factor_combo.currentTextChanged.connect(self.on_scale_factor_changed)
        h_layout.addWidget(QLabel("Scale Factor:"))
        h_layout.addWidget(self.scale_factor_combo)

        h_group.setLayout(h_layout)
        return h_group

    def create_save_dir_settings_layout(self):
        all_save_dir_group = QGroupBox("Save Settings Options: ", self)
        all_save_dir_layout = QHBoxLayout()

        self.change_save_dir_btn = QPushButton('Change Save Directory', self)
        self.change_save_dir_btn.clicked.connect(self.change_save_directory)
        self.save_directory_label = QLabel("Save to: Not Set", self)
        all_save_dir_layout.addWidget(self.change_save_dir_btn)
        all_save_dir_layout.addWidget(self.save_directory_label)

        all_save_dir_group.setLayout(all_save_dir_layout)
        return all_save_dir_group

    def create_type_processing_buttons_layout(self):
        control_process_group = QGroupBox("Processing Options: ", self)
        process_selection_layout = QHBoxLayout()

        self.upscale_btn = QRadioButton('Upscale', self)
        self.upscale_btn.clicked.connect(self.processing_logic)

        process_selection_layout.addWidget(self.upscale_btn)

        self.downscale_btn = QRadioButton('Downscale', self)
        self.downscale_btn.clicked.connect(self.processing_logic)

        process_selection_layout.addWidget(self.downscale_btn)

        self.convert_btn = QRadioButton('Convert', self)
        self.convert_btn.clicked.connect(self.processing_logic)

        process_selection_layout.addWidget(self.convert_btn)

        self.convert_from_combo = QComboBox(self)
        self.convert_from_combo.addItems(["png", "jpg/jpeg", "pdf", "tga", "bmp"])

        self.convert_from_format = self.convert_from_combo.itemText(0).split('/')[0]
        self.convert_from_combo.currentTextChanged.connect(self.on_convert_from_format_changed)

        process_selection_layout.addWidget(QLabel("Convert From:"))
        process_selection_layout.addWidget(self.convert_from_combo)

        self.convert_to_combo = QComboBox(self)
        self.convert_to_combo.addItems(["png", "jpg/jpeg", "pdf", "tga", "bmp"])

        self.convert_to_format = self.convert_to_combo.itemText(0).split('/')[0]
        self.convert_to_combo.currentTextChanged.connect(self.on_convert_to_format_changed)

        process_selection_layout.addWidget(QLabel("Convert To:"))
        process_selection_layout.addWidget(self.convert_to_combo)

        control_process_group.setLayout(process_selection_layout)

        return control_process_group

    def create_eta_label(self):
        eta_label_group = QGroupBox(self)
        eta_label_layout = QHBoxLayout()

        self.eta_label = QLabel("Estimated Time: Not Calculated", self)
        eta_label_layout.addWidget(self.eta_label)

        eta_label_group.setLayout(eta_label_layout)
        return eta_label_group

    def create_process_button(self):
        process_button_group = QGroupBox(self)
        process_button_layout = QHBoxLayout()

        process_btn = QPushButton('Process', self)
        process_btn.clicked.connect(self.process_queue)
        process_button_layout.addWidget(process_btn)

        process_button_group.setLayout(process_button_layout)
        return process_button_group

    def create_file_info_panel_layout(self):
        file_info_control_group = QGroupBox("File Information Panel: ", self)
        file_info_control_layout = QVBoxLayout()

        self.file_info_panel = QLabel("File Information:", self)
        file_info_control_layout.addWidget(self.file_info_panel)

        self.file_info_list = QListWidget(self)
        self.file_info_list.setSelectionMode(QListWidget.ExtendedSelection)
        file_info_control_layout.addWidget(self.file_info_list)

        self.total_info_label = QLabel("Total Files: 0, Total Size: 0.00 MB", self)
        file_info_control_layout.addWidget(self.total_info_label)

        add_btn = QPushButton('Add Images', self)
        add_btn.clicked.connect(self.add_images)
        file_info_control_layout.addWidget(add_btn)

        remove_btn = QPushButton('Remove Selected Image', self)
        remove_btn.clicked.connect(self.remove_selected_image)
        file_info_control_layout.addWidget(remove_btn)

        file_info_control_group.setLayout(file_info_control_layout)
        return file_info_control_group

    def create_processing_queue_control_panel_layout(self):
        queue_control_group = QGroupBox("Processing Queue:", self)
        queue_control_layout = QVBoxLayout()

        self.queue_panel = QListWidget(self)
        self.queue_panel.setSelectionMode(QListWidget.ExtendedSelection)
        queue_control_layout.addWidget(self.queue_panel)

        self.total_processing_queue_label = QLabel("Total Files: 0, Total Size: 0.00 MB", self)
        queue_control_layout.addWidget(self.total_processing_queue_label)

        add_to_queue_btn = QPushButton('Add to Queue', self)
        add_to_queue_btn.clicked.connect(self.on_add_to_queue_clicked)
        queue_control_layout.addWidget(add_to_queue_btn)

        remove_from_queue_btn = QPushButton('Remove from Queue', self)
        remove_from_queue_btn.clicked.connect(self.remove_from_queue)
        queue_control_layout.addWidget(remove_from_queue_btn)

        self.processing_queue_pbar = QProgressBar(self)
        self.processing_queue_pbar.setGeometry(30, 40, 200, 25)
        queue_control_layout.addWidget(self.processing_queue_pbar)
        self.processing_queue_pbar.setHidden(True)

        queue_control_group.setLayout(queue_control_layout)
        return queue_control_group

    def create_image_preview_section_layout(self):
        preview_widget_group = QGroupBox("Image Preview Panel: ", self)
        self.preview_layout = QGridLayout()

        preview_widget = QWidget()
        preview_widget.setLayout(self.preview_layout)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(preview_widget)

        preview_layout = QVBoxLayout()
        preview_layout.addWidget(scroll_area)
        preview_widget_group.setLayout(preview_layout)

        return preview_widget_group

    def processing_logic(self):
        self.processing_mode = ('upscale' if self.upscale_btn.isChecked() else
                                'downscale' if self.downscale_btn.isChecked() else
                                'convert' if self.convert_btn.isChecked() else
                                None)

    def scale_images_logic(self):
        self.scale_factor = self.scale_factor_combo.currentText()

    def convert_images_logic(self):
        self.convert_from_format = self.convert_from_combo.currentText().split('/')[0]
        self.convert_to_format = self.convert_to_combo.currentText().split('/')[0]

    def on_scale_factor_changed(self, text):
        self.scale_factor = text

    def on_convert_from_format_changed(self, text):
        self.convert_from_format = text.split('/')[0]

    def on_convert_to_format_changed(self, text):
        self.convert_to_format = text.split('/')[0]

    def closeEvent(self, event):
        self.settings.setValue("size", self.size())
        super().closeEvent(event)

    def ask_set_default_root(self, directory):
        if QMessageBox.question(self, "Set Default Root", "Would you like to set this as the default root directory?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.set_default_root(directory)

    def set_default_root(self, directory):
        QSettings("YourCompany", "YourApp").setValue("defaultRootPath", directory)

    def change_file_system_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.filesystem_panel.set_root(directory or QStandardPaths.standardLocations(QStandardPaths.HomeLocation)[0])

    def change_save_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        self.save_directory = directory or None
        self.save_directory_label.setText(f"Save to: {directory or 'Not Set'}")

    def update_image_paths(self, old_path, new_path):
        if old_path in self.filePaths:
            self.filePaths.remove(old_path)
        self.filePaths.append(new_path)
        self.file_info_list.clear()
        self.file_info_list.addItems(os.path.basename(path) for path in self.filePaths)
        self.update_preview()

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        new_files = [f for f in files if f not in self.filePaths]
        self.filePaths.extend(new_files)
        self.update_file_info_list()

    def remove_selected_image(self):
        for item in self.file_info_list.selectedItems():
            file_name = item.text().split(" - ")[0]
            full_path = next((p for p in self.filePaths if os.path.basename(p) == file_name), None)
            if full_path:
                self.filePaths.remove(full_path)
                self.file_info_list.takeItem(self.file_info_list.row(item))

    def update_file_info_list(self):
        self.file_info_list.clear()
        total_size = sum(os.path.getsize(p) for p in self.filePaths) / (1024 * 1024)
        for path in self.filePaths:
            file_size_mb = os.path.getsize(path) / (1024 * 1024)
            self.file_info_list.addItem(f"{os.path.basename(path)} - {file_size_mb:.2f} MB")
        self.total_info_label.setText(f"Total Files: {len(self.filePaths)}, Total Size: {total_size:.2f} MB")

    def on_add_to_queue_clicked(self):
        selected_items = self.file_info_list.selectedItems()
        if not selected_items:
            print("No file selected to add to the queue.")
            return
        for item in selected_items:
            file_path = item.text().split(" - ")[0]
            self.add_to_queue(file_path)

    def add_to_queue(self, file_path):
        selected_items = self.file_info_list.selectedItems()
        for item in selected_items:
            file_path = item.text().split(" - ")[0]
            if file_path not in self.filePaths:
                self.filePaths.append(file_path)
                self.queue_panel.addItem(file_path)
        self.update_processing_queue_label()

    def remove_from_queue(self):
        selected_items = self.queue_panel.selectedItems()
        if not selected_items:
            print("No file selected to remove from the queue.")
            return
        for item in selected_items:
            full_path = item.text()
            if full_path in self.filePaths:
                self.filePaths.remove(full_path)
                row = self.queue_panel.row(item)
                self.queue_panel.takeItem(row)
            else:
                print(f"Could not find the file path for {full_path} in the queue.")
        self.update_processing_queue_label()

    def update_processing_queue_label(self):
        total_size = sum(
            os.path.getsize(item.text()) for i in range(self.queue_panel.count()) for item in [self.queue_panel.item(i)]
            if os.path.isfile(item.text()))
        total_size_mb = total_size / (1024 * 1024)
        self.total_processing_queue_label.setText(
            f"Total Files: {self.queue_panel.count()}, Total Size: {total_size_mb:.2f} MB")

    def estimate_processing_time(self):
        if self.filePaths:
            start_time = time.time()
            end_time = time.time()
            total_time = (end_time - start_time) * len(self.filePaths)
            self.eta_label.setText(f"Estimated Time: {total_time:.2f} seconds")

    def add_to_saved_queue(self, original_file_path, operation_suffix):
        display_name = self.generate_display_name(original_file_path, operation_suffix)
        if display_name not in self.get_saved_queue_files():
            self.saved_queue_list.addItem(display_name)

    def generate_display_name(self, original_file_path, operation_suffix):
        base_filename = os.path.basename(original_file_path)
        name, ext = os.path.splitext(base_filename)
        return f"{name}{operation_suffix}{ext}"

    def get_saved_queue_files(self):
        return [self.saved_queue_list.item(i).text() for i in range(self.saved_queue_list.count())]

    def process_queue(self):
        if not (self.worker and self.worker.isRunning()):
            self.initialize_worker_settings()
            self.worker = Worker(self.filePaths, self.processing_mode, self.save_directory,
                                 self.scale_factor, self.convert_from_format, self.convert_to_format)
            self.worker.finished.connect(self.file_processed)
            self.worker.progress.connect(self.update_progress_bar)
            self.worker.start()
        else:
            print("A processing task is already running.")

    def initialize_worker_settings(self):
        self.scale_factor = self.scale_factor_combo.currentText()
        self.convert_from_format = self.convert_from_combo.currentText().split('/')[0]
        self.convert_to_format = self.convert_to_combo.currentText().split('/')[0]

    def file_processed(self, original_file_path, operation_suffix):
        self.add_to_saved_queue(original_file_path, operation_suffix)
        original_basename = os.path.basename(original_file_path)
        for i in range(self.queue_panel.count()):
            if os.path.basename(self.queue_panel.item(i).text()) == original_basename:
                self.queue_panel.takeItem(i)
                break
        self.update_processing_queue_label()

    def progress_bar(self):
        for i in range(101):
            time.sleep(0.05)
            self.update_progress_bar(i)

    def update_progress_bar(self, value):
        self.processing_queue_pbar.setValue(value)

def main():
    app = QApplication(sys.argv)
    style = 'Fusion'
    app.setStyle(style)
    ex = ImageProcessor()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
