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

from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QFileDialog

# --- Configuration ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
class Config:
    INPUT_DIR = os.path.join(BASE_PATH, 'input'); OUTPUT_DIR = os.path.join(BASE_PATH, 'output')
    TEMPLATE_DIR = os.path.join(BASE_PATH, 'templates'); URL_FILE_PATH = os.path.join(INPUT_DIR, 'qc.txt')
    STATE_FILE_PATH = os.path.join(INPUT_DIR, 'state.json'); PROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'processed_images')
    UNPROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'unprocessed_images'); NUM_WORKERS = 15
    LOWER_RED1, UPPER_RED1 = np.array([0, 80, 80]), np.array([10, 255, 255])
    LOWER_RED2, UPPER_RED2 = np.array([160, 80, 80]), np.array([179, 255, 255])
    LOWER_WHITE, UPPER_WHITE = np.array([0, 0, 180]), np.array([179, 40, 255])
    MIN_RED_TO_WHITE_RATIO = 0.01; MIN_TOTAL_AREA_RATIO = 0.0001; MIN_ASPECT_RATIO = 0.5; MAX_ASPECT_RATIO = 5.0

# --- Worker Functions ---
def download_image(url):
    try:
        path_parts = urlparse(url).path.strip('/').split('/'); dir_path = os.path.join(Config.UNPROCESSED_FOLDER, *path_parts[-3:-1])
        os.makedirs(dir_path, exist_ok=True); file_path = os.path.join(dir_path, path_parts[-1])
        if os.path.exists(file_path): return "skipped"
        response = requests.get(url, stream=True, timeout=20, verify=False)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(8192): f.write(chunk)
            return "success"
        return f"http_error_{response.status_code}"
    except Exception: return "error"
# ... (Other core functions like identify_and_move_task, etc. are assumed to be here) ...

# --- Worker QObjects ---
class BaseWorker(QObject):
    progress = Signal(int, int, str); status = Signal(str, str); finished = Signal(str, str)
    def __init__(self, step_id, *args, **kwargs): super().__init__(); self.step_id = step_id
    def run_with_executor(self, task_function, tasks, *args):
        counter = Counter()
        with ThreadPoolExecutor(max_workers=Config.NUM_WORKERS) as executor:
            futures = {executor.submit(task_function, task, *args) for task in tasks}
            for i, future in enumerate(as_completed(futures)):
                result = future.result(); counter[result] += 1
                self.progress.emit(i + 1, len(tasks), self.step_id)
                self.status.emit(f"处理中... {dict(counter)}", self.step_id)
        self.finished.emit(f"完成! 结果: {dict(counter)}", self.step_id)

class DownloadWorker(BaseWorker):
    def run(self):
        try:
            with open(Config.URL_FILE_PATH, 'r') as f: urls = list(dict.fromkeys([line.strip() for line in f if line.strip()]))
            if not urls: self.finished.emit("文件为空或不存在。", self.step_id); return
            for folder in [Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
                if os.path.exists(folder): shutil.rmtree(folder)
                os.makedirs(folder)
            self.run_with_executor(download_image, urls)
        except Exception as e: self.finished.emit(f"下载出错: {e}", self.step_id)

# ... (FilterWorker, TemplateWorker, ValidationWorker full implementations) ...

# --- Main Backend for this Tool ---
class ImageProcessorBackend(QObject):
    def __init__(self, main_window):
        super().__init__(); self.main_window = main_window; self.thread = None
    def run_js(self, code):
        if self.main_window: self.main_window.view.page().runJavaScript(code)
    def start_task(self, worker_class, *args):
        if self.thread and self.thread.isRunning(): self.run_js("alert('已有任务在运行中，请稍候。');"); return
        self.thread = QThread(); worker = worker_class(*args)
        worker.moveToThread(self.thread)
        worker.progress.connect(self.on_progress); worker.status.connect(self.on_status); worker.finished.connect(self.on_status)
        worker.finished.connect(self.thread.quit); worker.deleteLater(); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(worker.run); self.thread.start()

    @Slot(result=str)
    def open_qc_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self.main_window, "选择 qc.txt", "", "Text Files (*.txt)")
        if not path: return ""
        try:
            os.makedirs(Config.INPUT_DIR, exist_ok=True); shutil.copy(path, Config.URL_FILE_PATH)
            return os.path.basename(path)
        except Exception as e: self.run_js(f"alert('复制文件时出错: {e}');"); return ""

    @Slot()
    def start_download(self): self.start_task(DownloadWorker, 'download')
    # ... (Other start slots) ...

    @Slot(int, int, str)
    def on_progress(self, current, total, step_id): self.run_js(f"updateIpProgress('{step_id}', {int((current/total)*100) if total>0 else 0});")
    @Slot(str, str)
    def on_status(self, message, step_id): self.run_js(f"updateIpStatus('{step_id}', `{message}`);")
