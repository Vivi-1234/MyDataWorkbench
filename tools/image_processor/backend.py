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
    INPUT_DIR = os.path.join(BASE_PATH, 'input')
    OUTPUT_DIR = os.path.join(BASE_PATH, 'output')
    TEMPLATE_DIR = os.path.join(BASE_PATH, 'templates')
    URL_FILE_PATH = os.path.join(INPUT_DIR, 'qc.txt')
    PROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'processed_images')
    UNPROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'unprocessed_images')
    NUM_WORKERS = 15
    LOWER_RED1, UPPER_RED1 = np.array([0, 80, 80]), np.array([10, 255, 255])
    LOWER_RED2, UPPER_RED2 = np.array([160, 80, 80]), np.array([179, 255, 255])
    LOWER_WHITE, UPPER_WHITE = np.array([0, 0, 180]), np.array([179, 40, 255])
    MIN_RED_TO_WHITE_RATIO = 0.01; MIN_TOTAL_AREA_RATIO = 0.0001; MIN_ASPECT_RATIO = 0.5; MAX_ASPECT_RATIO = 5.0

# --- Worker Functions (run in executors) ---
def download_image(url):
    # ... (same as before)
    return "success" # Placeholder

def identify_and_move_task(source_path):
    # ... (same as before)
    return "no_logo_moved" # Placeholder

# --- Worker QObjects (run in QThreads) ---
class DownloadWorker(QObject):
    progress = Signal(int, int)
    status = Signal(str)
    finished = Signal(str)

    def run(self):
        try:
            with open(Config.URL_FILE_PATH, 'r') as f: urls = list(dict.fromkeys([line.strip() for line in f if line.strip()]))
            if not urls: self.finished.emit("文件为空。"); return

            for folder in [Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
                if os.path.exists(folder): shutil.rmtree(folder)
                os.makedirs(folder)

            # ... (ThreadPoolExecutor logic) ...

            self.finished.emit("下载完成!")
        except Exception as e:
            self.finished.emit(f"下载出错: {e}")

# ... Other workers would be here ...

# --- Main Backend for this Tool ---
class ImageProcessorBackend(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.thread = None

    @Slot(result=str)
    def open_qc_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self.main_window, "选择 qc.txt", "", "Text Files (*.txt)")
        if not path: return ""
        try:
            os.makedirs(Config.INPUT_DIR, exist_ok=True)
            shutil.copy(path, Config.URL_FILE_PATH)
            return os.path.basename(path)
        except Exception as e:
            self.run_js(f"alert('复制文件时出错: {e}');")
            return ""

    @Slot()
    def start_download(self):
        if self.thread and self.thread.isRunning(): return
        self.thread = QThread()
        worker = DownloadWorker()
        worker.moveToThread(self.thread)
        worker.progress.connect(self.on_progress)
        worker.status.connect(self.on_status)
        worker.finished.connect(self.on_status) # Final status
        worker.finished.connect(self.thread.quit)
        worker.finished.connect(worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(worker.run)
        self.thread.start()

    # Generic slots to forward updates to JS
    @Slot(int, int)
    def on_progress(self, current, total):
        percent = int((current / total) * 100) if total > 0 else 0
        self.run_js(f"updateIpProgress('download', {percent});")

    @Slot(str)
    def on_status(self, message):
        self.run_js(f"updateIpStatus('download', `{message}`);")

    def run_js(self, code):
        self.main_window.view.page().runJavaScript(code)
