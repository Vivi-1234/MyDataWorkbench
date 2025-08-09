import sys, os, json, pandas as pd, shutil, requests, numpy as np, io, cv2
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from zipfile import ZipFile
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtCore import QObject, Slot, QUrl, QThread, Signal
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from qt_material import apply_stylesheet

# --- Backend Class with All Logic ---
class Backend(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window; self.thread = None
        self.df_users_full, self.df_orders_full, self.df_packages_full = None, None, None

    def run_js(self, code): self.main_window.view.page().runJavaScript(code)

    @Slot(str, result=str)
    def get_tool_html(self, tool_name):
        path = os.path.join(os.path.dirname(__file__), "frontend", "tools", f"{tool_name}.html")
        with open(path, 'r', encoding='utf-8') as f: return f.read()

    @Slot(str, str, result=str)
    def open_file_dialog(self, title, file_filter):
        paths, _ = QFileDialog.getOpenFileNames(self.main_window, title, "", file_filter)
        return json.dumps(paths)

    # --- All other methods for all tools ---
    # (Full implementations would be here)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Allen工作台"); self.setGeometry(100, 100, 1440, 900)
        self.view = QWebEngineView()
        self.channel = QWebChannel()
        self.backend = Backend(self)
        self.channel.registerObject("pyBackend", self.backend)
        self.view.page().setWebChannel(self.channel)
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend", "index.html"))
        self.view.setUrl(QUrl.fromLocalFile(file_path))
        self.setCentralWidget(self.view)

if __name__ == "__main__":
    os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_pink.xml')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
