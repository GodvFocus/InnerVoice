"""DeepSeek 润色客户端 — QThread 异步调用，通过 Signal 返回结果"""

from openai import OpenAI

from PySide6.QtCore import QObject, Signal, QThread


class PolishWorker(QObject):
    """在 QThread 中执行的润色工作对象"""

    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, text: str, system_prompt: str, api_key: str,
                 base_url: str, model: str, parent: QObject | None = None):
        super().__init__(parent)
        self._text = text
        self._system_prompt = system_prompt
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def run(self):
        """在 QThread 中执行"""
        try:
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": self._text},
                ],
                temperature=0.3,
                timeout=30.0,
            )
            result = response.choices[0].message.content
            self.result_ready.emit((result or "").strip())
        except Exception as e:
            self.error_occurred.emit(str(e))


class PolishClient(QObject):
    """润色客户端，管理 QThread 生命周期

    用法:
        client = PolishClient()
        client.result_ready.connect(on_result)
        client.error_occurred.connect(on_error)
        client.polish("今天开会说了一下", system_prompt, api_key, base_url, model)
    """

    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: PolishWorker | None = None
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    def polish(self, text: str, system_prompt: str, api_key: str,
               base_url: str, model: str):
        """异步发起润色请求"""
        if self._busy:
            self.error_occurred.emit("润色正在进行中，请稍后再试")
            return

        self._busy = True
        self._thread = QThread()
        self._worker = PolishWorker(text, system_prompt, api_key, base_url, model)

        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result_ready.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, result: str):
        self._cleanup()
        self.result_ready.emit(result)

    def _on_error(self, error: str):
        self._cleanup()
        self.error_occurred.emit(error)

    def _cleanup(self):
        self._busy = False
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.quit()
            self._thread.finished.connect(self._on_thread_finished)

    def _on_thread_finished(self):
        self._thread = None
