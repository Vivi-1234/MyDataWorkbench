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
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar_widget)

        # AI Model Selector
        sidebar_layout.addWidget(QLabel("🧠 AI模型选择:"))
        self.model_selector = QComboBox()
        self.available_models = [
            "mulebuy-optimizer", "llama3.1:latest", "qwen3:8b", "gemma3:4b", "gpt-oss:20b"
        ]
        self.model_selector.addItems(self.available_models)
        sidebar_layout.addWidget(self.model_selector)
        sidebar_layout.addWidget(QLabel("---------------------")) # Separator

        self.tool_list_widget = QListWidget()
        self.tool_list_widget.itemClicked.connect(self.switch_tool)
        sidebar_layout.addWidget(self.tool_list_widget)

        # --- Central Widget Area ---
        self.stacked_widget = QStackedWidget()

        main_layout.addWidget(sidebar_widget)
        main_layout.addWidget(self.stacked_widget)

        self.setCentralWidget(main_widget)

        self.tool_widgets = {}
        self.load_tools()

    def get_selected_model(self):
        return self.model_selector.currentText()

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
            self.tool_list_widget.addItem(item)

            tool_widget = self.load_tool_widget(tool_name, display_name)
            self.stacked_widget.addWidget(tool_widget)
            self.tool_widgets[tool_name] = tool_widget

        if self.tool_list_widget.count() > 0:
            self.tool_list_widget.setCurrentRow(0)
            self.switch_tool(self.tool_list_widget.item(0))

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
                    return attribute(main_window=self) # Pass main window instance

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


from qt_material import apply_stylesheet

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply the material theme
    apply_stylesheet(app, theme='dark_pink.xml')

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
