"""全局快捷键管理测试"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from PySide6.QtCore import QCoreApplication

_app = QCoreApplication.instance()
if _app is None:
    _app = QCoreApplication([])

from modules.hotkey.hotkey_manager import HotkeyManager
from modules.overlay.state_machine import StateMachine
from shared.types.enums import AppState
from core.config.settings import Settings


class TestHotkeyManager:
    """HotkeyManager 单元测试 (mock keyboard 库)"""

    @pytest.fixture
    def sm(self):
        return StateMachine()

    @pytest.fixture
    def settings(self):
        return Settings()

    def test_initial_state_not_running(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        assert hm.is_running is False

    def test_start_stop(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        hm.start()
        assert hm.is_running is True
        hm.stop()
        assert hm.is_running is False

    def test_long_press_detection(self, sm, settings):
        """模拟长按: press -> 超时 -> transition to LISTENING"""
        hm = HotkeyManager(sm, settings)
        hm._on_press()
        hm._on_long_press_timeout()
        assert sm.current_state == AppState.LISTENING

    def test_release_after_long_press(self, sm, settings):
        """长按后释放 -> PROCESSING"""
        hm = HotkeyManager(sm, settings)
        hm._on_press()
        hm._on_long_press_timeout()
        assert sm.current_state == AppState.LISTENING
        hm._on_release()
        assert sm.current_state == AppState.PROCESSING

    def test_short_press_no_trigger(self, sm, settings):
        """短按(<阈值)不触发"""
        hm = HotkeyManager(sm, settings)
        hm._on_press()
        hm._on_release()  # 未超时就释放
        assert sm.current_state == AppState.IDLE

    def test_esc_triggers_cancel(self, sm, settings):
        """Escape 键触发取消"""
        hm = HotkeyManager(sm, settings)
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PROCESSING)
        sm.transition(AppState.PREVIEW)
        hm._on_esc()
        assert sm.current_state == AppState.IDLE

    def test_enter_triggers_confirm(self, sm, settings):
        """Enter 键触发确认"""
        hm = HotkeyManager(sm, settings)
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PROCESSING)
        sm.transition(AppState.PREVIEW)
        hm._on_enter()
        assert sm.current_state == AppState.IDLE
