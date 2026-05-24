"""InnerVoice 语音输入法 — 应用入口

编排顺序:
    1. 创建 QApplication
    2. 初始化 Settings
    3. 初始化 StateMachine
    4. 初始化 OverlayWindow, 绑定状态信号
    5. 初始化 AudioCapture + IATClient
    6. 初始化 HotkeyManager, 绑定 ASR 启停
    7. 进入事件循环
"""

import sys
import signal
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Settings
from db.database import init_db
from modules.polish.prompt_manager import PromptManager
from modules.overlay.state_machine import StateMachine
from modules.overlay.overlay_window import OverlayWindow
from modules.hotkey.hotkey_manager import HotkeyManager
from modules.asr.audio_capture import AudioCapture
from modules.asr.iat_client import IATClient
from modules.injector.text_injector import TextInjector
from shared.types.enums import AppState
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("InnerVoice")
    app.setQuitOnLastWindowClosed(False)

    # 模块初始化
    settings = Settings()

    # 数据库与主窗口初始化
    data_dir = Path(__file__).parent.parent.parent / "data"
    db_path = init_db(data_dir)
    prompt_manager = PromptManager(db_path)
    main_window = MainWindow(prompt_manager)
    main_window.show()

    state_machine = StateMachine()
    overlay = OverlayWindow()

    asr_config = settings.get("asr")
    audio_capture = AudioCapture()
    target_window: int | None = None
    iat_client = IATClient(
        appid=asr_config["appid"],
        apikey=asr_config["apikey"],
        apisecret=asr_config["apisecret"],
    )

    # 绑定: 状态机 -> 悬浮窗
    state_machine.state_changed.connect(overlay.on_state_changed)

    # 绑定: AudioCapture -> IATClient (音频数据传递)
    audio_capture.audio_chunk.connect(iat_client.send_audio)

    # 绑定: IATClient 握手完成 -> 启动录音 (避免提前发送音频)
    iat_client.connected.connect(audio_capture.start)

    # 绑定: IATClient -> OverlayWindow (流式文本)
    iat_client.partial_result.connect(overlay.set_text)

    # 绑定: IATClient 最终结果 -> PREVIEW 状态
    def on_final_result(text: str):
        audio_capture.stop()
        iat_client.disconnect()
        overlay.set_text(text)
        state_machine.transition(AppState.PREVIEW)

    iat_client.final_result.connect(on_final_result)

    # 绑定: 错误处理
    def on_asr_error(msg: str):
        print(f"[ASR Error] {msg}")
        if state_machine.current_state in (AppState.LISTENING, AppState.PROCESSING):
            audio_capture.stop()
            iat_client.disconnect()
            overlay.set_text(msg)
            state_machine.transition(AppState.ERROR)

    audio_capture.error_occurred.connect(on_asr_error)
    iat_client.error_occurred.connect(on_asr_error)

    # 热键管理
    hotkey_manager = HotkeyManager(state_machine, settings)

    # 绑定: 热键 -> ASR 启停
    hotkey_manager.asr_start_requested.connect(iat_client.connect)
    hotkey_manager.asr_stop_requested.connect(audio_capture.stop)
    hotkey_manager.asr_stop_requested.connect(iat_client.send_end)

    # 绑定: 确认 -> 文本注入
    def on_confirm(text: str):
        nonlocal target_window
        if TextInjector.inject_to_window(text, target_window):
            target_window = None

    hotkey_manager.set_text_getter(overlay.text)
    hotkey_manager.text_confirmed.connect(on_confirm)

    # 绑定: ASR 资源清理 (在状态退回 IDLE 时统一执行)
    def on_cleanup(new_state: AppState, old_state: AppState):
        nonlocal target_window
        if new_state == AppState.IDLE and old_state in (AppState.LISTENING, AppState.PROCESSING):
            audio_capture.stop()
            iat_client.disconnect()
        if new_state == AppState.IDLE:
            target_window = None
            overlay.set_text("")

    state_machine.state_changed.connect(on_cleanup)

    # 在开始录音前记录当前输入窗口，确认时恢复焦点后再粘贴
    def on_asr_start():
        nonlocal target_window
        target_window = TextInjector.current_window()

    hotkey_manager.asr_start_requested.connect(on_asr_start)

    # 按钮: 只做状态转换, 资源清理由 on_cleanup 统一处理
    overlay.confirm_button().clicked.connect(
        lambda: (
            on_confirm(overlay.text()),
            state_machine.transition(AppState.IDLE),
        )
    )
    overlay.cancel_button().clicked.connect(
        lambda: state_machine.transition(AppState.IDLE)
    )

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
