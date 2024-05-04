
#!/usr/bin/python3

import os
import sys
from pathlib import Path

from PIL import Image
from PyQt5.QtCore import Qt, QSize, QSettings, pyqtSignal, QStandardPaths, QThread
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
                             QHBoxLayout, QFileDialog, QLabel, QListWidget,
                             QComboBox, QMessageBox, QListWidgetItem, QGridLayout, QDesktopWidget, QProgressBar,
                             QGroupBox,
                             QRadioButton, QTreeView, QFileSystemModel, QScrollArea,
                             QTabWidget)

PREVIEW_IMAGE_WIDTH = 200
PREVIEW_IMAGE_HEIGHT = 200
MARGIN = 10

class FolderView(QWidget):
    default_root_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_me()

    def init_me(self):
        pass
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

        self.change_dir_btn.setToolTip(
            "Sets the directory path that is viewable in this panel. Default is the directory where this script resides.")

        self.filesystem_panel_label.setMinimumHeight(20)
        self.filesystem_panel_label.setBaseSize(25, 25)
        self.tree.setMinimumWidth(100)

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

class imageItem(QListWidgetItem):
    def __init__(self, fileName, fullPath):
        super().__init__(fileName)
        self.fullPath = fullPath
        self.fileName = fileName
        self.fileType = os.path.splitext(fileName)[1]
        self.fileSize = os.path.getsize(fullPath)

    @staticmethod
    def format_size(size_in_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f}{unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f}PB"

class Worker(QThread):
    progress = pyqtSignal(int)
    file_processed = pyqtSignal(imageItem, str)
    finished_processing_all = pyqtSignal(bool)

    def __init__(self, imagesToProcess, processing_mode, save_directory, scale_factor, convert_from_format,
                 convert_to_format):
        super().__init__()
        self.imagesToProcess = imagesToProcess
        self.processing_mode = processing_mode
        self.save_directory = save_directory
        self.scale_factor = scale_factor
        self.convert_from_format = convert_from_format
        self.convert_to_format = convert_to_format

    def run(self):
        total_files = len(self.imagesToProcess)
        self.finished_processing_all.emit(False)
        for i, image in enumerate(self.imagesToProcess):
            if isinstance(image, imageItem):
                file_path = image.fullPath
                try:
                    if not os.path.exists(file_path):
                        print(f"File does not exist: {file_path}")
                        continue

                    operation_suffix = ''
                    if self.processing_mode == 'upscale':
                        operation_suffix = "_upscaled"
                        self.upscale_image(file_path)
                    elif self.processing_mode == 'downscale':
                        operation_suffix = "_downscaled"
                        self.downscale_image(file_path)
                    elif self.processing_mode == 'convert':
                        operation_suffix = f"_converted_to_{self.convert_to_format}"
                        self.convert_image(file_path)

                    self.file_processed.emit(image, operation_suffix)

                except Exception as e:
                    print(f"An error occurred while processing {file_path}: {e}")

                progress_percent = int(((i + 1) / total_files) * 100)
                self.progress.emit(progress_percent)
        self.finished_processing_all.emit(True)

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
        base, original_ext = os.path.splitext(file_path)
        if self.processing_mode == 'convert':
            new_file_name = f"{os.path.basename(base)}{suffix}.{self.convert_to_format}"
        else:
            new_file_name = f"{os.path.basename(base)}{suffix}{original_ext}"
        new_file_path = os.path.join(self.save_directory, new_file_name)
        return new_file_path

class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processing_mode = None
        self.filesystem_panel = FolderView()
        self.filesystem_panel.default_root_changed.connect(self.ask_set_default_root)
        self.settings = QSettings("User", "PyImgScale")
        self.scale_factor = "1.5"
        self.convert_from_format = "png"
        self.convert_to_format = "png"
        self.upscale_model = None
        self.worker = None
        self.preview_layout = QGridLayout()
        self.initUI()

        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())

    def prepare_worker(self, imagesToProcess, processing_mode, save_directory, scale_factor, convert_from_format,
                       convert_to_format):
        self.worker = Worker(
            imagesToProcess, processing_mode, save_directory,
            scale_factor, convert_from_format, convert_to_format
        )
        self.worker.progress.connect(self.update_progress_bar)
        self.worker.file_processed.connect(self.file_processed)
        self.worker.finished_processing_all.connect(self.on_all_files_processed)

    def initialize_worker_settings(self):
        self.scale_factor = self.scale_factor_combo.currentText()
        self.convert_from_format = self.convert_from_combo.currentText().split('/')[0]
        self.convert_to_format = self.convert_to_combo.currentText().split('/')[0]

    def initUI(self):
        self.setWindowTitle("PyImgScale")
        self.setGeometry(0, 0, 1280, 720)
        self.resize(self.settings.value("size", QSize(1280, 720)))
        self.save_directory = None

        main_layout = QHBoxLayout()

        tabsLeft = QTabWidget()
        tabsLeft.addTab(self.fileSystemTabUI(), "File System")
        tabsLeft.addTab(self.fileInfoTabUI(), "Imported Files")
        tabsLeft.addTab(self.optionsTabUI(), "Options")
        main_layout.addWidget(tabsLeft)

        center_layout = QVBoxLayout()
        center_layout.addWidget(self.create_type_processing_buttons_layout())
        center_layout.addWidget(self.create_eta_label())
        center_layout.addWidget(self.create_progress_bar_layout())
        center_layout.addWidget(self.create_process_button())
        center_layout.addWidget(self.create_processing_queue_control_panel_layout())

        main_layout.addLayout(center_layout)

        tabsRight = QTabWidget()
        tabsRight.addTab(self.completedFilesPreviewTabUI(), "Completed Files Preview")
        tabsRight.addTab(self.savedFilesTabUI(), "Saved Files")
        main_layout.addWidget(tabsRight)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def fileSystemTabUI(self):
        optionsTab = QWidget()
        layout = QVBoxLayout()
        self.filesystem_panel = FolderView()
        layout.addWidget(self.filesystem_panel)
        optionsTab.setLayout(layout)
        return optionsTab

    def fileInfoTabUI(self):
        imagePreviewsTab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.create_file_info_panel_layout())
        imagePreviewsTab.setLayout(layout)
        return imagePreviewsTab

    def optionsTabUI(self):
        optionsTab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.create_process_settings_layout())
        layout.addWidget(self.create_scale_settings_layout())
        layout.addWidget(self.create_save_dir_settings_layout())
        # layout.addWidget(self.create_model_settings_layout())
        newWidget = QComboBox(self)
        layout.addWidget(newWidget)
        optionsTab.setLayout(layout)
        return optionsTab

    def completedFilesPreviewTabUI(self):
        optionsTab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.create_image_preview_section_layout())
        optionsTab.setLayout(layout)
        return optionsTab

    def savedFilesTabUI(self):
        imagePreviewsTab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.create_saved_processing_queue_list_layout())
        imagePreviewsTab.setLayout(layout)
        return imagePreviewsTab

    def create_saved_processing_queue_list_layout(self):
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
        
    def create_model_settings_layout(self):
        m_group = QGroupBox("Model Selection: ", self)
        m_layout = QHBoxLayout()

        self.model_option_combo = QComboBox(self)
        self.model_option_combo.addItems(["LASCOZ", "ESRGAN", "ESRGAN 2"])
        m_layout.addWidget(QLabel("Model Option:"))
        m_layout.addWidget(self.model_option_combo)

        m_group.setLayout(m_layout)
        return m_layout

    def create_scale_settings_layout(self):
        h_group = QGroupBox("Scale Settings: ", self)
        h_layout = QHBoxLayout()

        self.scale_factor_combo = QComboBox(self)
        self.scale_factor_combo.addItems(["1.5x", "2x", "4x", "6x", "8x"])

        self.scale_factor_combo.setToolTip(
            "Sets the scale factor to process with when upscaling/downscaling images.")

        self.scale_factor = self.scale_factor_combo.itemText(0)
        self.scale_factor_combo.currentTextChanged.connect(self.on_scale_factor_changed)
        h_layout.addWidget(QLabel("Scale Factor:"))
        h_layout.addWidget(self.scale_factor_combo)

        h_group.setLayout(h_layout)
        return h_group
		
    def create_upscale_model_option(self):
        pass

    def create_save_dir_settings_layout(self):
        all_save_dir_group = QGroupBox("Save Settings Options: ", self)
        all_save_dir_layout = QHBoxLayout()

        self.change_save_dir_btn = QPushButton('Change Save Directory', self)
        self.change_save_dir_btn.clicked.connect(self.change_save_directory)

        self.change_save_dir_btn.setToolTip(
            "Sets the directory path that new images will be saved at upon completion of file processing. Default is the directory where this script resides.")

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

        process_btn.setMinimumHeight(50)
        process_button_group.setMinimumHeight(50)

        process_button_group.setLayout(process_button_layout)
        return process_button_group

    def create_file_info_panel_layout(self):
        file_info_control_group = QGroupBox(self)
        file_info_control_layout = QVBoxLayout()

        self.file_info_panel = QLabel("File Information:", self)
        file_info_control_layout.addWidget(self.file_info_panel)

        self.file_info_list = QListWidget(self)
        self.file_info_list.setSelectionMode(QListWidget.ExtendedSelection)
        file_info_control_layout.addWidget(self.file_info_list)

        self.file_info_list.setMinimumWidth(200)
        self.file_info_list.setMinimumHeight(200)

        self.total_info_label = QLabel("Total Files: 0, Total Size: 0.00 MB", self)
        file_info_control_layout.addWidget(self.total_info_label)

        add_btn = QPushButton('Add Images', self)
        add_btn.clicked.connect(self.add_images)
        file_info_control_layout.addWidget(add_btn)

        remove_btn = QPushButton('Remove Selected Image', self)
        remove_btn.clicked.connect(self.remove_selected_image)
        file_info_control_layout.addWidget(remove_btn)

        add_btn.setMinimumHeight(50)
        remove_btn.setMinimumHeight(50)

        file_info_control_group.setLayout(file_info_control_layout)
        return file_info_control_group

    def create_processing_queue_control_panel_layout(self):
        queue_control_group = QGroupBox(self)
        queue_control_layout = QVBoxLayout()

        self.processing_queue_panel = QLabel("Processing Queue List:", self)
        queue_control_layout.addWidget(self.processing_queue_panel)

        self.processing_queue_list = QListWidget(self)
        self.processing_queue_list.setSelectionMode(QListWidget.ExtendedSelection)
        queue_control_layout.addWidget(self.processing_queue_list)

        self.processing_queue_list.setMinimumWidth(200)
        self.processing_queue_list.setMinimumHeight(200)

        self.total_processing_queue_label = QLabel("Total Files: 0, Total Size: 0.00 MB", self)
        queue_control_layout.addWidget(self.total_processing_queue_label)

        add_to_queue_btn = QPushButton('Add to Queue', self)
        add_to_queue_btn.clicked.connect(self.add_to_processing_queue)
        queue_control_layout.addWidget(add_to_queue_btn)

        remove_from_queue_btn = QPushButton('Remove from Queue', self)
        remove_from_queue_btn.clicked.connect(self.remove_from_queue)
        queue_control_layout.addWidget(remove_from_queue_btn)

        add_to_queue_btn.setMinimumHeight(50)
        remove_from_queue_btn.setMinimumHeight(50)

        queue_control_group.setLayout(queue_control_layout)
        return queue_control_group

    def create_image_preview_section_layout(self):
        preview_widget_group = QGroupBox("Image Preview Panel: ", self)

        preview_widget = QWidget()
        self.preview_layout = QGridLayout(preview_widget)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(preview_widget)

        scroll_area.setMinimumWidth(250)
        scroll_area.setMinimumHeight(250)

        preview_layout = QVBoxLayout()
        preview_layout.addWidget(scroll_area)

        preview_widget_group.setLayout(preview_layout)

        return preview_widget_group

    def create_progress_bar_layout(self):
        progress_bar_group = QGroupBox(self)
        progress_bar_layout = QGridLayout()

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(30, 40, 200, 25)
        progress_bar_layout.addWidget(self.progress_bar)
        self.progress_bar.setHidden(True)

        progress_bar_group.setLayout(progress_bar_layout)

        return progress_bar_group

    def processing_logic(self):
        self.processing_mode = ('upscale' if self.upscale_btn.isChecked() else
                                'downscale' if self.downscale_btn.isChecked() else
                                'convert' if self.convert_btn.isChecked() else
                                None)

    def on_scale_factor_changed(self, text):
        self.scale_factor = text

    def on_convert_from_format_changed(self, text):
        self.convert_from_format = text.split('/')[0]

    def on_convert_to_format_changed(self, text):
        self.convert_to_format = text.split('/')[0]

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

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        existing_paths = {self.file_info_list.item(i).fullPath for i in range(self.file_info_list.count())}

        for file_path in files:
            if file_path not in existing_paths:
                fileName = os.path.basename(file_path)
                fileType = os.path.splitext(fileName)[1]
                fileSize = os.path.getsize(file_path)

                newItem = imageItem(fileName, file_path)
                newItem.fileType = fileType
                newItem.fileSize = fileSize

                self.file_info_list.addItem(newItem)
                existing_paths.add(file_path)
            else:
                print(f"Duplicate file skipped: {file_path}")
        self.update_file_info_list()

    def remove_selected_image(self):
        for item in self.file_info_list.selectedItems():
            self.file_info_list.takeItem(self.file_info_list.row(item))

    def update_file_info_list(self):
        total_size = 0
        for i in range(self.file_info_list.count()):
            image_item = self.file_info_list.item(i)
            if isinstance(image_item, imageItem):
                total_size += image_item.fileSize
            else:
                print(f"The item at index {i} is not an instance of imageItem.")

        total_size_mb = total_size / (1024 * 1024)
        self.total_info_label.setText(
            f"Total Files: {self.file_info_list.count()}, Total Size: {total_size_mb:.2f} MB"
        )

    def add_to_processing_queue(self):
        selected_items = self.file_info_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one file to add to the queue.")
            return

        existing_paths = [self.processing_queue_list.item(i).fullPath for i in range(self.processing_queue_list.count())
                          if isinstance(self.processing_queue_list.item(i), imageItem)]

        for item in selected_items:
            if isinstance(item, imageItem) and item.fullPath not in existing_paths:
                fileName = item.fileName
                fileType = item.fileType
                fileSize = item.fileSize

                newItem = imageItem(item.fileName, item.fullPath)
                newItem.fileType = fileType
                newItem.fileSize = fileSize
                self.processing_queue_list.addItem(newItem)
                existing_paths.append(item.fullPath)
            elif isinstance(item, imageItem):
                QMessageBox.warning(self, "Duplicate", f"The file {item.fileName} is already in the queue.")

        self.update_processing_queue_label()

    def remove_from_queue(self):
        selected_items = self.processing_queue_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select at least one file to remove from the queue.")
            return

        for item in selected_items:
            self.processing_queue_list.takeItem(self.processing_queue_list.row(item))

        self.update_processing_queue_label()

    def remove_from_queue_by_item(self, file_path):
        for i in range(self.processing_queue_list.count()):
            item = self.processing_queue_list.item(i)
            if item.fullPath == file_path:  # Compare file paths
                self.processing_queue_list.takeItem(i)
                return

    def update_processing_queue_label(self):
        total_size = 0
        for i in range(self.processing_queue_list.count()):
            image_item = self.processing_queue_list.item(i)
            if isinstance(image_item, imageItem):
                total_size += image_item.fileSize
            else:
                print(f"The item at index {i} is not an instance of imageItem.")

        total_size_mb = total_size / (1024 * 1024)
        self.total_processing_queue_label.setText(
            f"Total Files: {self.processing_queue_list.count()}, Total Size: {total_size_mb:.2f} MB"
        )

    def get_saved_queue_items(self):
        return [self.saved_queue_list.item(i) for i in range(self.saved_queue_list.count())
                if isinstance(self.saved_queue_list.item(i), imageItem)]

    def add_to_saved_queue(self, image_item, operation_suffix):
        existing_items = self.get_saved_queue_items()
        if not any(item.fullPath == image_item.fullPath for item in existing_items):
            saved_image_item_name = self.generate_display_name(image_item, operation_suffix)
            saved_image_item = imageItem(saved_image_item_name, image_item.fullPath)
            saved_image_item.fileType = image_item.fileType
            saved_image_item.fileSize = image_item.fileSize
            self.saved_queue_list.addItem(saved_image_item)

    def generate_display_name(self, image_item, operation_suffix):
        base_filename = image_item.fileName
        name, ext = os.path.splitext(base_filename)
        return f"{name}{operation_suffix}{ext}"

    def process_queue(self):
        imagesToProcess = [self.processing_queue_list.item(i) for i in range(self.processing_queue_list.count())]
        if self.worker is None or not self.worker.isRunning():
            self.prepare_worker(
                imagesToProcess, self.processing_mode, self.save_directory,
                self.scale_factor, self.convert_from_format, self.convert_to_format
            )
            self.progress_bar.show()
            self.worker.start()
        else:
            print("A processing task is already running.")

    def file_processed(self, image_item, operation_suffix):
        for i in range(self.processing_queue_list.count()):
            processing_item = self.processing_queue_list.item(i)
            if processing_item == image_item:
                self.processing_queue_list.takeItem(i)
                break

        self.add_to_saved_queue(image_item, operation_suffix)
        self.update_processing_queue_label()
        self.update_image_preview()

    def update_image_preview(self):
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for i in range(self.saved_queue_list.count()):
            saved_item = self.saved_queue_list.item(i)
            pixmap = QPixmap(saved_item.fullPath)
            scaled_pixmap = pixmap.scaled(PREVIEW_IMAGE_WIDTH, PREVIEW_IMAGE_HEIGHT, Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation)
            label = QLabel()
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignCenter)
            label.setMargin(MARGIN)
            self.preview_layout.addWidget(label)

    def on_all_files_processed(self, all_processed):
        if all_processed:
            self.progress_bar.hide()
            self.show_processing_complete_dialog()

    def update_progress_bar(self, value):
        if hasattr(self, 'progress_bar') and self.progress_bar is not None:
            self.progress_bar.setValue(value)

    def show_processing_complete_dialog(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Processing complete.")
        msg_box.setWindowTitle("Done")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.buttonClicked.connect(msg_box.hide)
        msg_box.exec_()

def main():
    app = QApplication(sys.argv)
    style = 'Windows'
    app.setStyleSheet(Path('main.qss').read_text())
    ex = ImageProcessor()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
