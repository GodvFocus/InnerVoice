"""悬浮窗主窗口 - 无边框、置顶、底部居中的横向底栏"""

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QPalette, QEnterEvent
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QApplication,
    QGraphicsDropShadowEffect,
)

from shared.types.enums import AppState
from modules.overlay.status_indicator import StatusIndicator


# 样式常量
BG_COLOR = "#1e1e2e"
TEXT_COLOR = "#cdd6f4"
SUB_TEXT_COLOR = "#a6adc4"
BTN_CONFIRM_BG = "#cba6f7"
BTN_CONFIRM_TEXT = "#1e1e2e"
BTN_CANCEL_BORDER = "#585b70"
BORDER_RADIUS = 10
PANEL_WIDTH = 480
PANEL_HEIGHT = 42
OFFSET_Y = 60  # 距屏幕底部距离


def _button_style(bg: str, fg: str) -> str:
    return f"""
        QPushButton {{
            background: {bg};
            color: {fg};
            border: none;
            border-radius: 5px;
            padding: 5px 14px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            opacity: 0.85;
        }}
    """


class OverlayWindow(QWidget):
    """无边框悬浮窗, 底部居中

    用法:
        window = OverlayWindow()
        state_machine.state_changed.connect(window.on_state_changed)
        window.show()
    """

    def __init__(self):
        super().__init__()
        self._setup_window()
        self._setup_ui()
        self._setup_shadow()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(PANEL_WIDTH, PANEL_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 暗色背景
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(BG_COLOR))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # 指示灯
        self._indicator = StatusIndicator(self)
        layout.addWidget(self._indicator)

        # 状态标签
        self._status_label = QLabel("")
        self._status_label.setFont(QFont("Microsoft YaHei", 10))
        self._status_label.setStyleSheet(f"color: {SUB_TEXT_COLOR};")
        self._status_label.setFixedWidth(48)
        layout.addWidget(self._status_label)

        # 文本预览
        self._text_label = QLabel("")
        self._text_label.setFont(QFont("Microsoft YaHei", 12))
        self._text_label.setStyleSheet(f"color: {TEXT_COLOR};")
        self._text_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self._text_label, stretch=1)

        # 确认按钮
        self._btn_confirm = QPushButton("确认")
        self._btn_confirm.setStyleSheet(_button_style(BTN_CONFIRM_BG, BTN_CONFIRM_TEXT))
        self._btn_confirm.setVisible(False)
        layout.addWidget(self._btn_confirm)

        # 取消按钮
        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setStyleSheet(
            _button_style("transparent", SUB_TEXT_COLOR)
            + f"border: 1px solid {BTN_CANCEL_BORDER};"
        )
        self._btn_cancel.setVisible(False)
        layout.addWidget(self._btn_cancel)

    def _setup_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    # --- 公开接口 ---

    def confirm_button(self) -> QPushButton:
        return self._btn_confirm

    def cancel_button(self) -> QPushButton:
        return self._btn_cancel

    def set_text(self, text: str):
        self._text_label.setText(text)

    def text(self) -> str:
        return self._text_label.text()

    def on_state_changed(self, new_state: AppState, _old_state: AppState):
        """接收状态机信号, 更新面板显隐和 UI"""
        self._indicator.on_state_changed(new_state, _old_state)

        if new_state == AppState.IDLE:
            self.hide()
            return

        self._position_at_bottom_center()

        if new_state == AppState.LISTENING:
            self._status_label.setText("录音中")
            self._btn_confirm.setVisible(False)
            self._btn_cancel.setVisible(False)
            self.show()

        elif new_state == AppState.PROCESSING:
            self._status_label.setText("识别中...")
            self._btn_confirm.setVisible(False)
            self._btn_cancel.setVisible(False)
            self.show()

        elif new_state == AppState.PREVIEW:
            self._status_label.setText("完成")
            self._btn_confirm.setVisible(True)
            self._btn_cancel.setVisible(True)
            self.show()

        elif new_state == AppState.ERROR:
            self._status_label.setText("错误")
            self._btn_confirm.setVisible(False)
            self._btn_cancel.setVisible(True)
            self._btn_cancel.setText("关闭")
            self.show()

    def _position_at_bottom_center(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = (geo.width() - PANEL_WIDTH) // 2
        y = geo.bottom() - PANEL_HEIGHT - OFFSET_Y
        self.move(QPoint(x, y))
