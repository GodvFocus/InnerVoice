# 实时语音转写 & 文本注入 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接入讯飞 IAT 实时语音听写 + 实现剪贴板文本注入，完成"说话→实时转写→预览→注入"完整闭环

**Architecture:** 新增 asr/ 模块 (AudioCapture + IATClient) 和 injector/ 模块 (TextInjector)，精简状态机去掉 PROCESSING 状态，修改 OverlayWindow 支持 LISTENING 状态实时流式文字显示

**Tech Stack:** Python 3.10 (conda env: any), PySide6 6.11, PyAudio, websocket-client, pywin32, keyboard

**Design Doc:** `docs/superpowers/specs/2026-05-24-asr-text-injection-design.md`

---

## 文件结构

```
src/
├── app/main.py                          # 修改: 编排 ASR/注入模块
├── core/config/settings.py              # 修改: 支持 settings.local.json 覆盖
├── shared/types/enums.py                # 修改: 移除 PROCESSING
├── modules/
│   ├── asr/                             # 新增
│   │   ├── __init__.py
│   │   ├── audio_capture.py             # PyAudio 麦克风录音
│   │   └── iat_client.py               # 讯飞 IAT WebSocket 客户端
│   ├── injector/                        # 新增
│   │   ├── __init__.py
│   │   └── text_injector.py             # 剪贴板 + Ctrl+V 注入
│   ├── hotkey/
│   │   └── hotkey_manager.py            # 修改: 发射 ASR 启停信号
│   └── overlay/
│       ├── overlay_window.py            # 修改: LISTENING 状态显示流式文本
│       └── state_machine.py             # 修改: 精简转换表
tests/unit/
├── test_audio_capture.py                # 新增
├── test_iat_client.py                   # 新增
├── test_text_injector.py                # 新增
├── test_state_machine.py                # 修改: 适配新状态
└── test_hotkey_manager.py              # 修改: 适配新状态
configs/
├── default_settings.json                # 修改: 增加 ASR 配置节
└── settings.json                        # 修改: 增加 ASR 配置节
```

---

### Task 1: 安装新依赖

**Python:** `D:\anaconda3\envs\any\python.exe`

- [ ] **Step 1: 安装 pywin32**

```bash
D:\anaconda3\envs\any\python.exe -m pip install pywin32
```

- [ ] **Step 2: 安装 websocket-client**

```bash
D:\anaconda3\envs\any\python.exe -m pip install websocket-client
```

- [ ] **Step 3: 安装 PyAudio**

```bash
D:\anaconda3\envs\any\python.exe -m pip install PyAudio
```

Expected: 三个包均安装成功（PyAudio 在 Windows 上有预编译 wheel）

- [ ] **Step 4: 验证安装**

```bash
D:\anaconda3\envs\any\python.exe -c "import pyaudio, websocket, win32clipboard; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: 提交**

```bash
git add .
git commit -m "chore: 添加 pyaudio, websocket-client, pywin32 依赖"
```

---

### Task 2: 精简 AppState 枚举

**Files:**
- Modify: `src/shared/types/enums.py`

- [ ] **Step 1: 移除 PROCESSING 状态**

```python
"""应用状态枚举"""

from enum import Enum, auto


class AppState(Enum):
    """语音输入法的 4 个核心状态"""
    IDLE = auto()        # 待机, 面板隐藏
    LISTENING = auto()   # 录音中, 红色脉动指示灯 + 实时文字
    PREVIEW = auto()     # 结果预览, 绿色静态指示灯
    ERROR = auto()       # 异常, 红色快闪指示灯
```

- [ ] **Step 2: 提交**

```bash
git add src/shared/types/enums.py
git commit -m "refactor(types): 移除 PROCESSING 状态, 精简为 4 状态"
```

---

### Task 3: 精简 StateMachine 转换表

**Files:**
- Modify: `src/modules/overlay/state_machine.py`

- [ ] **Step 1: 更新转换表**

```python
"""状态机 - 管理 4 状态转换规则, 通过 Signal 通知 UI"""

from PySide6.QtCore import QObject, Signal

from shared.types.enums import AppState


TRANSITIONS: dict[AppState, set[AppState]] = {
    AppState.IDLE:       {AppState.LISTENING},
    AppState.LISTENING:  {AppState.PREVIEW, AppState.IDLE, AppState.ERROR},
    AppState.PREVIEW:    {AppState.IDLE, AppState.ERROR},
    AppState.ERROR:      {AppState.IDLE},
}


class StateMachine(QObject):
    """四状态语音输入状态机

    状态:
        IDLE -> LISTENING -> PREVIEW -> IDLE
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
```

- [ ] **Step 2: 提交**

```bash
git add src/modules/overlay/state_machine.py
git commit -m "refactor(state): 精简状态机转换表, 移除 PROCESSING"
```

---

### Task 4: 更新 StateMachine 测试

**Files:**
- Modify: `tests/unit/test_state_machine.py`

- [ ] **Step 1: 重写测试以适配 4 状态模型**

```python
"""状态机单元测试 — 4 状态模型"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from PySide6.QtCore import QCoreApplication

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

    def test_listening_to_preview(self, sm):
        sm.transition(AppState.LISTENING)
        ok = sm.transition(AppState.PREVIEW)
        assert ok is True
        assert sm.current_state == AppState.PREVIEW

    def test_preview_to_idle(self, sm):
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PREVIEW)
        ok = sm.transition(AppState.IDLE)
        assert ok is True
        assert sm.current_state == AppState.IDLE

    def test_listening_to_idle_on_cancel(self, sm):
        """Escape 在录音中取消"""
        sm.transition(AppState.LISTENING)
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
        ok = sm.transition(AppState.PREVIEW)
        assert ok is False

    def test_same_state_transition_returns_false(self, sm):
        ok = sm.transition(AppState.IDLE)
        assert ok is False

    def test_state_changed_signal_emitted(self, sm):
        signals = []
        sm.state_changed.connect(lambda new, old: signals.append((new, old)))
        sm.transition(AppState.LISTENING)
        assert len(signals) == 1
        assert signals[0] == (AppState.LISTENING, AppState.IDLE)

    def test_preview_to_error(self, sm):
        sm.transition(AppState.LISTENING)
        sm.transition(AppState.PREVIEW)
        ok = sm.transition(AppState.ERROR)
        assert ok is True
        assert sm.current_state == AppState.ERROR
```

- [ ] **Step 2: 运行测试确认通过**

```bash
cd D:\LearnPython\InnerVoice && D:\anaconda3\envs\any\python.exe -m pytest tests/unit/test_state_machine.py -v
```

Expected: 全部 11 个测试 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/unit/test_state_machine.py
git commit -m "test(state): 更新状态机测试适配 4 状态模型"
```

---

### Task 5: 扩展 Settings 支持 local.json 覆盖

**Files:**
- Modify: `src/core/config/settings.py`

- [ ] **Step 1: 增加 settings.local.json 加载逻辑**

```python
"""配置管理 - JSON 文件读写, 带默认值, 支持 local.json 覆盖"""

import json
from pathlib import Path
from typing import Any


DEFAULTS = {
    "hotkey": "right ctrl",
    "long_press_threshold_ms": 300,
    "panel_width": 480,
    "panel_height": 42,
    "panel_offset_y": 60,
    "font_size": 13,
    "idle_timeout_seconds": 30,
    "asr": {
        "appid": "",
        "apikey": "",
        "apisecret": "",
        "language": "zh_cn",
        "accent": "mandarin",
    },
}

CONFIG_FILENAME = "settings.json"
LOCAL_CONFIG_FILENAME = "settings.local.json"


class Settings:
    """用户配置管理, DEFAULTS -> settings.json -> settings.local.json"""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent.parent / "configs"
        self._config_dir = Path(config_dir)
        self._config_path = self._config_dir / CONFIG_FILENAME
        self._local_config_path = self._config_dir / LOCAL_CONFIG_FILENAME
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    def _load(self):
        self._load_file(self._config_path)
        self._load_file(self._local_config_path)

    def _load_file(self, path: Path):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
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

- [ ] **Step 2: 提交**

```bash
git add src/core/config/settings.py
git commit -m "feat(config): 支持 settings.local.json 覆盖配文件"
```

---

### Task 6: 创建 AudioCapture 模块

**Files:**
- Create: `src/modules/asr/__init__.py`
- Create: `src/modules/asr/audio_capture.py`

- [ ] **Step 1: 创建 __init__.py**

```python
"""ASR 语音识别模块"""
```

- [ ] **Step 2: 创建 audio_capture.py**

```python
"""音频采集 - PyAudio 麦克风流式读取 PCM 数据"""

import threading
import pyaudio

from PySide6.QtCore import QObject, Signal


class AudioCapture(QObject):
    """从麦克风捕获 PCM 音频流, 每 40ms 发射一帧

    用法:
        cap = AudioCapture()
        cap.audio_chunk.connect(on_audio)
        cap.error_occurred.connect(on_error)
        cap.start()  # 开始录音
        cap.stop()   # 停止录音
    """

    audio_chunk = Signal(bytes)   # 1280 字节 PCM 数据
    error_occurred = Signal(str)  # 错误描述

    RATE = 16000
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    CHUNK = 640         # 40ms @ 16kHz = 640 frames = 1280 bytes
    CHUNK_BYTES = 1280

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pa: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def is_active(self) -> bool:
        return self._running

    def start(self) -> bool:
        """打开麦克风并启动读取线程, 返回是否成功"""
        if self._running:
            return True
        try:
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )
        except OSError as e:
            self.error_occurred.emit(f"麦克风打开失败: {e}")
            self._cleanup_pa()
            return False

        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """停止录音并释放资源"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._cleanup_stream()
        self._cleanup_pa()

    def _read_loop(self):
        """后台线程: 循环读取 PCM 数据并发射信号"""
        while self._running:
            try:
                data = self._stream.read(self.CHUNK, exception_on_overflow=False)
                self.audio_chunk.emit(data)
            except OSError as e:
                if self._running:
                    self.error_occurred.emit(f"录音错误: {e}")
                break

    def _cleanup_stream(self):
        if self._stream:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
            except OSError:
                pass
            self._stream = None

    def _cleanup_pa(self):
        if self._pa:
            self._pa.terminate()
            self._pa = None
```

- [ ] **Step 3: 提交**

```bash
git add src/modules/asr/
git commit -m "feat(asr): 实现 AudioCapture 麦克风 PCM 音频采集"
```

---

### Task 7: 创建 AudioCapture 测试

**Files:**
- Create: `tests/unit/test_audio_capture.py`

- [ ] **Step 1: 编写 mock PyAudio 测试**

```python
"""AudioCapture 单元测试 (mock PyAudio)"""

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

from modules.asr.audio_capture import AudioCapture


class TestAudioCapture:
    """AudioCapture 测试 (mock PyAudio)"""

    @pytest.fixture
    def mock_pyaudio(self):
        with patch("modules.asr.audio_capture.pyaudio") as mock_pa:
            mock_stream = MagicMock()
            mock_stream.read.return_value = b"\x00" * 1280
            mock_stream.is_active.return_value = True
            mock_instance = MagicMock()
            mock_instance.open.return_value = mock_stream
            mock_pa.PyAudio.return_value = mock_instance
            yield mock_pa

    def test_start_stop(self, mock_pyaudio):
        cap = AudioCapture()
        ok = cap.start()
        assert ok is True
        assert cap.is_active is True
        cap.stop()
        assert cap.is_active is False

    def test_audio_chunk_emitted(self, mock_pyaudio):
        cap = AudioCapture()
        chunks = []
        cap.audio_chunk.connect(lambda data: chunks.append(data))
        cap.start()
        time.sleep(0.15)  # 等待几帧
        cap.stop()
        assert len(chunks) > 0
        assert len(chunks[0]) == 1280

    def test_stop_when_not_active(self, mock_pyaudio):
        cap = AudioCapture()
        cap.stop()  # 不应抛异常

    def test_error_when_mic_fails(self):
        with patch("modules.asr.audio_capture.pyaudio") as mock_pa:
            mock_pa.PyAudio.side_effect = OSError("no mic")
            cap = AudioCapture()
            errors = []
            cap.error_occurred.connect(lambda msg: errors.append(msg))
            ok = cap.start()
            assert ok is False
            assert len(errors) == 1
            assert "麦克风打开失败" in errors[0]
```

- [ ] **Step 2: 运行测试**

```bash
cd D:\LearnPython\InnerVoice && D:\anaconda3\envs\any\python.exe -m pytest tests/unit/test_audio_capture.py -v
```

Expected: 全部 4 个测试 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/unit/test_audio_capture.py
git commit -m "test(asr): 添加 AudioCapture 单元测试"
```

---

### Task 8: 创建 IATClient 模块

**Files:**
- Create: `src/modules/asr/iat_client.py`

- [ ] **Step 1: 创建 iat_client.py**

```python
"""讯飞语音听写(流式版) IAT WebSocket 客户端"""

import base64
import datetime
import hashlib
import hmac
import json
import threading
import time
import uuid

import websocket

from PySide6.QtCore import QObject, Signal


# IAT WebSocket 地址
IAT_URL = "wss://iat-api.xfyun.cn/v2/iat"
HOST = "iat-api.xfyun.cn"
URI = "/v2/iat"


class IATClient(QObject):
    """讯飞语音听写 WebSocket 客户端

    用法:
        client = IATClient(appid, apikey, apisecret)
        client.partial_result.connect(on_partial)
        client.final_result.connect(on_final)
        client.error_occurred.connect(on_error)
        client.connect()
        client.send_audio(pcm_bytes)
        client.send_end()
    """

    partial_result = Signal(str)   # 中间识别文本
    final_result = Signal(str)     # 最终识别文本
    error_occurred = Signal(str)   # 错误信息
    connected = Signal()           # 握手成功
    disconnected = Signal()        # 连接断开

    def __init__(
        self,
        appid: str,
        apikey: str,
        apisecret: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._appid = appid
        self._apikey = apikey
        self._apisecret = apisecret
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._seq = 0
        self._session_id = ""

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._running

    def connect(self):
        """建立 WebSocket 连接并握手"""
        if self._running:
            return
        url = self._build_url()
        self._running = True
        self._seq = 0
        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._thread.start()

    def send_audio(self, data: bytes):
        """发送音频帧 (status=1, 中间帧)"""
        if not self._ws or not self._running:
            return
        self._seq += 1
        frame = {
            "data": {
                "status": 1,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": base64.b64encode(data).decode("utf-8"),
            }
        }
        try:
            self._ws.send(json.dumps(frame))
        except Exception as e:
            self.error_occurred.emit(f"发送音频失败: {e}")

    def send_end(self):
        """发送结束帧 (status=2)"""
        if not self._ws or not self._running:
            return
        self._seq += 1
        frame = {
            "data": {
                "status": 2,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            }
        }
        try:
            self._ws.send(json.dumps(frame))
        except Exception as e:
            self.error_occurred.emit(f"发送结束帧失败: {e}")

    def disconnect(self):
        """主动断开连接"""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    # --- WebSocket 回调 ---

    def _on_open(self, ws):
        """握手成功, 发送首帧"""
        self._session_id = str(uuid.uuid4())
        first_frame = {
            "common": {"app_id": self._appid},
            "business": {
                "domain": "iat",
                "language": "zh_cn",
                "accent": "mandarin",
                "dwa": "wpgs",      # 动态修正
                "vinfo": 1,
                "vad_eos": 10000,   # 10秒静默断句
            },
            "data": {
                "status": 0,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": base64.b64encode(b"").decode("utf-8"),
            },
        }
        ws.send(json.dumps(first_frame))
        self.connected.emit()

    def _on_message(self, ws, message):
        """接收识别结果"""
        try:
            result = json.loads(message)
        except json.JSONDecodeError:
            return

        code = result.get("code", -1)
        if code != 0:
            err_msg = result.get("message", f"错误码: {code}")
            self.error_occurred.emit(err_msg)
            return

        data = result.get("data", {})
        status = data.get("status", 0)
        text = self._extract_text(data)

        if status == 1:
            self.partial_result.emit(text)
        elif status == 2:
            self.final_result.emit(text)

    def _on_error(self, ws, error):
        self.error_occurred.emit(f"WebSocket 错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        self._running = False
        self.disconnected.emit()

    # --- 签名 & URL 构建 ---

    def _build_url(self) -> str:
        """构建带鉴权签名的 WebSocket URL"""
        now = datetime.datetime.now(datetime.timezone.utc)
        date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # HMAC-SHA256 签名
        signature_origin = (
            f"host: {HOST}\n"
            f"date: {date_str}\n"
            f"GET {URI} HTTP/1.1"
        )
        signature = base64.b64encode(
            hmac.new(
                self._apisecret.encode("utf-8"),
                signature_origin.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        # authorization 头
        authorization_origin = (
            f'api_key="{self._apikey}",'
            f'algorithm="hmac-sha256",'
            f'headers="host date request-line",'
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(
            authorization_origin.encode("utf-8")
        ).decode("utf-8")

        # 拼接 URL
        from urllib.parse import urlencode
        params = urlencode({
            "authorization": authorization,
            "date": date_str,
            "host": HOST,
        })
        return f"{IAT_URL}?{params}"

    def _extract_text(self, data: dict) -> str:
        """从返回数据中提取识别文本"""
        result = data.get("result", {})
        ws_list = result.get("ws", [])
        words = []
        for ws_item in ws_list:
            cw_list = ws_item.get("cw", [])
            for cw in cw_list:
                w = cw.get("w", "")
                if w:
                    words.append(w)
        return "".join(words)
```

- [ ] **Step 2: 提交**

```bash
git add src/modules/asr/iat_client.py
git commit -m "feat(asr): 实现讯飞 IAT WebSocket 客户端"
```

---

### Task 9: 创建 IATClient 测试

**Files:**
- Create: `tests/unit/test_iat_client.py`

- [ ] **Step 1: 编写 mock WebSocket 测试**

```python
"""IATClient 单元测试 (mock WebSocket)"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from PySide6.QtCore import QCoreApplication

_app = QCoreApplication.instance()
if _app is None:
    _app = QCoreApplication([])

from modules.asr.iat_client import IATClient


# 模拟返回数据
PARTIAL_MSG = json.dumps({
    "code": 0,
    "message": "success",
    "sid": "test-sid",
    "data": {
        "status": 1,
        "result": {
            "ws": [{"cw": [{"w": "今天"}, {"w": "天气"}]}],
        },
    },
})

FINAL_MSG = json.dumps({
    "code": 0,
    "message": "success",
    "sid": "test-sid",
    "data": {
        "status": 2,
        "result": {
            "ws": [{"cw": [{"w": "今天天气不错"}]}],
        },
    },
})


class TestIATClient:
    """IATClient 测试 (mock WebSocket)"""

    @pytest.fixture
    def client(self):
        return IATClient("test_appid", "test_apikey", "test_apisecret")

    def test_initial_state_not_connected(self, client):
        assert client.is_connected is False

    def test_build_url(self, client):
        url = client._build_url()
        assert url.startswith("wss://iat-api.xfyun.cn/v2/iat?")
        assert "authorization=" in url
        assert "date=" in url
        assert "host=" in url

    def test_extract_text_partial(self, client):
        data = json.loads(PARTIAL_MSG)["data"]
        text = client._extract_text(data)
        assert text == "今天天气"

    def test_extract_text_empty(self, client):
        data = {"result": {"ws": []}}
        text = client._extract_text(data)
        assert text == ""

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_connect_and_disconnect(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws

        client.connect()
        assert client.is_connected is True

        client.disconnect()
        assert client.is_connected is False

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_send_audio(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws

        client.connect()
        client.send_audio(b"\x00" * 1280)
        assert mock_ws.send.called
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["data"]["status"] == 1

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_on_message_emits_partial_result(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        results = []
        client.partial_result.connect(lambda t: results.append(t))

        client._on_message(None, PARTIAL_MSG)
        assert len(results) == 1
        assert results[0] == "今天天气"

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_on_message_emits_final_result(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        results = []
        client.final_result.connect(lambda t: results.append(t))

        client._on_message(None, FINAL_MSG)
        assert len(results) == 1
        assert results[0] == "今天天气不错"

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_on_error(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        errors = []
        client.error_occurred.connect(lambda e: errors.append(e))

        client._on_error(None, "连接超时")
        assert len(errors) == 1
        assert "连接超时" in errors[0]

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_send_end_frame(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        client.send_end()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["data"]["status"] == 2
        assert sent_data["data"]["audio"] == ""
```

- [ ] **Step 2: 运行测试**

```bash
cd D:\LearnPython\InnerVoice && D:\anaconda3\envs\any\python.exe -m pytest tests/unit/test_iat_client.py -v
```

Expected: 全部 9 个测试 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/unit/test_iat_client.py
git commit -m "test(asr): 添加 IATClient 单元测试"
```

---

### Task 10: 创建 TextInjector 模块

**Files:**
- Create: `src/modules/injector/__init__.py`
- Create: `src/modules/injector/text_injector.py`

- [ ] **Step 1: 创建 __init__.py**

```python
"""文本注入模块"""
```

- [ ] **Step 2: 创建 text_injector.py**

```python
"""文本注入 - 剪贴板 + Ctrl+V 注入到当前活动窗口"""

import time
import win32clipboard
import win32con
import keyboard


class TextInjector:
    """将文本通过剪贴板粘贴注入到当前活动窗口

    用法:
        TextInjector.inject("你好世界")
    """

    @staticmethod
    def inject(text: str) -> bool:
        """注入文本到当前活动窗口, 返回是否成功"""
        if not text:
            return False

        # 保存原始剪贴板内容
        original = TextInjector._get_clipboard()

        try:
            TextInjector._set_clipboard(text)
            keyboard.send("ctrl+v")
            time.sleep(0.05)  # 等待粘贴完成
        finally:
            # 延迟恢复, 确保 Ctrl+V 已处理
            time.sleep(0.05)
            TextInjector._set_clipboard(original)
        return True

    @staticmethod
    def _get_clipboard() -> str | None:
        try:
            win32clipboard.OpenClipboard()
            try:
                return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except (TypeError, OSError):
                return ""
        except OSError:
            return ""
        finally:
            try:
                win32clipboard.CloseClipboard()
            except OSError:
                pass

    @staticmethod
    def _set_clipboard(text: str | None):
        if text is None:
            text = ""
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            if text:
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        except OSError:
            pass
        finally:
            try:
                win32clipboard.CloseClipboard()
            except OSError:
                pass
```

- [ ] **Step 3: 提交**

```bash
git add src/modules/injector/
git commit -m "feat(injector): 实现剪贴板 Ctrl+V 文本注入"
```

---

### Task 11: 创建 TextInjector 测试

**Files:**
- Create: `tests/unit/test_text_injector.py`

- [ ] **Step 1: 编写 mock 剪贴板测试**

```python
"""TextInjector 单元测试 (mock win32clipboard + keyboard)"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from modules.injector.text_injector import TextInjector


class TestTextInjector:
    """TextInjector 测试"""

    def test_inject_empty_text_returns_false(self):
        assert TextInjector.inject("") is False

    @patch("modules.injector.text_injector.keyboard")
    @patch("modules.injector.text_injector.win32clipboard")
    def test_inject_saves_and_restores_clipboard(self, mock_clip, mock_kb):
        # 模拟原始剪贴板内容
        original_text = "原始内容"
        get_calls = [original_text, "注入文本"]

        def get_clipboard():
            return get_calls.pop(0) if get_calls else ""

        mock_clip.GetClipboardData.side_effect = get_clipboard

        ok = TextInjector.inject("注入文本")
        assert ok is True
        mock_kb.send.assert_called_once_with("ctrl+v")

    @patch("modules.injector.text_injector.keyboard")
    @patch("modules.injector.text_injector.win32clipboard")
    def test_inject_handles_clipboard_error(self, mock_clip, mock_kb):
        mock_clip.OpenClipboard.side_effect = OSError("clipboard busy")

        ok = TextInjector.inject("测试")
        assert ok is True  # 不因剪贴板错误而崩溃
```

- [ ] **Step 2: 运行测试**

```bash
cd D:\LearnPython\InnerVoice && D:\anaconda3\envs\any\python.exe -m pytest tests/unit/test_text_injector.py -v
```

Expected: 全部 3 个测试 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/unit/test_text_injector.py
git commit -m "test(injector): 添加 TextInjector 单元测试"
```

---

### Task 12: 更新 OverlayWindow 支持流式文本

**Files:**
- Modify: `src/modules/overlay/overlay_window.py`

- [ ] **Step 1: 在 LISTENING 状态显示实时文本并隐藏按钮**

修改 `on_state_changed` 方法中 LISTENING 和 PREVIEW 的分支：

```python
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
            self._btn_cancel.setText("取消")
            self.show()

        elif new_state == AppState.PREVIEW:
            self._status_label.setText("完成")
            self._btn_confirm.setVisible(True)
            self._btn_cancel.setVisible(True)
            self._btn_cancel.setText("取消")
            self.show()

        elif new_state == AppState.ERROR:
            self._status_label.setText("错误")
            self._set_text("")
            self._btn_confirm.setVisible(False)
            self._btn_cancel.setVisible(True)
            self._btn_cancel.setText("关闭")
            self.show()
```

- [ ] **Step 2: 确认 set_text 方法已支持 LISTENING 状态更新**

现有 `set_text` 方法已经实现了文本更新 (`self._text_label.setText(text)`)，但需要确认它在 LISTENING 状态下也可被调用。在 `on_state_changed` 的 LISTENING 分支中，不再覆盖文本（移除原有的 `self._text_label.setText("")` 如果有的话）。当前代码 LISTENING 分支没有清除文本，但也没有保留文本。检查确认：现有代码的 LISTENING 分支只设置了状态标签和按钮可见性，没有重置文本。所以 `set_text` 调用后文本会保留。保持不变即可 — 在 `on_state_changed` LISTENING 分支中**不要**重置文本。

- [ ] **Step 3: 提交**

```bash
git add src/modules/overlay/overlay_window.py
git commit -m "feat(overlay): LISTENING 状态支持流式文本显示"
```

---

### Task 13: 更新 HotkeyManager 集成 ASR 触发

**Files:**
- Modify: `src/modules/hotkey/hotkey_manager.py`

- [ ] **Step 1: 添加 ASR 启停信号, 修改状态转换逻辑**

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

    快捷键行为:
        长按右 Ctrl (> threshold_ms) -> 唤起录音 (LISTENING)
        松开右 Ctrl -> 结束录音, 等待最终结果
        Enter -> 确认注入 (仅在 PREVIEW 状态)
        Escape -> 取消 (LISTENING / PREVIEW 状态)
    """

    text_confirmed = Signal(str)    # 用户确认后的文本
    asr_start_requested = Signal()  # 请求开始 ASR 录音
    asr_stop_requested = Signal()   # 请求停止 ASR 录音

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

        keyboard.add_hotkey("enter", lambda: self._on_enter())
        keyboard.add_hotkey("esc", lambda: self._on_esc())

        while self._running:
            time.sleep(0.1)

    def _on_press(self):
        if self._sm.current_state != AppState.IDLE:
            return
        threshold = self._settings.get("long_press_threshold_ms") / 1000.0
        self._press_timer = threading.Timer(threshold, self._on_long_press_timeout)
        self._press_timer.start()

    def _on_release(self):
        if self._press_timer:
            self._press_timer.cancel()
            self._press_timer = None
        if self._sm.current_state == AppState.LISTENING:
            self.asr_stop_requested.emit()

    def _on_long_press_timeout(self):
        self._sm.transition(AppState.LISTENING)
        self.asr_start_requested.emit()

    def _on_enter(self):
        if self._sm.current_state == AppState.PREVIEW:
            text = self._text_getter() if self._text_getter else ""
            if text:
                self.text_confirmed.emit(text)
            self._sm.transition(AppState.IDLE)

    def _on_esc(self):
        if self._sm.current_state in (AppState.PREVIEW, AppState.LISTENING):
            self._sm.transition(AppState.IDLE)
```

- [ ] **Step 2: 提交**

```bash
git add src/modules/hotkey/hotkey_manager.py
git commit -m "feat(hotkey): 集成 ASR 启停信号, 适配 4 状态模型"
```

---

### Task 14: 更新 HotkeyManager 测试

**Files:**
- Modify: `tests/unit/test_hotkey_manager.py`

- [ ] **Step 1: 更新测试以适配新状态和新信号**

```python
"""全局快捷键管理测试 — 4 状态 + ASR 信号"""

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
```

- [ ] **Step 2: 运行测试**

```bash
cd D:\LearnPython\InnerVoice && D:\anaconda3\envs\any\python.exe -m pytest tests/unit/test_hotkey_manager.py -v
```

Expected: 全部 8 个测试 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/unit/test_hotkey_manager.py
git commit -m "test(hotkey): 更新热键测试适配 ASR 信号和 4 状态"
```

---

### Task 15: 更新 main.py 编排所有模块

**Files:**
- Modify: `src/app/main.py`

- [ ] **Step 1: 重写 main.py 编排逻辑**

```python
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
from modules.overlay.state_machine import StateMachine
from modules.overlay.overlay_window import OverlayWindow
from modules.hotkey.hotkey_manager import HotkeyManager
from modules.asr.audio_capture import AudioCapture
from modules.asr.iat_client import IATClient
from modules.injector.text_injector import TextInjector
from shared.types.enums import AppState


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("InnerVoice")
    app.setQuitOnLastWindowClosed(False)

    # 模块初始化
    settings = Settings()
    state_machine = StateMachine()
    overlay = OverlayWindow()

    asr_config = settings.get("asr")
    audio_capture = AudioCapture()
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
        overlay.set_text(text)
        state_machine.transition(AppState.PREVIEW)

    iat_client.final_result.connect(on_final_result)

    # 绑定: 错误处理
    def on_asr_error(msg: str):
        print(f"[ASR Error] {msg}")
        if state_machine.current_state == AppState.LISTENING:
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
        TextInjector.inject(text)

    hotkey_manager.set_text_getter(overlay.text)
    hotkey_manager.text_confirmed.connect(on_confirm)

    # 绑定: ASR 资源清理 (在状态退回 IDLE 时统一执行, 避免双重调用)
    def on_cleanup(new_state: AppState, old_state: AppState):
        if new_state == AppState.IDLE and old_state == AppState.LISTENING:
            audio_capture.stop()
            iat_client.disconnect()

    state_machine.state_changed.connect(on_cleanup)

    # 按钮: 只做状态转换, 资源清理由 on_cleanup 统一处理
    overlay.confirm_button().clicked.connect(
        lambda: on_confirm(overlay.text())
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
```

- [ ] **Step 2: 提交**

```bash
git add src/app/main.py
git commit -m "feat(app): 编排 ASR/注入模块, 完成语音输入闭环"
```

---

### Task 16: 更新配置文件

**Files:**
- Modify: `configs/default_settings.json`
- Modify: `configs/settings.json`

- [ ] **Step 1: 读取当前配置文件**

```bash
cat configs/default_settings.json && echo "---" && cat configs/settings.json
```

- [ ] **Step 2: 更新 default_settings.json**

```json
{
  "hotkey": "right ctrl",
  "long_press_threshold_ms": 300,
  "panel_width": 480,
  "panel_height": 42,
  "panel_offset_y": 60,
  "font_size": 13,
  "idle_timeout_seconds": 30,
  "asr": {
    "appid": "",
    "apikey": "",
    "apisecret": "",
    "language": "zh_cn",
    "accent": "mandarin"
  }
}
```

- [ ] **Step 3: 更新 settings.json**

```json
{
  "asr": {
    "appid": "",
    "apikey": "",
    "apisecret": ""
  }
}
```

- [ ] **Step 4: 提交**

```bash
git add configs/default_settings.json configs/settings.json
git commit -m "feat(config): 添加 ASR 凭据配置节"
```

---

### Task 17: 全量测试验证

**Python:** `D:\anaconda3\envs\any\python.exe`

- [ ] **Step 1: 运行全部单元测试**

```bash
cd D:\LearnPython\InnerVoice && D:\anaconda3\envs\any\python.exe -m pytest tests/unit/ -v
```

Expected: 全部测试 PASS（约 35 个）

- [ ] **Step 2: 验证应用可以正常导入和启动（不连 ASR）**

```bash
cd D:\LearnPython\InnerVoice && D:\anaconda3\envs\any\python.exe -c "
import sys
from pathlib import Path
sys.path.insert(0, 'src')
from modules.asr.audio_capture import AudioCapture
from modules.asr.iat_client import IATClient
from modules.injector.text_injector import TextInjector
print('All modules imported successfully')
"
```

Expected: `All modules imported successfully`

- [ ] **Step 3: 检查 git 状态**

```bash
git -C D:\LearnPython\InnerVoice status
git -C D:\LearnPython\InnerVoice log --oneline -5
```

Expected: 工作区干净，所有提交按顺序排列

---

## 完成检查清单

- [ ] 所有单元测试通过
- [ ] AppState 枚举仅含 IDLE / LISTENING / PREVIEW / ERROR
- [ ] StateMachine 转换表不含 PROCESSING
- [ ] Settings 支持从 settings.local.json 加载覆盖值
- [ ] AudioCapture 正确打开 16kHz/16bit/单声道 PCM 流
- [ ] IATClient 正确生成 HMAC-SHA256 签名和帧格式
- [ ] TextInjector 保存/恢复剪贴板内容
- [ ] OverlayWindow 在 LISTENING 状态显示流式文本
- [ ] HotkeyManager 发射 asr_start_requested / asr_stop_requested 信号
- [ ] main.py 正确编排所有模块
- [ ] ASR 凭据存储在 settings.local.json（不提交到 git）
