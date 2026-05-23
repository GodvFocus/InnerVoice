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

    用法:
        manager = HotkeyManager(state_machine, settings)
        manager.start()  # 启动全局监听

    快捷键行为:
        长按右 Ctrl (> threshold_ms) -> 唤起录音 (LISTENING)
        松开右 Ctrl -> 结束录音 (PROCESSING)
        Enter -> 确认注入 (仅在 PREVIEW 状态)
        Escape -> 取消 (仅在 PREVIEW 状态)
    """

    text_confirmed = Signal(str)  # 用户确认后的文本

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
        """设置文本获取回调, 用于 Enter 确认时获取 overlay 中的文本"""
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
        """后台线程: 注册 keyboard 钩子"""
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

        # Enter / Escape 全局监听
        keyboard.add_hotkey("enter", lambda: self._on_enter())
        keyboard.add_hotkey("esc", lambda: self._on_esc())

        # 保持线程存活
        while self._running:
            time.sleep(0.1)

    def _on_press(self):
        """按键按下: 启动长按计时器"""
        if self._sm.current_state != AppState.IDLE:
            return
        threshold = self._settings.get("long_press_threshold_ms") / 1000.0
        self._press_timer = threading.Timer(threshold, self._on_long_press_timeout)
        self._press_timer.start()

    def _on_release(self):
        """按键释放: 取消计时器或触发状态转换"""
        if self._press_timer:
            self._press_timer.cancel()
            self._press_timer = None
        if self._sm.current_state == AppState.LISTENING:
            self._sm.transition(AppState.PROCESSING)

    def _on_long_press_timeout(self):
        """长按超时: 触发 LISTENING 状态"""
        self._sm.transition(AppState.LISTENING)

    def _on_enter(self):
        """Enter: 确认注入, 发射 text_confirmed 信号"""
        if self._sm.current_state == AppState.PREVIEW:
            text = self._text_getter() if self._text_getter else ""
            if text:
                self.text_confirmed.emit(text)
            self._sm.transition(AppState.IDLE)

    def _on_esc(self):
        """Escape: 取消"""
        if self._sm.current_state in (AppState.PREVIEW, AppState.LISTENING, AppState.PROCESSING):
            self._sm.transition(AppState.IDLE)
