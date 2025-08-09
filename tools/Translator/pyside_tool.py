import os, sys, json, pandas as pd, io, requests
from zipfile import ZipFile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QLineEdit, QComboBox, QTableView, QAbstractItemView, QMessageBox, QTabWidget, QTextEdit
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import QObject, QThread, Signal, Qt

class TranslatorWorker(QObject):
    finished = Signal(dict)
    progress = Signal(str)
    error = Signal(str)

    def __init__(self, model, base_files, target_files, target_lang):
        super().__init__()
        self.model = model
        self.base_files = base_files
        self.target_files = target_files
        self.target_lang = target_lang
        self.api_url = "http://localhost:11434/api/chat"

    def run(self):
        try:
            all_optimized_data = {}
            for filename, base_content in self.base_files.items():
                if filename not in self.target_files:
                    continue

                self.progress.emit(f"正在处理 {filename}...")
                target_content = self.target_files[filename]
                optimized_file_content = {}

                for key, base_value in base_content.items():
                    original_translation = target_content.get(key)

                    if original_translation is None or original_translation == "【缺失】":
                        prompt = f'TARGET LANGUAGE: {self.target_lang}\nPAGE CONTEXT: {filename}\nSOURCE (English): "{base_value}"'
                    else:
                        prompt = f'TARGET LANGUAGE: {self.target_lang}\nPAGE CONTEXT: {filename}\nSOURCE (English): "{base_value}"\nCURRENT ({self.target_lang}): "{original_translation}"'

                    response = requests.post(
                        self.api_url,
                        json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": False},
                        timeout=120
                    )
                    response.raise_for_status()
                    ai_result = response.json()['message']['content']

                    cleaned_result = ai_result.strip().strip('"').strip("'")
                    optimized_file_content[key] = cleaned_result

                all_optimized_data[filename] = optimized_file_content
            self.finished.emit(all_optimized_data)
        except requests.exceptions.RequestException as e:
            self.error.emit(f"调用AI失败: {e}")
        except Exception as e:
            self.error.emit(f"处理时出错: {e}")

class TranslatorWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.base_files_content = {}
        self.target_files_content = {}
        self.ai_results = {}

        # --- Base UI ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        title = QLabel("文案优化工具"); title.setObjectName("title")
        main_layout.addWidget(title)
        main_layout.addWidget(QLabel("本工具以本地EN文件夹为基准，利用AI优化和修正您上传的目标语言文件夹中的文案。"))

        # --- Step 1: Load Base Files ---
        self.load_status_label = QLabel("正在加载基准文件...")
        main_layout.addWidget(self.load_status_label)
        self._load_base_files()

        # --- Step 2: Target Language ---
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("<b>1. 目标语言:</b>"))
        self.target_lang_input = QLineEdit("Chinese")
        lang_layout.addWidget(self.target_lang_input)
        main_layout.addLayout(lang_layout)

        # --- Step 3: Upload Target Files ---
        main_layout.addWidget(QLabel("<b>2. 上传待优化文件:</b>"))
        self.upload_button = QPushButton("📂 选择待优化的JSON文件...")
        self.upload_button.clicked.connect(self.select_target_files)
        self.upload_status_label = QLabel("尚未选择文件。")
        main_layout.addWidget(self.upload_button)
        main_layout.addWidget(self.upload_status_label)

        # --- Step 4: Preview and Run ---
        main_layout.addWidget(QLabel("<b>3. 预览与执行:</b>"))
        self.preview_selector = QComboBox()
        self.preview_selector.currentTextChanged.connect(self.update_preview)
        self.preview_table = QTableView()
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.run_button = QPushButton("🚀 使用AI批量优化所有匹配的文件")
        self.run_button.clicked.connect(self.run_ai_optimization)
        self.run_status = QTextEdit()
        self.run_status.setReadOnly(True)
        self.run_status.setFixedHeight(100)

        main_layout.addWidget(self.preview_selector)
        main_layout.addWidget(self.preview_table)
        main_layout.addWidget(self.run_button)
        main_layout.addWidget(self.run_status)

        # --- Step 5: Results ---
        main_layout.addWidget(QLabel("<b>4. 审查并保存结果:</b>"))
        self.results_tabs = QTabWidget()
        self.save_button = QPushButton("📥 下载包含所有优化后文件的 .zip 包")
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        main_layout.addWidget(self.results_tabs, 1) # Give it stretch factor
        main_layout.addWidget(self.save_button)

    def _load_base_files(self):
        try:
            base_path = os.path.join(os.path.dirname(__file__), "data", "en")
            if not os.path.exists(base_path): raise FileNotFoundError(f"基准文件夹 '{base_path}' 不存在。")

            for filename in os.listdir(base_path):
                if filename.endswith('.json'):
                    with open(os.path.join(base_path, filename), 'r', encoding='utf-8') as f:
                        self.base_files_content[filename] = json.load(f)

            if not self.base_files_content: raise ValueError("在基准文件夹中没有找到任何.json文件。")
            self.load_status_label.setText(f"✅ 已成功加载 {len(self.base_files_content)} 个基准 (EN) 文件！")
        except Exception as e:
            self.load_status_label.setText(f"❌ 加载基准文件失败: {e}")
            QMessageBox.critical(self, "错误", f"加载基准文件失败: {e}")

    def select_target_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择目标语言的JSON文件", "", "JSON Files (*.json)")
        if not files: return

        self.target_files_content = {}
        for file_path in files:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.target_files_content[filename] = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "读取错误", f"读取文件 {filename} 失败: {e}")

        common_files = sorted(list(self.base_files_content.keys() & self.target_files_content.keys()))
        self.preview_selector.clear()
        if common_files:
            self.upload_status_label.setText(f"已选择 {len(files)} 个文件，其中 {len(common_files)} 个与基准文件匹配。")
            self.preview_selector.addItems(common_files)
        else:
            self.upload_status_label.setText("上传的文件中没有找到与基准文件同名的JSON文件。")

    def update_preview(self, filename):
        if not filename: return
        base_data = self.base_files_content.get(filename, {})
        target_data = self.target_files_content.get(filename, {})

        df = pd.DataFrame([
            {"Key": key, "基准文案 (EN)": base_value, f"当前文案 ({self.target_lang_input.text()})": target_data.get(key, "【缺失】")}
            for key, base_value in base_data.items()
        ])

        model = QStandardItemModel(df.shape[0], df.shape[1])
        model.setHorizontalHeaderLabels(df.columns)
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                model.setItem(row, col, QStandardItem(str(df.iloc[row, col])))
        self.preview_table.setModel(model)
        self.preview_table.resizeColumnsToContents()

    def run_ai_optimization(self):
        if not self.target_files_content:
            QMessageBox.warning(self, "提示", "请先选择要优化的文件。"); return

        self.run_button.setEnabled(False)
        self.run_status.setText("正在准备调用AI...")

        model = "llama3.1:latest"
        if self.main_window and hasattr(self.main_window, 'get_selected_model'):
            model = self.main_window.get_selected_model()
        self.run_status.append(f"使用模型: {model}")

        self.thread = QThread()
        self.worker = TranslatorWorker(model, self.base_files_content, self.target_files_content, self.target_lang_input.text())
        self.worker.moveToThread(self.thread)
        self.worker.progress.connect(lambda msg: self.run_status.append(msg))
        self.worker.error.connect(self.on_ai_error)
        self.worker.finished.connect(self.on_ai_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_ai_error(self, msg):
        self.run_button.setEnabled(True)
        self.run_status.append(f"错误: {msg}")
        QMessageBox.critical(self, "AI处理出错", msg)

    def on_ai_finished(self, results):
        self.run_button.setEnabled(True)
        self.run_status.append("✅ AI优化完成！请在下方审查结果。")
        self.ai_results = results
        self.save_button.setEnabled(True)
        self.display_results()

    def display_results(self):
        self.results_tabs.clear()
        for filename, optimized_data in self.ai_results.items():
            tab = QWidget()
            layout = QVBoxLayout(tab)
            table = QTableView()
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            layout.addWidget(table)

            base_data = self.base_files_content.get(filename, {})
            target_data = self.target_files_content.get(filename, {})

            df = pd.DataFrame([{
                "Key": key, "基准 (EN)": base_value,
                f"原始 ({self.target_lang_input.text()})": target_data.get(key, "【缺失】"),
                f"AI优化后 ({self.target_lang_input.text()})": optimized_data.get(key)
            } for key, base_value in base_data.items()])

            model = QStandardItemModel(df.shape[0], df.shape[1])
            model.setHorizontalHeaderLabels(df.columns)
            for row in range(df.shape[0]):
                for col in range(df.shape[1]):
                    model.setItem(row, col, QStandardItem(str(df.iloc[row, col])))
            table.setModel(model)
            table.resizeColumnsToContents()
            self.results_tabs.addTab(tab, filename)

    def save_results(self):
        if not self.ai_results: return

        path, _ = QFileDialog.getSaveFileName(self, "保存为 Zip 文件", "", "Zip Files (*.zip)")
        if not path: return

        try:
            with ZipFile(path, 'w') as zip_file:
                for filename, content_dict in self.ai_results.items():
                    zip_file.writestr(filename, json.dumps(content_dict, ensure_ascii=False, indent=4))
            QMessageBox.information(self, "成功", f"结果已成功保存到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存Zip文件时出错: {e}")
