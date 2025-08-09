import sys, os, importlib
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QListWidgetItem, QComboBox, QPushButton
)
from PySide6.QtCore import QSize, Qt

# --- Hardcoded QSS for stability and theme ---
STYLESHEET = """
QWidget {
    background-color: #1f2937; color: #e5e7eb;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QMainWindow { background-color: #111827; }
QListWidget { background-color: #374151; border: none; font-size: 14px; padding: 5px; }
QListWidget::item { padding: 10px 15px; border-radius: 5px; margin-bottom: 2px; }
QListWidget::item:hover { background-color: #4b5563; }
QListWidget::item:selected { background-color: #db2777; color: #ffffff; font-weight: bold; }
QPushButton {
    background-color: #be185d; color: #ffffff; border: none;
    padding: 8px 16px; font-size: 13px; border-radius: 5px;
}
QPushButton:hover { background-color: #9d174d; }
QComboBox {
    background-color: #4b5563; border-radius: 3px; padding: 5px;
}
/* Add other widget styles here */
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Allen工作台")
        self.setGeometry(100, 100, 1280, 800)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)

        sidebar_widget = QWidget(); sidebar_widget.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(10,10,10,10)

        sidebar_layout.addWidget(QLabel("<h3>Allen工作台</h3>"))
        sidebar_layout.addWidget(QLabel("🧠 AI模型选择:"))
        self.model_selector = QComboBox()
        self.model_selector.addItems(["mulebuy-optimizer", "llama3.1:latest", "qwen3:8b"])
        sidebar_layout.addWidget(self.model_selector)
        sidebar_layout.addSpacing(20)

        self.tool_list = QListWidget(); self.tool_list.itemClicked.connect(self.switch_tool)
        sidebar_layout.addWidget(self.tool_list)

        self.stack = QStackedWidget()
        main_layout.addWidget(sidebar_widget); main_layout.addWidget(self.stack)
        self.setCentralWidget(main_widget)

        self.tool_widgets = {}
        self.load_tools()

    def load_tools(self):
        tools_dir = "tools"
        tool_display_names = {
            "Affiliate_data": "联盟数据", "MulebuyPics": "Mulebuy图片",
            "image_processor": "图片批量处理器", "Translator": "文案优化"
        }
        available_tools = [d for d in os.listdir(tools_dir) if os.path.isdir(os.path.join(tools_dir, d)) and not d.startswith('__')]

        for tool_name in available_tools:
            display_name = tool_display_names.get(tool_name, tool_name)
            self.tool_list.addItem(QListWidgetItem(display_name))

            # Placeholder, will be replaced by actual widget
            placeholder = QLabel(f"{display_name}\n(待实现)")
            placeholder.setAlignment(Qt.AlignCenter)
            self.stack.addWidget(placeholder)

    def switch_tool(self, item):
        self.stack.setCurrentIndex(self.tool_list.row(item))

    def get_selected_model(self):
        return self.model_selector.currentText()

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
