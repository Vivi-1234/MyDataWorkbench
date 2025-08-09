from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class TestToolWidget(QWidget):
    """
    A minimal test widget. It displays a single, brightly colored label.
    If this widget's content is visible, it proves that the main application's
    tool loading and display mechanism is working correctly.
    """
    def __init__(self, main_window=None):
        super().__init__()

        # Use the more robust setLayout() pattern
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("Hello World!\n\nIf you can see this, the test was successful.")

        # Use a very obvious style to ensure it's visible
        label.setStyleSheet("""
            background-color: lightgreen;
            color: black;
            font-size: 24px;
            font-weight: bold;
            padding: 20px;
            border: 2px solid darkgreen;
        """)

        layout.addWidget(label)
        self.setLayout(layout)
