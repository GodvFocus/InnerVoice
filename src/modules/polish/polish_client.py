"""DeepSeek 润色客户端 — QThread 异步调用，通过 Signal 返回结果"""

from openai import OpenAI

from PySide6.QtCore import QObject, Signal, QThread


CORE_POLISH_SYSTEM_PROMPT = (
    "你是应用内置的文本润色助手。"
    "你必须始终输出用户的最终意图，主动丢弃所有被后文否定、修正或放弃的前文片段。"
    "如果用户在一句话里发生改口、自我纠正、时间修正、数字修正、对象修正或措辞回撤，"
    "只保留最终确认的那部分意思进行润色。"
    "保持最终意图不变，不补充用户未表达的新信息。"
    "只返回润色后的最终文本，不要解释，不要加引号，不要使用 Markdown。"
)


def _content_part_to_text(part) -> str:
    if part is None:
        return ""

    if isinstance(part, str):
        return part

    if isinstance(part, dict):
        if isinstance(part.get("text"), str):
            return part["text"]
        if isinstance(part.get("content"), str):
            return part["content"]
        text_obj = part.get("text")
        if hasattr(text_obj, "value") and isinstance(text_obj.value, str):
            return text_obj.value
        return ""

    text = getattr(part, "text", None)
    if isinstance(text, str):
        return text
    if hasattr(text, "value") and isinstance(text.value, str):
        return text.value

    content = getattr(part, "content", None)
    if isinstance(content, str):
        return content

    return ""


def _extract_text_from_response(response) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise ValueError("LLM 未返回 choices")

    message = getattr(choices[0], "message", None)
    if message is None:
        raise ValueError("LLM 返回中缺少 message")

    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text = "".join(_content_part_to_text(part) for part in content).strip()
        if text:
            return text

    raise ValueError("LLM 返回内容为空或格式不支持")


def _is_parse_error(error: Exception) -> bool:
    return isinstance(error, ValueError)


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
                    {
                        "role": "system",
                        "content": CORE_POLISH_SYSTEM_PROMPT,
                    },
                    {
                        "role": "system",
                        "content": self._system_prompt.rstrip(),
                    },
                    {"role": "user", "content": self._text},
                ],
                temperature=0.3,
                timeout=30.0,
            )
            self.result_ready.emit(_extract_text_from_response(response))
        except Exception as e:
            if _is_parse_error(e):
                self.result_ready.emit(self._text)
                return
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
