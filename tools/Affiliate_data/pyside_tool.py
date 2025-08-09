import os, pandas as pd
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QDateEdit, QGridLayout, QLineEdit, QMessageBox
)
from PySide6.QtCore import QDate, QObject, QThread, Signal, Qt
from PySide6.QtGui import QIntValidator

class Worker(QObject):
    finished = Signal(object); error = Signal(str)
    def __init__(self, affiliate_id, start_date, end_date):
        super().__init__(); self.affiliate_id = affiliate_id; self.start_date = start_date; self.end_date = end_date
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
                self.error.emit(f"找不到网红ID {self.affiliate_id} 的任何记录。"); return

            metrics = {
                "注册用户数": len(df_users[(df_users['reg_time'] >= self.start_date) & (df_users['reg_time'] <= self.end_date)]),
                "激活用户数": len(df_users[(df_users['verified_time'] >= self.start_date) & (df_users['verified_time'] <= self.end_date)]),
                "活跃人数": len(df_users[(df_users['activate_time'] >= self.start_date) & (df_users['activate_time'] <= self.end_date)]),
                "下单人数": df_orders['uid'].nunique(), "下单数量": len(df_orders), "下单总金额": df_orders['total_cny'].sum(),
                "提包人数": df_packages['uid'].nunique(), "提包数量": len(df_packages), "提包总金额": df_packages['total_cny'].sum()
            }
            metrics["收单总金额"] = metrics["下单总金额"] + metrics["提包总金额"]
            self.finished.emit(metrics)
        except FileNotFoundError: self.error.emit("错误：一个或多个数据文件不存在。")
        except Exception as e: self.error.emit(f"处理数据时出错: {e}")

class AffiliateDataWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__(); self.main_window = main_window
        layout = QVBoxLayout(self); layout.setContentsMargins(20,20,20,20); layout.setSpacing(15)

        input_widget = QWidget(); input_layout = QHBoxLayout(input_widget); input_layout.setSpacing(10)
        self.id_input = QLineEdit(); self.id_input.setValidator(QIntValidator(1, 999999999)); self.id_input.setPlaceholderText("输入网红ID")
        self.start_date_input = QDateEdit(QDate.currentDate()); self.start_date_input.setCalendarPopup(True)
        self.end_date_input = QDateEdit(QDate.currentDate()); self.end_date_input.setCalendarPopup(True)
        self.generate_button = QPushButton("🚀 生成分析报告")
        self.generate_button.clicked.connect(self.run_report_generation)
        input_layout.addWidget(QLabel("网红ID:")); input_layout.addWidget(self.id_input)
        input_layout.addWidget(QLabel("开始日期:")); input_layout.addWidget(self.start_date_input)
        input_layout.addWidget(QLabel("结束日期:")); input_layout.addWidget(self.end_date_input)
        input_layout.addStretch(); input_layout.addWidget(self.generate_button)

        self.report_container = QWidget()
        self.report_layout = QVBoxLayout(self.report_container)
        self.report_layout.addWidget(QLabel("请填写网红ID和日期，然后点击生成报告。"))

        layout.addWidget(input_widget); layout.addWidget(self.report_container, 1)

    def run_report_generation(self):
        if not self.id_input.text(): QMessageBox.warning(self, "提示", "请输入网红ID。"); return
        self.generate_button.setDisabled(True); self.generate_button.setText("正在生成...")
        self.clear_layout(self.report_layout); self.report_layout.addWidget(QLabel("正在计算..."))

        self.thread = QThread()
        self.worker = Worker(int(self.id_input.text()), self.start_date_input.dateTime().toPython(), self.end_date_input.dateTime().toPython().replace(hour=23, minute=59, second=59))
        self.worker.moveToThread(self.thread)
        self.worker.finished.connect(self.on_report_finished); self.worker.error.connect(self.on_report_error)
        self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater); self.thread.started.connect(self.worker.run); self.thread.start()

    def on_report_finished(self, metrics):
        self.clear_layout(self.report_layout)
        grid = QGridLayout(); grid.setSpacing(15)
        display_order = ['注册用户数', '激活用户数', '活跃人数', '下单人数', '下单数量', '下单总金额', '提包人数', '提包数量', '提包总金额', '收单总金额']
        row, col = 0, 0
        for key in display_order:
            val = metrics.get(key, 0); formatted_val = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
            key_label = QLabel(f"<b>{key}:</b>"); val_label = QLabel(formatted_val); val_label.setStyleSheet("font-size: 16px; color: #f43f5e;")
            grid.addWidget(key_label, row, col*2); grid.addWidget(val_label, row, col*2+1)
            col +=1
            if col > 1: col=0; row+=1
        self.report_layout.addLayout(grid); self.report_layout.addStretch()
        self.generate_button.setDisabled(False); self.generate_button.setText("🚀 生成分析报告")

    def on_report_error(self, msg):
        self.clear_layout(self.report_layout); self.report_layout.addWidget(QLabel(msg))
        QMessageBox.critical(self, "错误", msg)
        self.generate_button.setDisabled(False); self.generate_button.setText("🚀 生成分析报告")

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            elif child.layout(): self.clear_layout(child.layout())
