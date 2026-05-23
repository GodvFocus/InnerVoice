# 全局语音触发 + 基础 UI 面板 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现长按右 Ctrl 唤起悬浮语音输入面板，含状态机驱动的 UI 状态切换与脉动指示灯动画。

**Architecture:** PySide6 无边框悬浮窗 + keyboard 库全局热键监听 + 自定义 5 状态状态机 + QPropertyAnimation 动画。状态机通过 PySide6 Signal 解耦热键模块与 UI 模块。

**Tech Stack:** Python 3.10, PySide6, keyboard, pytest

**Python 路径:** `D:/anaconda3/envs/any/python.exe`

---

### Task 0: 环境准备与依赖安装

**Files:**
- Modify: `D:/anaconda3/envs/any/` (pip install)

- [ ] **Step 1: 安装 PySide6 和 keyboard**

```bash
"D:/anaconda3/envs/any/python.exe" -m pip install PySide6 keyboard pytest -q
```

- [ ] **Step 2: 验证安装**

```bash
"D:/anaconda3/envs/any/python.exe" -c "import PySide6; print('PySide6:', PySide6.__version__)"
"D:/anaconda3/envs/any/python.exe" -c "import keyboard; print('keyboard:', keyboard.__version__)"
"D:/anaconda3/envs/any/python.exe" -m pytest --version
```

---

### Task 1: 应用状态枚举

**Files:**
- Create: `src/shared/types/enums.py`
- Create: `src/shared/types/__init__.py`

- [ ] **Step 1: 编写状态枚举**

```python
"""应用状态枚举"""

from enum import Enum, auto


class AppState(Enum):
    """语音输入法的 5 个核心状态"""
    IDLE = auto()        # 待机, 面板隐藏
    LISTENING = auto()   # 录音中, 红色脉动指示灯
    PROCESSING = auto()  # 识别中, 黄色旋转指示灯
    PREVIEW = auto()     # 结果预览, 绿色静态指示灯
    ERROR = auto()       # 异常, 红色快闪指示灯
```

- [ ] **Step 2: 创建 `__init__.py`**

```python
from .enums import AppState

__all__ = ["AppState"]
```

- [ ] **Step 3: 提交**

```bash
git add src/shared/types/enums.py src/shared/types/__init__.py
git commit -m "feat(types): 添加 AppState 枚举定义"
```

---

### Task 2: 配置管理模块

**Files:**
- Create: `src/core/config/settings.py`
- Create: `src/core/config/__init__.py`
- Create: `configs/default_settings.json`
- Create: `tests/unit/test_settings.py`

- [ ] **Step 1: 创建默认配置文件**

```json
{
  "hotkey": "right ctrl",
  "long_press_threshold_ms": 300,
  "panel_width": 480,
  "panel_height": 40,
  "panel_offset_y": 60,
  "font_size": 13,
  "idle_timeout_seconds": 30
}
```

- [ ] **Step 2: 编写测试**

```python
"""配置管理模块测试"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# 将 src 加入 path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.config.settings import Settings


class TestSettings:
    """Settings 模块单元测试"""

    @pytest.fixture
    def temp_config_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_load_defaults_when_no_file(self, temp_config_dir):
        settings = Settings(config_dir=temp_config_dir)
        assert settings.get("hotkey") == "right ctrl"
        assert settings.get("long_press_threshold_ms") == 300

    def test_save_and_load(self, temp_config_dir):
        settings = Settings(config_dir=temp_config_dir)
        settings.set("hotkey", "right shift")
        settings.save()

        # 重新加载
        settings2 = Settings(config_dir=temp_config_dir)
        assert settings2.get("hotkey") == "right shift"

    def test_get_nonexistent_key_returns_none(self, temp_config_dir):
        settings = Settings(config_dir=temp_config_dir)
        assert settings.get("nonexistent") is None

    def test_set_persists_in_memory(self, temp_config_dir):
        settings = Settings(config_dir=temp_config_dir)
        settings.set("panel_width", 600)
        assert settings.get("panel_width") == 600

    def test_defaults_not_overwritten_by_partial_save(self, temp_config_dir):
        settings = Settings(config_dir=temp_config_dir)
        settings.set("hotkey", "ctrl+shift+v")
        settings.save()

        settings2 = Settings(config_dir=temp_config_dir)
        # 其他默认值应该还在
        assert settings2.get("panel_width") == 480
        assert settings2.get("hotkey") == "ctrl+shift+v"
```

- [ ] **Step 3: 运行测试验证失败**

```bash
"D:/anaconda3/envs/any/python.exe" -m pytest tests/unit/test_settings.py -v
```
Expected: ImportError (模块尚不存在)

- [ ] **Step 4: 实现 Settings 类**

```python
"""配置管理 - JSON 文件读写, 带默认值"""

import json
from pathlib import Path
from typing import Any


DEFAULTS = {
    "hotkey": "right ctrl",
    "long_press_threshold_ms": 300,
    "panel_width": 480,
    "panel_height": 40,
    "panel_offset_y": 60,
    "font_size": 13,
    "idle_timeout_seconds": 30,
}

CONFIG_FILENAME = "settings.json"


class Settings:
    """用户配置管理, 默认值 + JSON 持久化"""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent.parent / "configs"
        self._config_dir = Path(config_dir)
        self._config_path = self._config_dir / CONFIG_FILENAME
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    def _load(self):
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def all(self) -> dict[str, Any]:
        return dict(self._data)
```

- [ ] **Step 5: 创建 `__init__.py`**

```python
from .settings import Settings

__all__ = ["Settings"]
```

- [ ] **Step 6: 运行测试验证通过**

```bash
"D:/anaconda3/envs/any/python.exe" -m pytest tests/unit/test_settings.py -v
```
Expected: 5 passed

- [ ] **Step 7: 提交**

```bash
git add src/core/config/settings.py src/core/config/__init__.py configs/default_settings.json tests/unit/test_settings.py
git commit -m "feat(config): 实现 Settings 配置管理模块"
```

---

### Task 3: 状态机

**Files:**
- Create: `src/modules/overlay/state_machine.py`
- Create: `tests/unit/test_state_machine.py`

- [ ] **Step 1: 编写状态机测试**

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
"D:/anaconda3/envs/any/python.exe" -m pytest tests/unit/test_state_machine.py -v
```
Expected: ImportError (模块尚不存在)

- [ ] **Step 3: 实现 StateMachine**

```python
"""状态机 - 管理 5 状态转换规则, 通过 Signal 通知 UI"""

from PySide6.QtCore import QObject, Signal

from shared.types.enums import AppState


# 合法转换表: from_state -> {to_state, ...}
TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.IDLE:       {AppState.LISTENING},
    AppState.LISTENING:  {AppState.PROCESSING, AppState.ERROR},
    AppState.PROCESSING: {AppState.PREVIEW, AppState.ERROR},
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
        # ERROR 状态可以从任意状态进入
        if to_state == AppState.ERROR or to_state in allowed:
            old = self._current_state
            self._current_state = to_state
            self.state_changed.emit(to_state, old)
            return True
        return False
```

- [ ] **Step 4: 运行测试验证通过**

```bash
"D:/anaconda3/envs/any/python.exe" -m pytest tests/unit/test_state_machine.py -v
```
Expected: 11 passed

- [ ] **Step 5: 提交**

```bash
git add src/modules/overlay/state_machine.py tests/unit/test_state_machine.py
git commit -m "feat(state): 实现 StateMachine 状态机"
```

---

### Task 4: 脉动指示灯组件

**Files:**
- Create: `src/modules/overlay/status_indicator.py`

- [ ] **Step 1: 实现 StatusIndicator**

```python
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

    def paintEvent(self, event):
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
```
由于此组件依赖 PySide6 渲染, 不做自动化单元测试。将通过人工目视验证动画效果。

- [ ] **Step 2: 提交**

```bash
git add src/modules/overlay/status_indicator.py
git commit -m "feat(ui): 实现 StatusIndicator 脉动指示灯组件"
```

---

### Task 5: 悬浮窗主窗口

**Files:**
- Create: `src/modules/overlay/overlay_window.py`

- [ ] **Step 1: 实现 OverlayWindow**

```python
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
```

此组件依赖 PySide6 窗口系统, 不做自动化单元测试。将通过启动应用人工验证悬浮窗位置和动画。

- [ ] **Step 2: 提交**

```bash
git add src/modules/overlay/overlay_window.py
git commit -m "feat(ui): 实现 OverlayWindow 无边框悬浮窗"
```

---

### Task 6: 全局快捷键管理

**Files:**
- Create: `src/modules/hotkey/hotkey_manager.py`
- Create: `tests/unit/test_hotkey_manager.py`

- [ ] **Step 1: 编写测试**

```python
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
        # 模拟 keyboard 回调触发
        hm._on_press()
        # 手动触发长按超时逻辑
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
"D:/anaconda3/envs/any/python.exe" -m pytest tests/unit/test_hotkey_manager.py -v
```
Expected: ImportError (模块尚不存在)

- [ ] **Step 3: 实现 HotkeyManager**

```python
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
        # keyboard.unhook_all() 在 daemon 线程退出时自然释放

    def _listen(self):
        """后台线程: 注册 keyboard 钩子"""
        hotkey = self._settings.get("hotkey")
        threshold = self._settings.get("long_press_threshold_ms") / 1000.0
        hotkey_name = "right ctrl"

        def on_press(event):
            if event.name == hotkey_name and not self._is_pressed:
                self._is_pressed = True
                self._on_press()

        def on_release(event):
            if event.name == hotkey_name and self._is_pressed:
                self._is_pressed = False
                self._on_release()

        keyboard.on_press(on_press, suppress=False)
        keyboard.on_release(on_release, suppress=False)

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
        """Enter: 确认注入"""
        if self._sm.current_state == AppState.PREVIEW:
            # 文本由 overlay_window 提供, 这里先发信号
            self._sm.transition(AppState.IDLE)

    def _on_esc(self):
        """Escape: 取消"""
        if self._sm.current_state in (AppState.PREVIEW, AppState.LISTENING, AppState.PROCESSING):
            self._sm.transition(AppState.IDLE)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
"D:/anaconda3/envs/any/python.exe" -m pytest tests/unit/test_hotkey_manager.py -v
```
Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add src/modules/hotkey/hotkey_manager.py tests/unit/test_hotkey_manager.py
git commit -m "feat(hotkey): 实现 HotkeyManager 全局快捷键管理"
```

---

### Task 7: 应用入口 & 模块编排

**Files:**
- Create: `src/app/main.py`

- [ ] **Step 1: 实现 main.py**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add src/app/main.py
git commit -m "feat(app): 实现 main.py 应用入口与模块编排"
```

---

### Task 8: 集成验证

- [ ] **Step 1: 启动应用**

```bash
"D:/anaconda3/envs/any/python.exe" "D:/LearnPython/InnerVoice/src/app/main.py"
```

- [ ] **Step 2: 人工验证清单**
  - [ ] 启动后终端打印启动成功信息
  - [ ] 界面不出现 (IDLE 状态隐藏)
  - [ ] 长按右 Ctrl 300ms+ 后, 底部出现横向底栏
  - [ ] 指示灯红色脉动动画流畅
  - [ ] 状态文字显示"录音中"
  - [ ] 松开右 Ctrl, 状态变为"识别中...", 指示灯黄色
  - [ ] 按 Escape 取消, 面板消失
  - [ ] 再次长按唤起, 松开后手动调用 `state_machine.transition(AppState.PREVIEW)` 可看到确认/取消按钮

- [ ] **Step 3: 运行所有单元测试**

```bash
"D:/anaconda3/envs/any/python.exe" -m pytest tests/unit/ -v
```

- [ ] **Step 4: 提交最终状态**

```bash
git add -A
git commit -m "feat: 完成全局语音触发和基础 UI 面板 (F1 + F3)"
```
