"""全局快捷键管理测试 — 4 状态 + ASR 信号"""

import sys
from pathlib import Path

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
    """HotkeyManager 单元测试"""

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
        hm = HotkeyManager(sm, settings)
        hm._on_press()
        hm._on_long_press_timeout()
        assert sm.current_state == AppState.LISTENING

    def test_long_press_emits_asr_start(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        signals = []
        hm.asr_start_requested.connect(lambda: signals.append("start"))
        hm._on_press()
        hm._on_long_press_timeout()
        assert len(signals) == 1

    def test_release_emits_asr_stop(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        hm._on_press()
        hm._on_long_press_timeout()
        signals = []
        hm.asr_stop_requested.connect(lambda: signals.append("stop"))
        hm._on_release()
        assert len(signals) == 1

    def test_short_press_no_trigger(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        hm._on_press()
        hm._on_release()
        assert sm.current_state == AppState.IDLE

    def test_esc_in_listening_triggers_idle(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        sm.transition(AppState.LISTENING)
        hm._on_esc()
        assert sm.current_state == AppState.IDLE

    def test_esc_in_preview_triggers_idle(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PREVIEW)
        hm._on_esc()
        assert sm.current_state == AppState.IDLE

    def test_enter_in_preview_confirms_and_goes_idle(self, sm, settings):
        hm = HotkeyManager(sm, settings)
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PREVIEW)
        hm._on_enter()
        assert sm.current_state == AppState.IDLE
