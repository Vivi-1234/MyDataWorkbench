import sys
import os
import json
import pandas as pd
import shutil
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtCore import QObject, Slot, QUrl, QFileInfo
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from tools.image_processor.backend import ImageProcessorBackend
from tools.translator.backend import TranslatorBackend

# --- Backend Class ---
# This class will contain all Python logic callable from JavaScript
class Backend(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        # Create instances of modular backends
        self.image_processor = ImageProcessorBackend(main_window)
        self.translator = TranslatorBackend(main_window)

    @Slot(str, result=str)
    def get_tool_html(self, tool_name):
        """Loads the HTML content for a given tool."""
        # Correct path construction
        tool_html_path = os.path.join(os.path.dirname(__file__), "frontend", "tools", f"{tool_name}.html")
        if os.path.exists(tool_html_path):
            with open(tool_html_path, 'r', encoding='utf-8') as f:
                return f.read()
        return f"<h2 class='text-red-500'>错误: 未找到工具界面文件 {tool_name}.html</h2>"

    # --- Affiliate Data Tool Methods ---
    def __init__(self):
        super().__init__()
        self.df_users_full, self.df_orders_full, self.df_packages_full = None, None, None

    def _load_affiliate_data(self):
        if self.df_users_full is not None: return True
        try:
            DATA_PATH = os.path.join(os.path.dirname(__file__), 'tools', 'Affiliate_data', 'data')
            users_path = os.path.join(DATA_PATH, 'wp_users_affilate_tmp.csv')
            orders_path = os.path.join(DATA_PATH, 'wp_erp_order_tmp.csv')
            packages_path = os.path.join(DATA_PATH, 'wp_erp_packeage_tmp.csv')

            self.df_users_full = pd.read_csv(users_path, encoding='gb18030')
            self.df_orders_full = pd.read_csv(orders_path, encoding='gb18030')
            self.df_packages_full = pd.read_csv(packages_path, encoding='gb18030')

            for df in [self.df_users_full, self.df_orders_full, self.df_packages_full]:
                for col in df.columns:
                    if 'time' in col: df[col] = pd.to_datetime(df[col], errors='coerce')
            return True
        except Exception as e:
            print(f"Error loading affiliate data: {e}")
            return False

    @Slot(int, str, str, result=str)
    def generate_affiliate_report(self, affiliate_id, start_date_str, end_date_str):
        if not self._load_affiliate_data():
            return json.dumps({"error": "无法加载数据文件，请检查服务器日志。"})

        try:
            start_date = pd.to_datetime(f"{start_date_str} 00:00:00")
            end_date = pd.to_datetime(f"{end_date_str} 23:59:59")

            df_users = self.df_users_full[self.df_users_full['affilate'] == affiliate_id]
            df_orders = self.df_orders_full[self.df_orders_full['affilate'] == affiliate_id]
            df_packages = self.df_packages_full[self.df_packages_full['affilate'] == affiliate_id]

            if df_users.empty and df_orders.empty and df_packages.empty:
                return json.dumps({"error": f"找不到网红ID {affiliate_id} 的任何记录。"})

            users_reg = df_users[(df_users['reg_time'] >= start_date) & (df_users['reg_time'] <= end_date)]
            users_verified = df_users[(df_users['verified_time'] >= start_date) & (df_users['verified_time'] <= end_date)]
            users_active = df_users[(df_users['activate_time'] >= start_date) & (df_users['activate_time'] <= end_date)]
            orders = df_orders[(df_orders['create_time'] >= start_date) & (df_orders['create_time'] <= end_date)]
            packages = df_packages[(df_packages['create_time'] >= start_date) & (df_packages['create_time'] <= end_date)]

            metrics = {
                "注册用户数": len(users_reg), "激活用户数": len(users_verified), "活跃人数": len(users_active),
                "下单人数": int(orders['uid'].nunique()), "下单数量": len(orders), "下单总金额": float(orders['total_cny'].sum()),
                "提包人数": int(packages['uid'].nunique()), "提包数量": len(packages), "提包总金额": float(packages['total_cny'].sum()),
            }
            metrics["收单总金额"] = metrics["下单总金额"] + metrics["提包总金额"]

            return json.dumps(metrics)

        except Exception as e:
            print(f"Error generating report: {e}")
            return json.dumps({"error": f"生成报告时出错: {e}"})

    # --- Mulebuy Pics Tool Methods ---
    @Slot(result=str)
    def get_mulebuy_image_data(self):
        try:
            DATA_PATH = os.path.join(os.path.dirname(__file__), 'tools', 'MulebuyPics', 'data')
            os.makedirs(DATA_PATH, exist_ok=True)

            categories = sorted([d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))])

            uncategorized_path = QUrl.fromLocalFile(DATA_PATH).toString()
            uncategorized_images = sorted([
                uncategorized_path + '/' + f for f in os.listdir(DATA_PATH)
                if os.path.isfile(os.path.join(DATA_PATH, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg'))
            ])

            result = {
                "categories": categories,
                "uncategorized": { "path": uncategorized_path, "images": uncategorized_images },
                "categorized": []
            }

            for category in categories:
                category_path_str = os.path.join(DATA_PATH, category)
                category_url = QUrl.fromLocalFile(category_path_str).toString()
                images = sorted([
                    category_url + '/' + f for f in os.listdir(category_path_str)
                    if os.path.isfile(os.path.join(category_path_str, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg'))
                ])
                result["categorized"].append({ "name": category, "path": category_url, "images": images })

            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": f"Error getting image data: {e}"})

    @Slot(str, result=str)
    def create_mulebuy_category(self, name):
        try:
            if not name or not name.strip(): return json.dumps({"success": False, "error": "分类名称不能为空。"})
            path = os.path.join(os.path.dirname(__file__), 'tools', 'MulebuyPics', 'data', name)
            os.makedirs(path, exist_ok=True)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @Slot(str, result=str)
    def delete_mulebuy_images(self, paths_str):
        try:
            paths_to_delete = json.loads(paths_str)
            for url_str in paths_to_delete:
                path = QUrl(url_str).toLocalFile()
                if os.path.exists(path):
                    os.remove(path)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @Slot(list, str, result=str)
    def move_mulebuy_images(self, paths_str, destination_category):
        try:
            paths_to_move = json.loads(paths_str)
            DATA_PATH = os.path.join(os.path.dirname(__file__), 'tools', 'MulebuyPics', 'data')
            destination_path = DATA_PATH if destination_category == "未分类" else os.path.join(DATA_PATH, destination_category)
            for url_str in paths_to_move:
                source_path = QUrl(url_str).toLocalFile()
                if os.path.exists(source_path):
                    shutil.move(source_path, os.path.join(destination_path, os.path.basename(source_path)))
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @Slot(str, result=str)
    def delete_mulebuy_category(self, name):
        try:
            path = os.path.join(os.path.dirname(__file__), 'tools', 'MulebuyPics', 'data', name)
            if len(os.listdir(path)) > 0:
                return json.dumps({"success": False, "error": "无法删除：该分类不为空。"})
            shutil.rmtree(path)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @Slot(str, str, result=str)
    def rename_mulebuy_category(self, old_name, new_name):
        try:
            DATA_PATH = os.path.join(os.path.dirname(__file__), 'tools', 'MulebuyPics', 'data')
            os.rename(os.path.join(DATA_PATH, old_name), os.path.join(DATA_PATH, new_name))
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @Slot(result=str)
    def open_image_file_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(None, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        return json.dumps(file_paths)

    @Slot(list, str, result=str)
    def upload_mulebuy_images(self, source_paths, target_category):
        try:
            DATA_PATH = os.path.join(os.path.dirname(__file__), 'tools', 'MulebuyPics', 'data')
            save_path = DATA_PATH if target_category == "未分类" else os.path.join(DATA_PATH, target_category)
            for path in source_paths:
                shutil.copy(path, os.path.join(save_path, os.path.basename(path)))
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Allen工作台")
        self.setGeometry(100, 100, 1440, 900)

        # --- Web Engine View ---
        self.view = QWebEngineView()

        # --- Web Channel Setup ---
        self.channel = QWebChannel()
        self.backend = Backend(self) # Pass main_window instance
        self.channel.registerObject("pyBackend", self.backend)
        self.channel.registerObject("pyIpBackend", self.backend.image_processor)
        self.channel.registerObject("pyTranslatorBackend", self.backend.translator)
        self.view.page().setWebChannel(self.channel)

        # --- Load HTML ---
        # Use an absolute path to ensure it works regardless of where the script is run
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend", "index.html"))
        self.view.setUrl(QUrl.fromLocalFile(file_path))

        self.setCentralWidget(self.view)

if __name__ == "__main__":
    # This is important for WebEngine to work correctly
    os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
