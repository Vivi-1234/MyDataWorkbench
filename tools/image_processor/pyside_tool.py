import os
import sys
import cv2
import shutil
import time
import requests
import numpy as np
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from collections import Counter

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar,
    QFileDialog, QSlider, QListWidget, QMessageBox, QStackedWidget,
    QTextEdit, QSizePolicy, QListWidgetItem
)
from PySide6.QtCore import QThread, QObject, Signal, Qt

# --- Configuration ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

class Config:
    INPUT_DIR = os.path.join(BASE_PATH, 'input')
    OUTPUT_DIR = os.path.join(BASE_PATH, 'output')
    TEMPLATE_DIR = os.path.join(BASE_PATH, 'templates')
    URL_FILE_PATH = os.path.join(INPUT_DIR, 'qc.txt')
    STATE_FILE_PATH = os.path.join(INPUT_DIR, 'state.json')
    PROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'processed_images')
    UNPROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'unprocessed_images')
    NUM_WORKERS = 15
    LOWER_RED1, UPPER_RED1 = np.array([0, 80, 80]), np.array([10, 255, 255])
    LOWER_RED2, UPPER_RED2 = np.array([160, 80, 80]), np.array([179, 255, 255])
    LOWER_WHITE, UPPER_WHITE = np.array([0, 0, 180]), np.array([179, 40, 255])
    MIN_RED_TO_WHITE_RATIO = 0.01
    MIN_TOTAL_AREA_RATIO = 0.002
    MIN_ASPECT_RATIO = 0.3
    MAX_ASPECT_RATIO = 7.0

# --- Backend Logic ---
def download_image(url):
    try:
        path_parts = urlparse(url).path.strip('/').split('/')
        if len(path_parts) < 3: return "url_error"
        dir_path = os.path.join(Config.UNPROCESSED_FOLDER, *path_parts[-3:-1])
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, path_parts[-1])
        if os.path.exists(file_path): return "skipped"
        response = requests.get(url, stream=True, timeout=20, verify=False)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(8192): f.write(chunk)
            return "success"
        return f"http_error_{response.status_code}"
    except requests.exceptions.RequestException: return "request_error"
    except Exception: return "error"

def check_for_logo_in_roi(hsv, roi_ratio):
    height, width, _ = hsv.shape
    y1, y2 = int(height * roi_ratio[0]), int(height * roi_ratio[1])
    x1, x2 = int(width * roi_ratio[2]), int(width * roi_ratio[3])
    red_mask = cv2.bitwise_or(cv2.inRange(hsv, Config.LOWER_RED1, Config.UPPER_RED1), cv2.inRange(hsv, Config.LOWER_RED2, Config.UPPER_RED2))
    white_mask = cv2.inRange(hsv, Config.LOWER_WHITE, Config.UPPER_WHITE)
    roi_isolated = np.zeros_like(red_mask); roi_isolated[y1:y2, x1:x2] = 255
    red_mask_roi = cv2.bitwise_and(red_mask, roi_isolated)
    white_mask_roi = cv2.bitwise_and(white_mask, roi_isolated)
    red_area = cv2.countNonZero(red_mask_roi)
    white_area = cv2.countNonZero(white_mask_roi)
    if white_area == 0 or (red_area / white_area < Config.MIN_RED_TO_WHITE_RATIO): return False
    logo_mask = cv2.bitwise_or(red_mask_roi, white_mask_roi)
    contours, _ = cv2.findContours(logo_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return False
    max_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_contour)
    _, _, bw, bh = cv2.boundingRect(max_contour)
    if (area / (height * width) < Config.MIN_TOTAL_AREA_RATIO or (bh > 0 and (bw / bh < Config.MIN_ASPECT_RATIO or bw / bh > Config.MAX_ASPECT_RATIO))): return False
    return True

def identify_and_move_task(source_path):
    try:
        img = cv2.imread(source_path)
        if img is None: return "load_fail"
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        logo_found = check_for_logo_in_roi(hsv, (0.75, 1.0, 0.0, 0.4)) or check_for_logo_in_roi(hsv, (0.0, 0.25, 0.6, 1.0))
        if logo_found: return "logo_found_stay"
        destination_path = source_path.replace(Config.UNPROCESSED_FOLDER, Config.PROCESSED_FOLDER, 1)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        shutil.move(source_path, destination_path)
        return "no_logo_moved"
    except Exception: return "error_stay"

templates_g = []
def init_template_worker():
    global templates_g
    templates_g.clear()
    if not os.path.exists(Config.TEMPLATE_DIR): return
    for f in os.listdir(Config.TEMPLATE_DIR):
        if f.lower().endswith(('.png', '.jpg')):
            img = cv2.imread(os.path.join(Config.TEMPLATE_DIR, f), cv2.IMREAD_GRAYSCALE)
            if img is not None: templates_g.append(img)

def match_and_cover(image, threshold):
    h, w = image.shape[:2]
    rois_to_check = [(0, h // 2, w // 2, w), (h // 2, 0, h, w // 2)] # Corrected ROI definitions
    for y1, x1, y2, x2 in rois_to_check:
        roi = image[y1:y2, x1:x2]; gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        for template in templates_g:
            th, tw = template.shape
            for scale in [1.2, 1.0, 0.8]:
                w_s, h_s = int(tw * scale), int(th * scale)
                if h_s <= 0 or w_s <= 0 or h_s > gray_roi.shape[0] or w_s > gray_roi.shape[1]: continue
                res = cv2.matchTemplate(gray_roi, cv2.resize(template, (w_s, h_s)), cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    top_left = (max_loc[0] + x1, max_loc[1] + y1)
                    bottom_right = (top_left[0] + w_s, top_left[1] + h_s)
                    cv2.rectangle(image, top_left, bottom_right, (0, 128, 0), -1)
                    return image, True
    return image, False

def process_template_task(source_path, threshold):
    processed_path = source_path.replace(Config.UNPROCESSED_FOLDER, Config.PROCESSED_FOLDER, 1)
    try:
        image = cv2.imread(source_path)
        if image is None: return "load_fail"
        processed_image, matched = match_and_cover(image, threshold)
        if matched:
            os.makedirs(os.path.dirname(processed_path), exist_ok=True)
            cv2.imwrite(processed_path, processed_image)
            if os.path.exists(source_path): os.remove(source_path)
            return "processed"
        return "unmatched"
    except Exception: return "error"

# --- Worker Classes ---
class BaseWorker(QObject):
    finished = Signal(dict)
    progress = Signal(int, int, dict)

    def run_with_executor(self, task_function, tasks, *args):
        results_counter = Counter()
        executor_class = ThreadPoolExecutor if task_function != identify_and_move_task else ProcessPoolExecutor
        with executor_class(max_workers=Config.NUM_WORKERS) as executor:
            futures = {executor.submit(task_function, task, *args) for task in tasks}
            total = len(futures)
            for i, future in enumerate(as_completed(futures)):
                try:
                    result = future.result()
                    results_counter[result] += 1
                except Exception as e:
                    results_counter['future_error'] += 1
                self.progress.emit(i + 1, total, dict(results_counter))
        self.finished.emit(dict(results_counter))

class DownloadWorker(BaseWorker):
    def run(self):
        if not os.path.exists(Config.URL_FILE_PATH):
            self.finished.emit({"error": "qc.txt not found"})
            return
        with open(Config.URL_FILE_PATH, 'r') as f:
            urls = list(dict.fromkeys([line.strip() for line in f if line.strip()]))
        for folder in [Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
            if os.path.exists(folder): shutil.rmtree(folder)
            os.makedirs(folder)
        self.run_with_executor(download_image, urls)

class FilterWorker(BaseWorker):
    def run(self):
        tasks = [os.path.join(dp, f) for dp, _, fn in os.walk(Config.UNPROCESSED_FOLDER) for f in fn if f.lower().endswith(('.jpg', '.png'))]
        if not tasks: self.finished.emit({}); return
        self.run_with_executor(identify_and_move_task, tasks)

class TemplateWorker(BaseWorker):
    def __init__(self, threshold):
        super().__init__()
        self.threshold = threshold

    def run(self):
        init_template_worker()
        tasks = [os.path.join(dp, f) for dp, _, fn in os.walk(Config.UNPROCESSED_FOLDER) for f in fn if f.lower().endswith(('.jpg', '.png'))]
        if not tasks: self.finished.emit({}); return
        self.run_with_executor(process_template_task, tasks, self.threshold)

class ValidationWorker(QObject):
    finished = Signal(list)
    def run(self):
        if not os.path.exists(Config.URL_FILE_PATH):
             self.finished.emit(["qc.txt not found"])
             return
        with open(Config.URL_FILE_PATH, 'r') as f:
            urls = list(dict.fromkeys([line.strip() for line in f if line.strip()]))
        missing = []
        for url in urls:
            try:
                path_parts = urlparse(url).path.strip('/').split('/')
                expected_path = os.path.join(Config.PROCESSED_FOLDER, *path_parts[-3:-1], path_parts[-1])
                if not os.path.exists(expected_path): missing.append(url)
            except Exception: missing.append(url)
        self.finished.emit(missing)

# --- Main Widget ---
class ImageProcessorWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.threads = []
        self.ensure_dirs_exist()
        self.state = {}
        self.load_state()

        main_layout = QHBoxLayout(self)
        sidebar_layout = QVBoxLayout(); sidebar_layout.setFixedWidth(200)
        sidebar_layout.addWidget(QLabel("<b>文件状态</b>"))
        self.unprocessed_label = QLabel("🔵 待处理: 0")
        self.processed_label = QLabel("🟢 已处理: 0")
        sidebar_layout.addWidget(self.unprocessed_label); sidebar_layout.addWidget(self.processed_label)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(QLabel("<b>重置操作</b>"))
        reset_button = QPushButton("🗑️ 全部重置"); reset_button.clicked.connect(self.reset_all)
        sidebar_layout.addWidget(reset_button)

        content_layout = QVBoxLayout()
        title = QLabel("🖼️ 图片批量处理器"); title.setObjectName("title")
        content_layout.addWidget(title); content_layout.addWidget(QLabel("本工具将引导您完成从下载到处理的全过程。"))
        self.stacked_widget = QStackedWidget(); content_layout.addWidget(self.stacked_widget)
        main_layout.addLayout(sidebar_layout); main_layout.addLayout(content_layout)

        self.create_all_steps()
        self.update_folder_status()
        self.stacked_widget.setCurrentIndex(self.state.get('current_step', 0))

    def create_all_steps(self):
        self.stacked_widget.addWidget(self.create_step1_ui())
        self.stacked_widget.addWidget(self.create_step2_ui())
        self.stacked_widget.addWidget(self.create_step3_ui())
        self.stacked_widget.addWidget(self.create_step4_ui())

    def create_step_ui(self, title, main_widget, prev_func=None, next_func=None):
        widget = QWidget(); layout = QVBoxLayout(widget); layout.setAlignment(Qt.AlignTop)
        layout.addWidget(QLabel(f"<h3>{title}</h3>")); layout.addWidget(main_widget); layout.addStretch()
        nav_layout = QHBoxLayout()
        if prev_func:
            prev_button = QPushButton("⬅️ 上一步"); prev_button.clicked.connect(prev_func)
            nav_layout.addWidget(prev_button)
        nav_layout.addStretch()
        if next_func:
            next_button = QPushButton("➡️ 下一步"); next_button.clicked.connect(next_func)
            nav_layout.addWidget(next_button)
        layout.addLayout(nav_layout)
        return widget

    def create_step1_ui(self):
        widget = QWidget(); layout = QVBoxLayout(widget)
        self.upload_button = QPushButton("📂 选择 qc.txt 文件"); self.upload_button.clicked.connect(self.select_qc_file)
        self.file_label = QLabel(); self.update_file_label()
        self.download_button = QPushButton("🚀 开始下载"); self.download_button.clicked.connect(self.start_download)
        self.download_progress = QProgressBar(); self.download_status = QTextEdit(); self.download_status.setReadOnly(True)
        h_layout = QHBoxLayout(); h_layout.addWidget(self.upload_button); h_layout.addWidget(self.file_label, 1)
        layout.addLayout(h_layout); layout.addWidget(self.download_button); layout.addWidget(self.download_progress); layout.addWidget(self.download_status)
        return self.create_step_ui("步骤 1: 下载图片", widget, next_func=lambda: self.change_step(1))

    def create_step2_ui(self):
        widget = QWidget(); layout = QVBoxLayout(widget)
        self.filter_button = QPushButton("🤖 开始自动筛选"); self.filter_button.clicked.connect(self.start_filtering)
        self.filter_progress = QProgressBar(); self.filter_status = QTextEdit(); self.filter_status.setReadOnly(True)
        layout.addWidget(QLabel("此步骤将自动筛选出没有Logo的图片。")); layout.addWidget(self.filter_button); layout.addWidget(self.filter_progress); layout.addWidget(self.filter_status)
        return self.create_step_ui("步骤 2: 自动筛选", widget, prev_func=lambda: self.change_step(0), next_func=lambda: self.change_step(2))

    def create_step3_ui(self):
        widget = QWidget(); layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("<b>模板管理</b>"))
        self.template_list = QListWidget(); self.refresh_template_list()
        upload_template_btn = QPushButton("上传模板"); upload_template_btn.clicked.connect(self.upload_templates)
        delete_template_btn = QPushButton("删除选中"); delete_template_btn.clicked.connect(self.delete_template)
        h_layout1 = QHBoxLayout(); h_layout1.addWidget(upload_template_btn); h_layout1.addWidget(delete_template_btn)
        layout.addWidget(self.template_list); layout.addLayout(h_layout1)

        layout.addWidget(QLabel("<b>参数调整</b>"))
        self.threshold_slider = QSlider(Qt.Horizontal); self.threshold_slider.setRange(50, 95); self.threshold_slider.setValue(int(self.state.get('match_threshold', 80.0)))
        self.threshold_label = QLabel(f"匹配阈值: {self.threshold_slider.value() / 100.0:.2f}"); self.threshold_slider.valueChanged.connect(lambda v: self.threshold_label.setText(f"匹配阈值: {v/100.0:.2f}"))
        self.threshold_slider.valueChanged.connect(lambda v: self.state.update({'match_threshold': v/100.0}))
        layout.addWidget(self.threshold_label); layout.addWidget(self.threshold_slider)

        self.process_button = QPushButton("🔥 开始处理"); self.process_button.clicked.connect(self.start_processing)
        self.process_progress = QProgressBar(); self.process_status = QTextEdit(); self.process_status.setReadOnly(True)
        layout.addWidget(self.process_button); layout.addWidget(self.process_progress); layout.addWidget(self.process_status)
        return self.create_step_ui("步骤 3: 模板匹配", widget, prev_func=lambda: self.change_step(1), next_func=lambda: self.change_step(3))

    def create_step4_ui(self):
        widget = QWidget(); layout = QVBoxLayout(widget)
        self.validate_button = QPushButton("🔍 开始最终校验"); self.validate_button.clicked.connect(self.start_validation)
        self.validation_results = QTextEdit(); self.validation_results.setReadOnly(True)
        layout.addWidget(QLabel("此步骤将检查 `qc.txt` 中的链接是否都有对应的已处理图片。"))
        layout.addWidget(self.validate_button); layout.addWidget(self.validation_results)
        return self.create_step_ui("步骤 4: 最终校验", widget, prev_func=lambda: self.change_step(2))

    def start_thread(self, worker_class, on_progress, on_finished, *args):
        thread = QThread(); worker = worker_class(*args); worker.moveToThread(thread)
        if on_progress: worker.progress.connect(on_progress)
        worker.finished.connect(on_finished); worker.finished.connect(thread.quit); worker.finished.connect(worker.deleteLater)
        thread.started.connect(worker.run); thread.finished.connect(thread.deleteLater)
        thread.start(); self.threads.append(thread)

    def format_report(self, title, summary_dict):
        html = f"<b>{title}</b><br><br>"
        for status, count in summary_dict.items():
            html += f"• {status}: {count}<br>"
        return html

    def start_download(self):
        if not os.path.exists(Config.URL_FILE_PATH): QMessageBox.warning(self, "文件未找到", "请先选择一个 qc.txt 文件。"); return
        self.download_button.setEnabled(False); self.download_progress.setValue(0); self.download_status.clear()
        self.start_thread(DownloadWorker, self.update_download_progress, self.on_download_finished)
    def update_download_progress(self, current, total, stats): self.download_progress.setValue(int((current/total)*100)); self.download_status.setHtml(self.format_report(f"下载进度: {current}/{total}", stats))
    def on_download_finished(self, summary): self.download_button.setEnabled(True); self.download_status.setHtml(self.format_report("下载完成!", summary)); self.update_folder_status(); QMessageBox.information(self, "完成", "图片下载完成。")

    def start_filtering(self):
        self.filter_button.setEnabled(False); self.filter_progress.setValue(0); self.filter_status.clear()
        self.start_thread(FilterWorker, self.update_filter_progress, self.on_filter_finished)
    def update_filter_progress(self, c, t, s): self.filter_progress.setValue(int((c/t)*100) if t > 0 else 0); self.filter_status.setHtml(self.format_report(f"筛选进度: {c}/{t}", s))
    def on_filter_finished(self, summary): self.filter_button.setEnabled(True); self.filter_status.setHtml(self.format_report("筛选完成!", summary) if summary else "文件夹为空，无需筛选。"); self.update_folder_status(); QMessageBox.information(self, "完成", "自动筛选完成。")

    def start_processing(self):
        self.process_button.setEnabled(False); self.process_progress.setValue(0); self.process_status.clear()
        self.start_thread(TemplateWorker, self.update_process_progress, self.on_process_finished, self.state.get('match_threshold', 0.8))
    def update_process_progress(self, c, t, s): self.process_progress.setValue(int((c/t)*100) if t > 0 else 0); self.process_status.setHtml(self.format_report(f"处理进度: {c}/{t}", s))
    def on_process_finished(self, summary): self.process_button.setEnabled(True); self.process_status.setHtml(self.format_report("处理完成!", summary) if summary else "文件夹为空，无需处理。"); self.update_folder_status(); QMessageBox.information(self, "完成", "模板处理完成。")

    def start_validation(self):
        self.validate_button.setEnabled(False); self.validation_results.setText("正在校验...");
        self.start_thread(ValidationWorker, None, self.on_validation_finished)
    def on_validation_finished(self, missing_files):
        self.validate_button.setEnabled(True)
        if not missing_files:
            self.validation_results.setText("✅ 所有文件均已处理。")
        else:
            self.validation_results.setText(f"🟡 发现 {len(missing_files)} 个缺失文件:\n\n" + "\n".join(missing_files))
        QMessageBox.information(self, "完成", "校验完成。")

    def change_step(self, index): self.stacked_widget.setCurrentIndex(index); self.state['current_step'] = index; self.save_state()
    def select_qc_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 qc.txt", Config.INPUT_DIR, "Text Files (*.txt)");
        if path: shutil.copy(path, Config.URL_FILE_PATH); self.update_file_label(); QMessageBox.information(self, "成功", f"'{os.path.basename(path)}' 已设置。")
    def update_file_label(self): self.file_label.setText(f"当前文件: {os.path.basename(Config.URL_FILE_PATH) if os.path.exists(Config.URL_FILE_PATH) else '未选择'}")
    def update_folder_status(self):
        unprocessed = sum(len(f) for _,_,f in os.walk(Config.UNPROCESSED_FOLDER)) if os.path.exists(Config.UNPROCESSED_FOLDER) else 0
        processed = sum(len(f) for _,_,f in os.walk(Config.PROCESSED_FOLDER)) if os.path.exists(Config.PROCESSED_FOLDER) else 0
        self.unprocessed_label.setText(f"🔵 待处理: {unprocessed}"); self.processed_label.setText(f"🟢 已处理: {processed}")
    def refresh_template_list(self):
        self.template_list.clear()
        if not os.path.exists(Config.TEMPLATE_DIR): return
        self.template_list.addItems([f for f in os.listdir(Config.TEMPLATE_DIR) if f.lower().endswith(('.png', '.jpg'))])
    def upload_templates(self):
        files, _ = QFileDialog.getOpenFileNames(self, "上传模板", "", "Images (*.png *.jpg)");
        for f in files: shutil.copy(f, os.path.join(Config.TEMPLATE_DIR, os.path.basename(f)))
        self.refresh_template_list()
    def delete_template(self):
        selected = self.template_list.currentItem()
        if not selected: return
        if QMessageBox.question(self, "确认删除", f"确定要删除模板 '{selected.text()}' 吗?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            os.remove(os.path.join(Config.TEMPLATE_DIR, selected.text())); self.refresh_template_list()
    def reset_all(self):
        if QMessageBox.question(self, "确认重置", "确定要重置所有进度和文件吗？这将删除output文件夹和状态文件。", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            if os.path.exists(Config.STATE_FILE_PATH): os.remove(Config.STATE_FILE_PATH)
            for folder in [Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
                if os.path.exists(folder): shutil.rmtree(folder, ignore_errors=True)
            self.ensure_dirs_exist(); self.load_state(); self.change_step(0); self.update_folder_status()
            for w in [self.download_status, self.filter_status, self.process_status, self.validation_results]: w.clear()
            QMessageBox.information(self, "成功", "所有进度和文件已重置。")

    def ensure_dirs_exist(self):
        for d in [Config.INPUT_DIR, Config.OUTPUT_DIR, Config.TEMPLATE_DIR, Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
            os.makedirs(d, exist_ok=True)
    def load_state(self):
        if os.path.exists(Config.STATE_FILE_PATH):
            try: self.state = json.load(open(Config.STATE_FILE_PATH))
            except: self.state = {}
        defaults = {'current_step': 0, 'match_threshold': 80.0};
        for k,v in defaults.items(): self.state.setdefault(k,v)
    def save_state(self):
        with open(Config.STATE_FILE_PATH, 'w') as f: json.dump(self.state, f, indent=4)
    def closeEvent(self, event):
        self.save_state()
        for thread in self.threads:
            thread.quit()
            thread.wait()
        super().closeEvent(event)
