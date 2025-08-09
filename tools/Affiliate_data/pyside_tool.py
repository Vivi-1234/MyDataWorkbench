import os, pandas as pd
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QDateEdit, QGridLayout, QSpinBox, QMessageBox
)
from PySide6.QtCore import QDate, QObject, QThread, Signal

class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, affiliate_id, start_date, end_date):
        super().__init__()
        self.affiliate_id = affiliate_id
        self.start_date = start_date
        self.end_date = end_date
        self.DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')

    def run(self):
        try:
            users_df = pd.read_csv(os.path.join(self.DATA_PATH, 'wp_users_affilate_tmp.csv'), encoding='gb18030')
            orders_df = pd.read_csv(os.path.join(self.DATA_PATH, 'wp_erp_order_tmp.csv'), encoding='gb18030')
            packages_df = pd.read_csv(os.path.join(self.DATA_PATH, 'wp_erp_packeage_tmp.csv'), encoding='gb18030')

            for df in [users_df, orders_df, packages_df]:
                for col in df.columns:
                    if 'time' in col: df[col] = pd.to_datetime(df[col], errors='coerce')

            df_users = users_df[users_df['affilate'] == self.affiliate_id]
            df_orders = orders_df[orders_df['affilate'] == self.affiliate_id]
            df_packages = packages_df[packages_df['affilate'] == self.affiliate_id]

            if df_users.empty and df_orders.empty and df_packages.empty:
                self.error.emit(f"找不到网红ID {self.affiliate_id} 的任何记录。")
                return

            users_reg = df_users[(df_users['reg_time'] >= self.start_date) & (df_users['reg_time'] <= self.end_date)]
            # ... all other calculations ...
            metrics = {"注册用户数": len(users_reg)}
            self.finished.emit(metrics)

        except FileNotFoundError: self.error.emit("错误：找不到数据文件。")
        except Exception as e: self.error.emit(f"处理数据时出错: {e}")

class AffiliateDataWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window

        main_layout = QHBoxLayout(self)
        sidebar = self.create_sidebar()

        self.report_container = QWidget()
        self.report_layout = QVBoxLayout(self.report_container)
        self.report_layout.addWidget(QLabel("请在左侧面板设置参数后点击按钮生成报告。"))

        main_layout.addWidget(sidebar); main_layout.addWidget(self.report_container, 1)

    def create_sidebar(self):
        # ... (UI setup) ...
        self.generate_button = QPushButton("🚀 生成分析报告")
        self.generate_button.clicked.connect(self.run_report_generation)
        # ...
        return QWidget() # Placeholder

    def run_report_generation(self):
        self.generate_button.setDisabled(True); self.generate_button.setText("正在生成...")
        # ... get values ...
        self.thread = QThread()
        self.worker = Worker(affiliate_id, start_date, end_date)
        # ... thread setup ...
        self.worker.finished.connect(self.on_report_finished)
        self.worker.error.connect(self.on_report_error)
        self.thread.start()

    def on_report_finished(self, metrics):
        # ... clear layout and display metrics ...
        self.generate_button.setDisabled(False); self.generate_button.setText("🚀 生成分析报告")
    def on_report_error(self, msg):
        QMessageBox.critical(self, "错误", msg)
        self.generate_button.setDisabled(False); self.generate_button.setText("🚀 生成分析报告")
