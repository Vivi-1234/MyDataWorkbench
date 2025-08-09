# 文件路径: MyDataWorkbench/tools/MulebuyPics/pyside_tool.py

import os
import shutil
import sys
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QTabWidget, QScrollArea, QGridLayout, QCheckBox,
    QMessageBox, QLineEdit, QComboBox, QGroupBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QSize, QThread, Signal, QObject

# --- Configuration ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_PATH, "data")
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
THUMBNAIL_SIZE = 160

# --- Custom Thumbnail Widget ---
class ThumbnailWidget(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.checkbox = QCheckBox()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.checkbox, alignment=Qt.AlignHCenter)
        layout.addWidget(self.image_label)

        # Load pixmap
        pixmap = QPixmap(image_path)
        self.image_label.setPixmap(pixmap.scaled(THUMBNAIL_SIZE, THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))

# --- Main Widget ---
class MulebuyPicsWidget(QWidget):
    def __init__(self):
        super().__init__()
        os.makedirs(DATA_PATH, exist_ok=True)

        main_layout = QHBoxLayout(self)
        sidebar = self.create_sidebar()
        self.tab_widget = QTabWidget()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.tab_widget, 1)

        self.refresh_all()

    def create_sidebar(self):
        # (Same as before, omitted for brevity but is included in the file)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_widget.setFixedWidth(250)

        upload_group = QGroupBox("📁 上传新图片")
        upload_layout = QVBoxLayout(upload_group)
        self.upload_category_combo = QComboBox()
        self.upload_button = QPushButton("选择图片上传")
        self.upload_button.clicked.connect(self.upload_images)
        upload_layout.addWidget(QLabel("选择上传目标:"))
        upload_layout.addWidget(self.upload_category_combo)
        upload_layout.addWidget(self.upload_button)

        cat_manage_group = QGroupBox("🗂️ 分类管理")
        cat_manage_layout = QVBoxLayout(cat_manage_group)
        self.new_cat_input = QLineEdit(); self.new_cat_input.setPlaceholderText("输入新分类名称")
        create_cat_button = QPushButton("创建分类"); create_cat_button.clicked.connect(self.create_category)
        self.manage_cat_combo = QComboBox()
        self.manage_cat_combo.currentIndexChanged.connect(lambda i: self.rename_cat_input.setText(self.manage_cat_combo.currentText()))
        self.rename_cat_input = QLineEdit()
        rename_cat_button = QPushButton("重命名选中分类"); rename_cat_button.clicked.connect(self.rename_category)
        delete_cat_button = QPushButton("删除选中分类"); delete_cat_button.clicked.connect(self.delete_category)

        cat_manage_layout.addWidget(self.new_cat_input); cat_manage_layout.addWidget(create_cat_button)
        cat_manage_layout.addSpacing(15); cat_manage_layout.addWidget(QLabel("管理现有分类:"))
        cat_manage_layout.addWidget(self.manage_cat_combo); cat_manage_layout.addWidget(self.rename_cat_input)
        cat_manage_layout.addWidget(rename_cat_button); cat_manage_layout.addWidget(delete_cat_button)

        sidebar_layout.addWidget(upload_group); sidebar_layout.addWidget(cat_manage_group)
        sidebar_layout.addStretch()
        return sidebar_widget

    def refresh_all(self):
        self.categories = sorted([d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))])
        self.upload_category_combo.clear(); self.upload_category_combo.addItems(["未分类"] + self.categories)
        self.manage_cat_combo.clear(); self.manage_cat_combo.addItems(self.categories)
        self.tab_widget.clear()
        self.create_gallery_tabs()

    def create_gallery_tabs(self):
        uncategorized_images = sorted([f for f in os.listdir(DATA_PATH) if os.path.isfile(os.path.join(DATA_PATH, f)) and f.lower().endswith(SUPPORTED_FORMATS)])
        self.add_gallery_tab("未分类", uncategorized_images, DATA_PATH)
        for category in self.categories:
            category_path = os.path.join(DATA_PATH, category)
            image_files = sorted([f for f in os.listdir(category_path) if f.lower().endswith(SUPPORTED_FORMATS)])
            self.add_gallery_tab(category, image_files, category_path)

    def add_gallery_tab(self, name, image_files, path):
        tab_content_widget = QWidget()
        tab_layout = QVBoxLayout(tab_content_widget)

        # --- Bulk Actions Toolbar ---
        toolbar = self.create_bulk_actions_toolbar(name)
        tab_layout.addWidget(toolbar)

        # --- Image Grid ---
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True)
        grid_widget = QWidget(); grid_layout = QGridLayout(grid_widget)
        grid_layout.setAlignment(Qt.AlignTop)

        for i, fname in enumerate(image_files):
            thumb = ThumbnailWidget(os.path.join(path, fname))
            grid_layout.addWidget(thumb, i // 4, i % 4)

        scroll_area.setWidget(grid_widget)
        tab_layout.addWidget(scroll_area)
        self.tab_widget.addTab(tab_content_widget, f"{name} ({len(image_files)})")

    def create_bulk_actions_toolbar(self, category_name):
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        select_all_check = QCheckBox("全选")
        select_all_check.stateChanged.connect(lambda state: self.select_all_in_current_tab(state == Qt.Checked))

        delete_button = QPushButton("🗑️ 删除选中")
        delete_button.clicked.connect(self.bulk_delete)

        move_combo = QComboBox()

        move_button = QPushButton("执行移动")
        move_button.clicked.connect(lambda: self.bulk_move(move_combo.currentText()))

        toolbar_layout.addWidget(select_all_check)
        toolbar_layout.addWidget(delete_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(QLabel("移动到:"))
        toolbar_layout.addWidget(move_combo)
        toolbar_layout.addWidget(move_button)

        # Store combo box to update it later
        toolbar_widget.setProperty("move_combo", move_combo)
        return toolbar_widget

    def get_current_thumbnails(self):
        current_tab = self.tab_widget.currentWidget()
        if not current_tab: return []
        return current_tab.findChildren(ThumbnailWidget)

    def select_all_in_current_tab(self, checked):
        for thumb in self.get_current_thumbnails():
            thumb.checkbox.setChecked(checked)

    def get_selected_thumbnails(self):
        return [thumb for thumb in self.get_current_thumbnails() if thumb.checkbox.isChecked()]

    def bulk_delete(self):
        selected = self.get_selected_thumbnails()
        if not selected: return
        reply = QMessageBox.question(self, "确认删除", f"确定要永久删除选中的 {len(selected)} 张图片吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for thumb in selected: os.remove(thumb.image_path)
            self.refresh_all()

    def bulk_move(self, target_category):
        selected = self.get_selected_thumbnails()
        if not selected or not target_category or target_category == "--移动到--": return

        target_path = DATA_PATH if target_category == "未分类" else os.path.join(DATA_PATH, target_category)
        for thumb in selected:
            shutil.move(thumb.image_path, os.path.join(target_path, os.path.basename(thumb.image_path)))
        self.refresh_all()

    def upload_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", f"Images ({' '.join(['*' + ext for ext in SUPPORTED_FORMATS])})")
        if not files: return
        target_category = self.upload_category_combo.currentText()
        save_path = DATA_PATH if target_category == "未分类" else os.path.join(DATA_PATH, target_category)
        for file in files: shutil.copy(file, os.path.join(save_path, os.path.basename(file)))
        QMessageBox.information(self, "成功", f"成功上传 {len(files)} 个文件到 '{target_category}'！")
        self.refresh_all()

    def create_category(self):
        name = self.new_cat_input.text().strip()
        if not name or name in self.categories: QMessageBox.warning(self, "无效操作", "请输入一个有效且不重复的分类名称。"); return
        os.makedirs(os.path.join(DATA_PATH, name)); self.new_cat_input.clear(); self.refresh_all()

    def rename_category(self):
        old_name = self.manage_cat_combo.currentText(); new_name = self.rename_cat_input.text().strip()
        if not all([old_name, new_name]) or old_name == new_name: QMessageBox.warning(self, "无效操作", "请选择一个分类并提供一个不同的新名称。"); return
        os.rename(os.path.join(DATA_PATH, old_name), os.path.join(DATA_PATH, new_name)); self.refresh_all()

    def delete_category(self):
        name = self.manage_cat_combo.currentText()
        if not name: return
        cat_path = os.path.join(DATA_PATH, name)
        if os.listdir(cat_path): QMessageBox.warning(self, "无法删除", "该分类下仍有图片，请先将其移出或删除。"); return
        if QMessageBox.question(self, "确认删除", f"确定要永久删除分类 '{name}' 吗？", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            shutil.rmtree(cat_path); self.refresh_all()

    def tab_widget(self):
        return self.parent().findChild(QTabWidget)

    def on_tab_changed(self, index):
        if index < 0: return
        current_tab_widget = self.tab_widget.widget(index)
        move_combo = current_tab_widget.findChild(QComboBox)
        if not move_combo: return

        current_cat_name = self.tab_widget.tabText(index).split(' ')[0]

        move_options = ["--移动到--"] + [cat for cat in self.categories if cat != current_cat_name]
        if current_cat_name != "未分类":
            move_options.insert(1, "未分类")

        move_combo.clear()
        move_combo.addItems(move_options)

    def showEvent(self, event):
        # Override showEvent to connect the signal after the UI is fully constructed
        try:
            self.tab_widget.currentChanged.disconnect()
        except RuntimeError:
            pass # was not connected
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.on_tab_changed(self.tab_widget.currentIndex()) # Manually trigger for the first tab
        super().showEvent(event)
