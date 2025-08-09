# 文件路径: MyDataWorkbench/tools/Translator/pyside_tool.py

import os
import sys
import json
import pandas as pd
import io
import requests
from zipfile import ZipFile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QComboBox, QTableView, QTabWidget, QMessageBox, QGroupBox
)
from PySide6.QtCore import QThread, QObject, Signal, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

# --- Backend Logic ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_DATA_PATH = os.path.join(BASE_PATH, "data", "en")

def _load_base_files_from_disk(base_path):
    if not os.path.exists(base_path): return None, f"错误：基准文件夹 '{base_path}' 不存在。"
    base_files_content = {}
    try:
        for filename in os.listdir(base_path):
            if filename.endswith('.json'):
                with open(os.path.join(base_path, filename), 'r', encoding='utf-8') as f:
                    base_files_content[filename] = json.load(f)
        return base_files_content, None
    except Exception as e: return None, f"读取基准文件时出错: {e}"

def _ai_assisted_translation(model_to_use, page_name, base_text, original_translation, target_lang):
    prompt = f"TARGET LANGUAGE: {target_lang}\nPAGE CONTEXT: {page_name}\nSOURCE (English): \"{base_text}\""
    if original_translation and original_translation != "【缺失】":
        prompt += f"\nCURRENT ({target_lang}): \"{original_translation}\""
    try:
        response = requests.post("http://localhost:11434/api/chat", json={"model": model_to_use, "messages": [{"role": "user", "content": prompt}], "stream": False}, timeout=120)
        response.raise_for_status()
        ai_result = response.json()['message']['content'].strip()
        return ai_result.strip('\'"')
    except requests.exceptions.RequestException as e:
        return f"【AI调用失败: {e}】"

class TranslationWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, model, lang, base_content, target_files_content):
        super().__init__()
        self.model = model
        self.lang = lang
        self.base_content = base_content
        self.target_files_content = target_files_content

    def run(self):
        all_optimized_data = {}
        try:
            for filename, base_data in self.base_content.items():
                if filename not in self.target_files_content: continue
                target_data = self.target_files_content[filename]
                optimized_file_content = {}
                for key, base_value in base_data.items():
                    optimized_text = _ai_assisted_translation(self.model, filename, base_value, target_data.get(key), self.lang)
                    optimized_file_content[key] = optimized_text
                all_optimized_data[filename] = optimized_file_content
            self.finished.emit(all_optimized_data)
        except Exception as e:
            self.error.emit(f"AI处理时发生意外错误: {e}")

class PandasModel(QStandardItemModel):
    def __init__(self, data):
        super().__init__()
        for i, row in data.iterrows():
            for j, val in enumerate(row):
                self.setItem(i, j, QStandardItem(str(val)))
        self.setHorizontalHeaderLabels(data.columns)

class TranslatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.base_files_content, error_msg = _load_base_files_from_disk(BASE_DATA_PATH)
        self.target_files_content = {}
        self.ai_results = {}

        layout = QVBoxLayout(self)
        if error_msg: layout.addWidget(QLabel(error_msg)); return

        # --- Step 1: Input ---
        input_group = QGroupBox("1. 输入和上传")
        input_layout = QVBoxLayout(input_group)
        self.lang_input = QLineEdit("Chinese"); self.lang_input.setPlaceholderText("例如: German, Spanish, Japanese")
        upload_button = QPushButton("上传待优化文件 (JSON)"); upload_button.clicked.connect(self.upload_files)
        input_layout.addWidget(QLabel("目标语言全称:"))
        input_layout.addWidget(self.lang_input)
        input_layout.addWidget(upload_button)

        # --- Step 2: Preview ---
        preview_group = QGroupBox("2. 预览和执行")
        self.preview_layout = QVBoxLayout(preview_group)
        self.file_combo = QComboBox(); self.file_combo.currentTextChanged.connect(self.update_preview)
        self.preview_table = QTableView(); self.preview_table.setEditTriggers(QTableView.NoEditTriggers)
        self.run_ai_button = QPushButton("🚀 使用AI批量优化所有匹配的文件"); self.run_ai_button.clicked.connect(self.run_ai_optimization)
        self.preview_layout.addWidget(self.file_combo)
        self.preview_layout.addWidget(self.preview_table)
        self.preview_layout.addWidget(self.run_ai_button)

        # --- Step 3: Review ---
        review_group = QGroupBox("3. 结果审查和下载")
        self.review_layout = QVBoxLayout(review_group)
        self.review_tabs = QTabWidget()
        self.download_button = QPushButton("📥 下载包含所有优化后文件的 .zip 包"); self.download_button.clicked.connect(self.download_zip)
        self.review_layout.addWidget(self.review_tabs)
        self.review_layout.addWidget(self.download_button)

        layout.addWidget(input_group)
        layout.addWidget(preview_group)
        layout.addWidget(review_group)

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择JSON文件", "", "JSON Files (*.json)")
        if not files: return
        self.target_files_content = {}
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    self.target_files_content[os.path.basename(file)] = json.load(f)
            except Exception as e: QMessageBox.warning(self, "读取错误", f"无法读取文件 {os.path.basename(file)}: {e}"); return

        common_files = sorted(list(self.base_files_content.keys() & self.target_files_content.keys()))
        self.file_combo.clear(); self.file_combo.addItems(common_files)
        QMessageBox.information(self, "成功", f"文件加载成功！共找到 {len(common_files)} 个同名文件可供处理。")

    def update_preview(self, filename):
        if not filename: return
        base_data = self.base_files_content[filename]
        target_data = self.target_files_content[filename]
        df = pd.DataFrame([{"Key": k, "基准文案 (EN)": v, f"当前文案 ({self.lang_input.text()})": target_data.get(k, "【缺失】")} for k, v in base_data.items()])
        self.preview_table.setModel(PandasModel(df)); self.preview_table.resizeColumnsToContents()

    def run_ai_optimization(self):
        # This should get the model from the main window, but for now, it's hardcoded.
        # In a real app, you'd pass the main window instance or use a signal/slot mechanism.
        model = "mulebuy-optimizer"
        self.run_ai_button.setEnabled(False); self.run_ai_button.setText("处理中...")

        self.thread = QThread()
        self.worker = TranslationWorker(model, self.lang_input.text(), self.base_files_content, self.target_files_content)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_ai_finished)
        self.worker.error.connect(self.on_ai_error)
        self.thread.start()

    def on_ai_error(self, err_msg):
        self.run_ai_button.setEnabled(True); self.run_ai_button.setText("🚀 使用AI批量优化所有匹配的文件")
        QMessageBox.critical(self, "AI 错误", err_msg)
        self.thread.quit(); self.thread.wait()

    def on_ai_finished(self, results):
        self.ai_results = results
        self.run_ai_button.setEnabled(True); self.run_ai_button.setText("🚀 使用AI批量优化所有匹配的文件")
        self.thread.quit(); self.thread.wait()
        QMessageBox.information(self, "完成", "AI优化完成！请在下方审查结果。")
        self.populate_review_tabs()

    def populate_review_tabs(self):
        self.review_tabs.clear()
        for filename, optimized_data in self.ai_results.items():
            base_data = self.base_files_content[filename]
            target_data = self.target_files_content[filename]
            df = pd.DataFrame([{"Key": k, "基准 (EN)": v, f"原始 ({self.lang_input.text()})": target_data.get(k, "【缺失】"), f"AI优化后 ({self.lang_input.text()})": optimized_data.get(k)} for k, v in base_data.items()])
            table = QTableView(); table.setModel(PandasModel(df)); table.resizeColumnsToContents()
            self.review_tabs.addTab(table, filename)

    def download_zip(self):
        if not self.ai_results: QMessageBox.warning(self, "无结果", "没有可供下载的AI优化结果。"); return
        path, _ = QFileDialog.getSaveFileName(self, "保存Zip文件", f"optimized_{self.lang_input.text()}_files.zip", "Zip Files (*.zip)")
        if not path: return
        with ZipFile(path, 'w') as zip_file:
            for filename, content in self.ai_results.items():
                zip_file.writestr(filename, json.dumps(content, ensure_ascii=False, indent=4))
        QMessageBox.information(self, "成功", f"优化后的文件已保存到 {path}")
