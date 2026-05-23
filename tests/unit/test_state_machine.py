"""状态机单元测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from PySide6.QtCore import QCoreApplication

# 状态机测试需要 QApplication 实例 (Signal 依赖 QObject)
_app = QCoreApplication.instance()
if _app is None:
    _app = QCoreApplication([])

from modules.overlay.state_machine import StateMachine
from shared.types.enums import AppState


class TestStateMachine:
    """StateMachine 合法/非法转换测试"""

    @pytest.fixture
    def sm(self):
        return StateMachine()

    def test_initial_state_is_idle(self, sm):
        assert sm.current_state == AppState.IDLE

    def test_idle_to_listening(self, sm):
        ok = sm.transition(AppState.LISTENING)
        assert ok is True
        assert sm.current_state == AppState.LISTENING

    def test_listening_to_processing(self, sm):
        sm.transition(AppState.LISTENING)
        ok = sm.transition(AppState.PROCESSING)
        assert ok is True
        assert sm.current_state == AppState.PROCESSING

    def test_processing_to_preview(self, sm):
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PROCESSING)
        ok = sm.transition(AppState.PREVIEW)
        assert ok is True
        assert sm.current_state == AppState.PREVIEW

    def test_preview_to_idle_on_confirm(self, sm):
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PROCESSING)
        sm.transition(AppState.PREVIEW)
        ok = sm.transition(AppState.IDLE)
        assert ok is True
        assert sm.current_state == AppState.IDLE

    def test_error_to_idle(self, sm):
        sm._current_state = AppState.ERROR
        ok = sm.transition(AppState.IDLE)
        assert ok is True
        assert sm.current_state == AppState.IDLE

    def test_any_state_to_error(self, sm):
        sm.transition(AppState.LISTENING)
        ok = sm.transition(AppState.ERROR)
        assert ok is True
        assert sm.current_state == AppState.ERROR

    def test_invalid_transition_returns_false(self, sm):
        # IDLE -> PREVIEW 是不允许的
        ok = sm.transition(AppState.PREVIEW)
        assert ok is False
        assert sm.current_state == AppState.IDLE

    def test_same_state_transition_returns_false(self, sm):
        ok = sm.transition(AppState.IDLE)
        assert ok is False

    def test_state_changed_signal_emitted(self, sm):
        signals = []
        sm.state_changed.connect(lambda new, old: signals.append((new, old)))
        sm.transition(AppState.LISTENING)
        assert len(signals) == 1
        assert signals[0] == (AppState.LISTENING, AppState.IDLE)
