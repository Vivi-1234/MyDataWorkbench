# 文件路径: MyDataWorkbench/tools/Affiliate_data/pyside_tool.py

import os
import sys
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QDateEdit, QGridLayout, QSpinBox, QMessageBox
)
from PySide6.QtCore import QDate

# --- Configuration & Backend Logic ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_PATH, "data")

def _load_data_from_disk(data_path):
    try:
        users_path = os.path.join(data_path, 'wp_users_affilate_tmp.csv')
        orders_path = os.path.join(data_path, 'wp_erp_order_tmp.csv')
        packages_path = os.path.join(data_path, 'wp_erp_packeage_tmp.csv')
        return pd.read_csv(users_path, encoding='gb18030'), pd.read_csv(orders_path, encoding='gb18030'), pd.read_csv(packages_path, encoding='gb18030')
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None

def _calculate_metrics(users_df, orders_df, packages_df, start_date, end_date):
    users_reg = users_df[(users_df['reg_time'] >= start_date) & (users_df['reg_time'] <= end_date)]
    users_verified = users_df[(users_df['verified_time'] >= start_date) & (users_df['verified_time'] <= end_date)]
    users_active = users_df[(users_df['activate_time'] >= start_date) & (users_df['activate_time'] <= end_date)]
    orders = orders_df[(orders_df['create_time'] >= start_date) & (orders_df['create_time'] <= end_date)]
    packages = packages_df[(packages_df['create_time'] >= start_date) & (packages_df['create_time'] <= end_date)]

    metrics = {
        "注册用户数": len(users_reg), "激活用户数": len(users_verified), "活跃人数": len(users_active),
        "下单人数": orders['uid'].nunique(), "下单数量": len(orders), "下单总金额 (CNY)": orders['total_cny'].sum(),
        "提包人数": packages['uid'].nunique(), "提包数量": len(packages), "提包总金额 (CNY)": packages['total_cny'].sum(),
    }
    metrics["收单总金额 (CNY)"] = metrics["下单总金额 (CNY)"] + metrics["提包总金额 (CNY)"]
    return metrics

# --- Main Widget ---
class AffiliateDataWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.df_users_full, self.df_orders_full, self.df_packages_full = None, None, None

        main_layout = QHBoxLayout(self)
        sidebar = self.create_sidebar()

        # --- Report Area ---
        report_area = QWidget()
        self.report_layout = QVBoxLayout(report_area)
        self.report_layout.addWidget(QLabel("请在左侧面板设置参数后点击按钮生成报告。"))

        main_layout.addWidget(sidebar)
        main_layout.addWidget(report_area, 1)

    def create_sidebar(self):
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_widget.setFixedWidth(250)

        sidebar_layout.addWidget(QLabel("<b>参数设置</b>"))
        self.id_input = QSpinBox()
        self.id_input.setRange(1, 999999999) # Increased limit
        self.start_date_input = QDateEdit(QDate.currentDate())
        self.end_date_input = QDateEdit(QDate.currentDate())
        self.start_date_input.setCalendarPopup(True)
        self.end_date_input.setCalendarPopup(True)

        generate_button = QPushButton("🚀 生成分析报告")
        generate_button.clicked.connect(self.generate_report)

        sidebar_layout.addWidget(QLabel("输入网红ID:"))
        sidebar_layout.addWidget(self.id_input)
        sidebar_layout.addWidget(QLabel("选择开始日期:"))
        sidebar_layout.addWidget(self.start_date_input)
        sidebar_layout.addWidget(QLabel("选择结束日期:"))
        sidebar_layout.addWidget(self.end_date_input)
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(generate_button)
        sidebar_layout.addStretch()
        return sidebar_widget

    def load_data(self):
        """Loads data from disk if not already loaded. Returns True on success."""
        if self.df_users_full is not None:
            return True # Already loaded

        self.df_users_full, self.df_orders_full, self.df_packages_full = _load_data_from_disk(DATA_PATH)

        if self.df_users_full is None:
            QMessageBox.critical(self, "错误", f"未在 '{DATA_PATH}' 中找到必需的CSV文件。")
            return False

        # Pre-convert date columns for performance
        for df in [self.df_users_full, self.df_orders_full, self.df_packages_full]:
            for col in df.columns:
                if 'time' in col:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
        return True

    def generate_report(self):
        # Load data on demand
        if not self.load_data():
            return # Stop if data loading failed

        affiliate_id = self.id_input.value()
        start_date = self.start_date_input.dateTime().toPython()
        end_date = self.end_date_input.dateTime().toPython().replace(hour=23, minute=59, second=59)

        df_users = self.df_users_full[self.df_users_full['affilate'] == affiliate_id]
        df_orders = self.df_orders_full[self.df_orders_full['affilate'] == affiliate_id]
        df_packages = self.df_packages_full[self.df_packages_full['affilate'] == affiliate_id]

        if df_users.empty and df_orders.empty and df_packages.empty:
            QMessageBox.warning(self, "无数据", f"找不到网红ID {affiliate_id} 的任何记录。"); return

        final_metrics = _calculate_metrics(df_users, df_orders, df_packages, start_date, end_date)
        self.display_report(final_metrics, affiliate_id, start_date, end_date)

    def display_report(self, metrics, affiliate_id, start_date, end_date):
        # Clear previous report
        while self.report_layout.count():
            child = self.report_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        title = f"网红 {affiliate_id} 数据报告 ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
        self.report_layout.addWidget(QLabel(f"<h3>{title}</h3>"))

        grid = QGridLayout()
        display_order = ['注册用户数', '激活用户数', '活跃人数', '下单人数', '下单数量', '下单总金额 (CNY)', '提包人数', '提包数量', '提包总金额 (CNY)', '收单总金额 (CNY)']

        row, col = 0, 0
        for key in display_order:
            val = metrics.get(key, 0)
            formatted_val = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
            key_label = QLabel(f"<b>{key.replace(' (CNY)', '')}:</b>")
            val_label = QLabel(formatted_val)
            grid.addWidget(key_label, row, col * 2)
            grid.addWidget(val_label, row, col * 2 + 1)
            col += 1
            if col > 1:
                col = 0
                row += 1

        self.report_layout.addLayout(grid)
        self.report_layout.addStretch()
