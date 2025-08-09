import sys, os, importlib
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QListWidgetItem, QComboBox, QPushButton
)
from PySide6.QtCore import Qt

STYLESHEET = """
QWidget {
    background-color: #18181b; color: #d4d4d8;
    font-family: 'Segoe UI', sans-serif;
}
QMainWindow { background-color: #09090b; }
QLabel { color: #d4d4d8; }
QLabel#title { font-size: 18px; font-weight: bold; color: #f43f5e; }
QListWidget { background-color: #27272a; border: none; }
QListWidget::item { padding: 12px 18px; border-radius: 5px; margin: 2px 5px; }
QListWidget::item:hover { background-color: #3f3f46; }
QListWidget::item:selected { background-color: #f43f5e; color: #ffffff; }
QPushButton {
    background-color: #e11d48; color: #ffffff; border: none;
    padding: 8px 16px; font-size: 13px; border-radius: 5px;
}
QPushButton:hover { background-color: #be123c; }
QPushButton:disabled { background-color: #52525b; color: #a1a1aa; }
QComboBox {
    background-color: #3f3f46; border-radius: 3px; padding: 5px;
    border: 1px solid #52525b;
}
QLineEdit, QTextEdit, QSpinBox {
    background-color: #3f3f46; border: 1px solid #52525b;
    padding: 5px; border-radius: 3px;
}
QProgressBar { border: 1px solid #52525b; border-radius: 5px; text-align: center; color: #d4d4d8; }
QProgressBar::chunk { background-color: #e11d48; border-radius: 4px; margin: 1px; }
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Allen工作台")
        self.setGeometry(100, 100, 1366, 768)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0); main_layout.setSpacing(0)

        sidebar_widget = QWidget(); sidebar_widget.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(10,10,10,10); sidebar_layout.setSpacing(10)

        title_label = QLabel("Allen工作台"); title_label.setObjectName("title")
        sidebar_layout.addWidget(title_label)

        sidebar_layout.addWidget(QLabel("🧠 AI模型选择:"))
        self.model_selector = QComboBox()
        self.model_selector.addItems(["mulebuy-optimizer", "llama3.1:latest", "qwen3:8b"])
        sidebar_layout.addWidget(self.model_selector)
        sidebar_layout.addSpacing(10)

        self.tool_list = QListWidget(); self.tool_list.itemClicked.connect(self.switch_tool)
        sidebar_layout.addWidget(self.tool_list)

        self.stack = QStackedWidget()
        main_layout.addWidget(sidebar_widget); main_layout.addWidget(self.stack)
        self.setCentralWidget(main_widget)

        self.tool_widgets = {}
        self.load_tools()

    def load_tools(self):
        tools_dir = "tools"
        tool_map = {
            "Affiliate_data": "联盟数据", "MulebuyPics": "Mulebuy图片",
            "image_processor": "图片批量处理器", "Translator": "文案优化"
        }

        available_tools = [d for d in os.listdir(tools_dir) if d in tool_map and os.path.isdir(os.path.join(tools_dir, d))]

        for tool_name in available_tools:
            display_name = tool_map.get(tool_name)
            item = QListWidgetItem(display_name); item.setData(Qt.UserRole, tool_name)
            self.tool_list.addItem(item)

            try:
                module = importlib.import_module(f"tools.{tool_name}.pyside_tool")
                widget_class = next(getattr(module, name) for name in dir(module) if isinstance(getattr(module, name), type) and issubclass(getattr(module, name), QWidget) and getattr(module, name) is not QWidget)
                widget = widget_class(self)
            except Exception as e:
                print(f"Error loading {tool_name}: {e}")
                widget = QLabel(f"加载工具 {tool_name} 失败:\n{e}")
                widget.setAlignment(Qt.AlignCenter)

            self.stack.addWidget(widget)

        if self.tool_list.count() > 0: self.tool_list.setCurrentRow(0)

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
