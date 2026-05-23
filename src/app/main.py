"""InnerVoice 语音输入法 — 应用入口

编排顺序:
    1. 创建 QApplication
    2. 初始化 Settings
    3. 初始化 StateMachine
    4. 初始化 OverlayWindow, 绑定状态信号
    5. 初始化 HotkeyManager, 启动全局监听
    6. 进入事件循环
"""

import sys
import signal
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# 确保 src 在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Settings
from modules.overlay.state_machine import StateMachine
from modules.overlay.overlay_window import OverlayWindow
from modules.hotkey.hotkey_manager import HotkeyManager
from shared.types.enums import AppState


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("InnerVoice")
    app.setQuitOnLastWindowClosed(False)  # 悬浮窗关闭不退出应用

    # 模块初始化
    settings = Settings()
    state_machine = StateMachine()
    overlay = OverlayWindow()

    # 绑定: 状态机 -> 悬浮窗
    state_machine.state_changed.connect(overlay.on_state_changed)

    # 绑定: 确认按钮 -> 状态转换 + 退出
    def on_confirm():
        text = overlay.text()
        if text:
            state_machine.transition(AppState.IDLE)
            # TODO: 文本注入 (下一阶段)
            print(f"[确认注入] {text}")

    def on_cancel():
        state_machine.transition(AppState.IDLE)

    overlay.confirm_button().clicked.connect(on_confirm)
    overlay.cancel_button().clicked.connect(on_cancel)

    # 热键管理
    hotkey_manager = HotkeyManager(state_machine, settings)
    hotkey_manager.set_text_getter(overlay.text)
    hotkey_manager.text_confirmed.connect(lambda text: print(f"[确认注入] {text}"))
    hotkey_manager.start()

    # Ctrl+C 退出
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(200)

    print("[InnerVoice] 语音输入法已启动, 长按右 Ctrl 开始说话...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
