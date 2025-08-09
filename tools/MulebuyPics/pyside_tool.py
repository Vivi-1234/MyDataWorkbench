import os, shutil
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QListWidget,
    QFileDialog, QTabWidget, QScrollArea, QGridLayout, QCheckBox,
    QMessageBox, QLineEdit, QComboBox, QGroupBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class ThumbnailWidget(QWidget):
    def __init__(self, image_path):
        super().__init__(); self.image_path = image_path; self.setFixedSize(180, 200)
        layout = QVBoxLayout(self); layout.setContentsMargins(5,5,5,5)
        self.checkbox = QCheckBox(); self.image_label = QLabel(); self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.checkbox, 0, Qt.AlignHCenter); layout.addWidget(self.image_label, 1)
        pixmap = QPixmap(image_path); self.image_label.setPixmap(pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))

class MulebuyPicsWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__(); self.main_window = main_window
        self.DATA_PATH = os.path.join(os.path.dirname(__file__), "data"); os.makedirs(self.DATA_PATH, exist_ok=True)
        main_layout = QHBoxLayout(self); main_layout.setContentsMargins(10,10,10,10)
        main_layout.addWidget(self.create_sidebar()); main_layout.addWidget(self.create_main_area(), 1)
        self.refresh_all()

    def create_sidebar(self):
        sidebar = QWidget(); sidebar_layout = QVBoxLayout(sidebar); sidebar.setFixedWidth(250)
        # ... (full implementation of sidebar UI) ...
        return sidebar

    def create_main_area(self):
        main_area = QWidget(); layout = QVBoxLayout(main_area)
        self.tab_widget = QTabWidget(); self.tab_widget.currentChanged.connect(self.populate_move_combo)
        # ... (full implementation of main area UI) ...
        layout.addWidget(self.tab_widget)
        return main_area

    def refresh_all(self): self.categories = sorted([d for d in os.listdir(self.DATA_PATH) if os.path.isdir(os.path.join(self.DATA_PATH, d))]); self.populate_sidebar_combos(); self.recreate_tabs()
    def populate_sidebar_combos(self):
        self.upload_category_combo.clear(); self.upload_category_combo.addItems(["未分类"] + self.categories)
        self.manage_cat_combo.clear(); self.manage_cat_combo.addItems(self.categories)
    def recreate_tabs(self):
        self.tab_widget.clear()
        # ... (logic to create all tabs and their content) ...
    # ... (all other methods for functionality)
