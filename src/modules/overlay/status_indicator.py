"""脉动指示灯 - 根据 AppState 显示不同颜色和动画"""

from PySide6.QtCore import Qt, QPropertyAnimation, Property, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QBrush
from PySide6.QtWidgets import QWidget

from shared.types.enums import AppState


# 各状态对应的指示灯颜色
COLORS = {
    AppState.IDLE:       QColor("#6c7086"),  # 灰色
    AppState.LISTENING:  QColor("#f38ba8"),  # 红色
    AppState.PROCESSING: QColor("#f9e2af"),  # 黄色
    AppState.PREVIEW:    QColor("#a6e3a1"),  # 绿色
    AppState.ERROR:      QColor("#f38ba8"),  # 红色
}

DIAMETER = 12


class StatusIndicator(QWidget):
    """脉动指示灯, 绑定到 StateMachine.state_changed 信号

    用法:
        indicator = StatusIndicator()
        state_machine.state_changed.connect(indicator.on_state_changed)
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = COLORS[AppState.IDLE]
        self._pulse_scale = 1.0  # 呼吸缩放, 1.0~1.5
        self.setFixedSize(DIAMETER + 4, DIAMETER + 4)
        self._anim = QPropertyAnimation(self, b"pulse_scale")
        self._anim.setDuration(800)
        self._anim.setLoopCount(-1)  # 无限循环

    def _get_pulse_scale(self) -> float:
        return self._pulse_scale

    def _set_pulse_scale(self, value: float):
        self._pulse_scale = value
        self.update()

    pulse_scale = Property(float, _get_pulse_scale, _set_pulse_scale)

    def on_state_changed(self, new_state: AppState, _old_state: AppState):
        self._color = COLORS[new_state]
        self._anim.stop()

        if new_state == AppState.LISTENING:
            # 呼吸效果: 1.0 <-> 1.5
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(1.5)
            self._anim.setEasingCurve(QEasingCurve.InOutSine)
            self._anim.start()
        elif new_state == AppState.PROCESSING:
            # 旋转感: 快速脉冲
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(1.3)
            self._anim.setDuration(400)
            self._anim.setEasingCurve(QEasingCurve.InOutQuad)
            self._anim.start()
        elif new_state == AppState.ERROR:
            # 快闪
            self._anim.setStartValue(1.0)
            self._anim.setEndValue(1.8)
            self._anim.setDuration(200)
            self._anim.setLoopCount(3)
            self._anim.setEasingCurve(QEasingCurve.Linear)
            self._anim.start()
        else:
            self._pulse_scale = 1.0
            self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        radius = (DIAMETER / 2) * self._pulse_scale

        # 外发光
        glow = QColor(self._color)
        glow.setAlpha(40)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, int(radius * 1.6), int(radius * 1.6))

        # 实心圆
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(center, int(radius), int(radius))
