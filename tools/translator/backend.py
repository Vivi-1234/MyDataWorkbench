import os
import json
import requests
import pandas as pd
from zipfile import ZipFile
import io
from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QFileDialog

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_DATA_PATH = os.path.join(BASE_PATH, "data", "en")

def _ai_assisted_translation(model, page, base, original, lang):
    prompt = f"TARGET LANGUAGE: {lang}\nPAGE CONTEXT: {page}\nSOURCE (English): \"{base}\""
    if original and original != "【缺失】":
        prompt += f"\nCURRENT ({lang}): \"{original}\""
    try:
        response = requests.post("http://localhost:11434/api/chat", json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}, timeout=120)
        response.raise_for_status()
        ai_result = response.json()['message']['content'].strip()
        return ai_result.strip('\'"')
    except Exception as e: return f"【AI调用失败: {e}】"

class TranslatorWorker(QObject):
    finished = Signal(str)
    def __init__(self, model, lang, base_content, target_content):
        super().__init__(); self.model, self.lang, self.base, self.target = model, lang, base_content, target_content
    def run(self):
        results = {}
        for fname, fdata in self.base.items():
            if fname not in self.target: continue
            results[fname] = {k: _ai_assisted_translation(self.model, fname, v, self.target[fname].get(k), self.lang) for k, v in fdata.items()}
        self.finished.emit(json.dumps(results, ensure_ascii=False))

class TranslatorBackend(QObject):
    def __init__(self, main_window):
        super().__init__(); self.main_window = main_window; self.thread = None
    def run_js(self, code): self.main_window.view.page().runJavaScript(code)

    @Slot(result=str)
    def get_base_files(self):
        content = {}
        try:
            for fname in os.listdir(BASE_DATA_PATH):
                if fname.endswith('.json'):
                    with open(os.path.join(BASE_DATA_PATH, fname), 'r', encoding='utf-8') as f: content[fname] = json.load(f)
            return json.dumps(content)
        except Exception as e: return json.dumps({"error": str(e)})

    @Slot(result=str)
    def open_translation_files(self):
        files, _ = QFileDialog.getOpenFileNames(self.main_window, "选择翻译文件", "", "JSON (*.json)")
        if not files: return json.dumps({})
        content = {}
        try:
            for file in files:
                with open(file, 'r', encoding='utf-8') as f: content[os.path.basename(file)] = json.load(f)
            return json.dumps(content)
        except Exception as e: return json.dumps({"error": str(e)})

    @Slot(str, str, str, str)
    def start_translation(self, lang, model, base_files_str, target_files_str):
        if self.thread and self.thread.isRunning(): self.run_js("alert('已有任务在运行中。');"); return
        self.thread = QThread()
        worker = TranslatorWorker(model, lang, json.loads(base_files_str), json.loads(target_files_str))
        worker.moveToThread(self.thread)
        worker.finished.connect(lambda r: self.run_js(f"onAiTranslationFinished('{r}');"))
        worker.finished.connect(self.thread.quit); worker.deleteLater(); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.started.connect(worker.run); self.thread.start()
