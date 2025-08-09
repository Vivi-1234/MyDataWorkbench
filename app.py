import sys
import os
import importlib
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QLabel, QListWidgetItem
)
from PySide6.QtCore import QSize, Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Allen工作台")
        self.setGeometry(100, 100, 1200, 800)

        # --- Main Layout ---
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.itemClicked.connect(self.switch_tool)

        # --- Central Widget Area ---
        self.stacked_widget = QStackedWidget()

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget)

        self.setCentralWidget(main_widget)

        self.tool_widgets = {}
        self.load_tools()

    def load_tools(self):
        """Scans 'tools', finds pyside_tool.py, and loads the widget."""
        tools_dir = "tools"
        tool_display_names = {
            "image_processor": "图片批量处理器",
            "MulebuyPics": "Mulebuy图片",
            "Affiliate_data": "联盟数据",
            "Translator": "文案优化"
        }

        welcome_widget = QLabel("欢迎使用 Allen 工作台\n\n请从左侧选择一个工具")
        welcome_widget.setAlignment(Qt.AlignCenter)
        self.stacked_widget.addWidget(welcome_widget)

        available_tools = [d for d in os.listdir(tools_dir) if os.path.isdir(os.path.join(tools_dir, d)) and not d.startswith('__')]

        for tool_name in available_tools:
            display_name = tool_display_names.get(tool_name, tool_name)
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, tool_name)
            self.sidebar.addItem(item)

            tool_widget = self.load_tool_widget(tool_name, display_name)
            self.stacked_widget.addWidget(tool_widget)
            self.tool_widgets[tool_name] = tool_widget

        if self.sidebar.count() > 0:
            self.sidebar.setCurrentRow(0)
            self.switch_tool(self.sidebar.item(0))

    def load_tool_widget(self, tool_name, display_name):
        """Dynamically loads a widget from a tool's pyside_tool.py file."""
        try:
            module_path = f"tools.{tool_name}.pyside_tool"
            tool_module = importlib.import_module(module_path)

            # Find the QWidget class in the module
            for attribute_name in dir(tool_module):
                attribute = getattr(tool_module, attribute_name)
                if isinstance(attribute, type) and issubclass(attribute, QWidget) and attribute is not QWidget:
                    print(f"Found widget {attribute_name} in {tool_name}")
                    return attribute() # Instantiate the widget

            # Fallback if no specific widget is found
            return self.create_placeholder_widget(f"{display_name}\n\n在pyside_tool.py中未找到QWidget。")

        except ImportError as e:
            print(f"Could not import {module_path}: {e}")
            return self.create_placeholder_widget(f"无法加载工具: {display_name}\n\n请确保 'pyside_tool.py' 文件存在。")
        except Exception as e:
            print(f"Error loading widget for {tool_name}: {e}")
            return self.create_placeholder_widget(f"加载 {display_name} 时出错。")

    def create_placeholder_widget(self, text):
        """Creates a standard placeholder widget."""
        widget = QLabel(text)
        widget.setAlignment(Qt.AlignCenter)
        widget.setWordWrap(True)
        return widget

    def switch_tool(self, item):
        """Switches the view in the QStackedWidget to the selected tool."""
        tool_name = item.data(Qt.UserRole)

        # This logic will be expanded later to load the actual tool widget
        if tool_name in self.tool_widgets:
            widget_to_display = self.tool_widgets[tool_name]
            self.stacked_widget.setCurrentWidget(widget_to_display)
        else:
            # This case handles the welcome screen or any item without a tool_name
            self.stacked_widget.setCurrentIndex(0)


def load_stylesheet():
    """Loads an external QSS stylesheet."""
    style_file = "styles.qss"
    if os.path.exists(style_file):
        with open(style_file, "r") as f:
            return f.read()
    else:
        print(f"Warning: Stylesheet '{style_file}' not found.")
        return ""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply the stylesheet
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
