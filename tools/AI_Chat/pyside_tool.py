import sys, os, json, requests
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel
from PySide6.QtCore import QObject, QThread, Signal, Qt

class ChatWorker(QObject):
    response_ready = Signal(str)
    error = Signal(str)

    def __init__(self, model, messages):
        super().__init__()
        self.model = model
        self.messages = messages
        self.api_url = "http://localhost:11434/api/chat"

    def run(self):
        try:
            payload = {
                "model": self.model,
                "messages": self.messages,
                "stream": False # Keep it simple, no streaming for now
            }
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()

            response_data = response.json()
            ai_message = response_data.get("message", {}).get("content", "")
            self.response_ready.emit(ai_message)

        except requests.exceptions.RequestException as e:
            self.error.emit(f"API请求失败: {e}")
        except Exception as e:
            self.error.emit(f"发生未知错误: {e}")

class AIChatWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.threads = []
        self.messages = []

        # --- UI Setup ---
        layout = QVBoxLayout(self)

        title = QLabel("🤖 AI 聊天"); title.setObjectName("title")
        layout.addWidget(title)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setPlaceholderText("在这里开始对话...")
        layout.addWidget(self.chat_history)

        input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("输入消息...")
        self.send_button = QPushButton("发送")

        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)

        # --- Connections ---
        self.send_button.clicked.connect(self.send_message)
        self.user_input.returnPressed.connect(self.send_message)

    def send_message(self):
        user_text = self.user_input.text().strip()
        if not user_text:
            return

        # Append user message to history and UI
        self.messages.append({"role": "user", "content": user_text})
        self.chat_history.append(f"<b>You:</b> {user_text}")
        self.user_input.clear()

        # Disable input while waiting for response
        self.user_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.chat_history.append("<i>AI 正在思考...</i>")

        # Get selected model from main window
        selected_model = "llama3.1:latest" # Default model
        if self.main_window and hasattr(self.main_window, 'get_selected_model'):
            selected_model = self.main_window.get_selected_model()

        # Start worker thread for API call
        self.start_chat_worker(selected_model)

    def start_chat_worker(self, model):
        thread = QThread()
        worker = ChatWorker(model, self.messages)
        worker.moveToThread(thread)

        worker.response_ready.connect(self.handle_response)
        worker.error.connect(self.handle_error)

        # Cleanup
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.started.connect(worker.run)
        thread.start()
        self.threads.append(thread)

    def handle_response(self, ai_text):
        # Remove "thinking" message
        self.chat_history.undo()

        self.messages.append({"role": "assistant", "content": ai_text})
        self.chat_history.append(f"<b style='color:#f43f5e;'>AI:</b> {ai_text}\n")

        self.user_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.user_input.setFocus()

    def handle_error(self, error_message):
        self.chat_history.undo()
        self.chat_history.append(f"<b style='color:red;'>错误:</b> {error_message}\n")
        self.user_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.user_input.setFocus()

    def closeEvent(self, event):
        for thread in self.threads:
            thread.quit()
            thread.wait()
        super().closeEvent(event)
