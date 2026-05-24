"""全局快捷键管理 - keyboard 库监听长按右 Ctrl"""

import threading
import time

import keyboard

from PySide6.QtCore import QObject, Signal

from shared.types.enums import AppState
from modules.overlay.state_machine import StateMachine
from core.config.settings import Settings


class HotkeyManager(QObject):
    """全局热键监听, 检测长按右 Ctrl 触发语音输入

    快捷键行为:
        长按右 Ctrl (> threshold_ms) -> 唤起录音 (LISTENING)
        松开右 Ctrl -> 结束录音, 等待最终结果
        Enter -> 确认注入 (仅在 PREVIEW 状态)
        Escape -> 取消 (LISTENING / PREVIEW 状态)
    """

    text_confirmed = Signal(str)    # 用户确认后的文本
    asr_start_requested = Signal()  # 请求开始 ASR 录音
    asr_stop_requested = Signal()   # 请求停止 ASR 录音

    def __init__(self, state_machine: StateMachine, settings: Settings, parent: QObject | None = None):
        super().__init__(parent)
        self._sm = state_machine
        self._settings = settings
        self._running = False
        self._press_timer: threading.Timer | None = None
        self._is_pressed = False
        self._thread: threading.Thread | None = None
        self._text_getter: callable | None = None

    def set_text_getter(self, getter: callable):
        self._text_getter = getter

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._press_timer:
            self._press_timer.cancel()

    def _listen(self):
        hotkey_name = self._settings.get("hotkey") or "right ctrl"

        def on_press(_event=None):
            if not self._is_pressed:
                self._is_pressed = True
                self._on_press()

        def on_release(_event=None):
            if self._is_pressed:
                self._is_pressed = False
                self._on_release()

        keyboard.on_press_key(hotkey_name, on_press, suppress=False)
        keyboard.on_release_key(hotkey_name, on_release, suppress=False)

        keyboard.add_hotkey("enter", lambda: self._on_enter())
        keyboard.add_hotkey("esc", lambda: self._on_esc())

        while self._running:
            time.sleep(0.1)

    def _on_press(self):
        if self._sm.current_state != AppState.IDLE:
            return
        threshold = self._settings.get("long_press_threshold_ms") / 1000.0
        self._press_timer = threading.Timer(threshold, self._on_long_press_timeout)
        self._press_timer.start()

    def _on_release(self):
        if self._press_timer:
            self._press_timer.cancel()
            self._press_timer = None
        if self._sm.current_state == AppState.LISTENING:
            self.asr_stop_requested.emit()

    def _on_long_press_timeout(self):
        self._sm.transition(AppState.LISTENING)
        self.asr_start_requested.emit()

    def _on_enter(self):
        if self._sm.current_state == AppState.PREVIEW:
            text = self._text_getter() if self._text_getter else ""
            if text:
                self.text_confirmed.emit(text)
            self._sm.transition(AppState.IDLE)

    def _on_esc(self):
        if self._sm.current_state in (AppState.PREVIEW, AppState.LISTENING):
            self._sm.transition(AppState.IDLE)
