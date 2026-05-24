"""状态机 - 管理 5 状态转换规则, 通过 Signal 通知 UI"""

from PySide6.QtCore import QObject, Signal

from shared.types.enums import AppState


TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.IDLE:       {AppState.LISTENING},
    AppState.LISTENING:  {AppState.PROCESSING, AppState.IDLE, AppState.ERROR},
    AppState.PROCESSING: {AppState.PREVIEW, AppState.IDLE, AppState.ERROR},
    AppState.PREVIEW:    {AppState.IDLE, AppState.ERROR},
    AppState.ERROR:      {AppState.IDLE},
}


class StateMachine(QObject):
    """五状态语音输入状态机

    状态:
        IDLE -> LISTENING -> PROCESSING -> PREVIEW -> IDLE
        任意状态 -> ERROR -> IDLE
    """

    state_changed = Signal(AppState, AppState)  # new_state, old_state

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._current_state = AppState.IDLE

    @property
    def current_state(self) -> AppState:
        return self._current_state

    def transition(self, to_state: AppState) -> bool:
        """尝试状态转换, 返回是否成功"""
        if to_state == self._current_state:
            return False
        allowed = TRANSITIONS.get(self._current_state, set())
        if to_state == AppState.ERROR or to_state in allowed:
            old = self._current_state
            self._current_state = to_state
            self.state_changed.emit(to_state, old)
            return True
        return False
