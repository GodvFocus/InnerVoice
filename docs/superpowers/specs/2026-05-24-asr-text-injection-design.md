# 实时语音转写 & 文本注入 — 设计文档

**日期:** 2026-05-24
**版本:** v1.0
**状态:** 已确认

---

## 1. 概述

在 InnerVoice 现有框架基础上，接入讯飞语音听写（流式版）IAT API 实现实时语音转写，并实现剪贴板粘贴方式的文本注入，完成"说话 → 实时转写 → 预览确认 → 注入目标窗口"完整闭环。

## 2. 技术选型

| 组件 | 选型 | 原因 |
|------|------|------|
| ASR 服务 | 讯飞语音听写（流式版）IAT WebSocket API | 实时流式识别，边说边出字，HMAC-SHA256 鉴权 |
| 音频采集 | PyAudio | 成熟稳定，PCM 16k/16bit 格式天然匹配 |
| 文本注入 | 剪贴板 + Ctrl+V | 速度快，支持长文本，注入后恢复原始剪贴板 |
| 编程语言 | Python 3.10 | 与现有项目一致 |
| Conda 环境 | `any` (D:\anaconda3\envs\any) | 用户指定 |

## 3. 讯飞 IAT API 接口要点

- **地址:** `wss://iat-api.xfyun.cn/v2/iat`
- **鉴权:** HMAC-SHA256 签名，基于 RFC1123 日期 + APIKey/APISecret
- **音频格式:** PCM，采样率 16kHz，位长 16bit，单声道
- **发送方式:** 每 40ms 发送 1280 字节音频数据
- **帧类型:** status=0（首帧，携带业务参数）、status=1（中间音频帧）、status=2（结束帧）
- **返回:** `data.status=1` 中间结果，`data.status=2` 最终结果
- **文字提取路径:** `data.result.ws[].cw[].w` 拼接
- **最大时长:** 单次 60 秒

## 4. 架构设计

### 4.1 模块总览

```
src/
├── app/main.py                  # 编排层（修改）
├── core/config/settings.py      # 配置 + ASR 凭据（修改）
├── shared/types/enums.py        # AppState 枚举（修改）
├── modules/
│   ├── overlay/
│   │   ├── overlay_window.py    # 悬浮窗（修改：支持流式文本更新）
│   │   ├── state_machine.py     # 状态机（修改：精简状态）
│   │   └── status_indicator.py  # 指示灯（不变）
│   ├── hotkey/
│   │   └── hotkey_manager.py    # 热键管理（修改：集成 ASR 启停）
│   ├── asr/                     # [新增] 语音识别模块
│   │   ├── __init__.py
│   │   ├── audio_capture.py     # PyAudio 麦克风录音
│   │   └── iat_client.py        # 讯飞 IAT WebSocket 客户端
│   └── injector/                # [新增] 文本注入模块
│       ├── __init__.py
│       └── text_injector.py     # 剪贴板 + Ctrl+V 注入
```

### 4.2 AudioCapture — 音频采集

**职责:** 从麦克风捕获 PCM 音频流，每 40ms 输出一帧

```
class AudioCapture(QObject):
    audio_chunk = Signal(bytes)  # 1280 字节 PCM 数据
    error_occurred = Signal(str)

    def start() -> bool   # 打开麦克风流，开始读取
    def stop()            # 停止并关闭流
    def is_active -> bool
```

- 使用 PyAudio 阻塞式 `read()`，在独立线程中循环读取
- 音频参数硬编码：16kHz / 16bit / 单声道 / frames_per_buffer=640（40ms）
- 错误时发射 `error_occurred` 信号，由上层决定状态转换

### 4.3 IATClient — 讯飞 WebSocket 客户端

**职责:** 建立 WebSocket 连接，发送音频帧，接收识别结果

```
class IATClient(QObject):
    partial_result = Signal(str)  # 中间识别文本
    final_result = Signal(str)    # 最终识别文本
    error_occurred = Signal(str)  # 错误信息
    connected = Signal()          # 握手成功
    disconnected = Signal()       # 连接断开

    def __init__(appid, apikey, apisecret)
    def connect()                 # 建立 WebSocket 连接 + 握手
    def send_audio(bytes)         # 发送音频帧（status=1）
    def send_end()                # 发送结束帧（status=2）
    def disconnect()              # 主动断开
    def is_connected -> bool
```

**签名生成规则:**
1. 生成 RFC1123 格式 UTC 时间（date）
2. 拼接签名原文: `host: iat-api.xfyun.cn\ndate: {date}\nGET /v2/iat HTTP/1.1`
3. 用 APISecret 对原文做 HMAC-SHA256 → Base64
4. 构造 authorization 头

**结果解析:**
- 收到 JSON → 检查 `code`，非 0 为错误
- `data.status == 1`: 中间结果，提取 `ws[].cw[].w` 拼接，发射 `partial_result`
- `data.status == 2`: 最终结果，提取拼接，发射 `final_result`

### 4.4 TextInjector — 文本注入

**职责:** 将文本写入当前活动窗口的光标位置

```
class TextInjector:
    def inject(text: str) -> bool  # 同步方法，注入文本到活动窗口
```

**实现流程:**
1. `win32clipboard.OpenClipboard()` 读取并保存原始内容
2. `win32clipboard.SetClipboardData(CF_UNICODETEXT, text)` 写入目标文本
3. `keyboard.send("ctrl+v")` 粘贴
4. 短暂等待（0.05s）确保粘贴完成
5. 恢复原始剪贴板内容
6. 异常时尽力恢复剪贴板

### 4.5 状态机精简

去掉 `PROCESSING` 状态：

```
IDLE ←→ LISTENING → PREVIEW → IDLE
 ↑                      ↓
 └──── ERROR ←──────────┘
```

| 状态 | 悬浮窗表现 |
|------|-----------|
| IDLE | 面板隐藏，等待热键 |
| LISTENING | 红色脉动灯 + "录音中" + **实时文字跳动更新** + 无按钮 |
| PREVIEW | 绿色灯 + "完成" + 最终文本 + 确认/取消按钮 |
| ERROR | 红色快闪 + 错误信息 + 关闭按钮 |

### 4.6 配置扩展

`configs/settings.json` 增加 ASR 配置：

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
    "apisecret": ""
  }
}
```

凭据存储在 `configs/settings.local.json`（已加入 .gitignore），不与代码一同提交。

## 5. 数据流

```
麦克风 ──[PCM]──→ AudioCapture ──[bytes]──→ IATClient
                                              │
                                    WebSocket │ 讯飞云
                                              │
                          partial_result / final_result (Signal)
                                              │
                                     OverlayWindow.set_text()
                                              │
                              用户点击确认 / 按 Enter
                                              │
                                  TextInjector.inject()
                                              │
                                   Ctrl+V → 活动窗口
```

## 6. 线程模型

| 线程 | 运行内容 |
|------|---------|
| 主线程 | Qt 事件循环、UI 渲染、StateMachine、TextInjector |
| AudioCapture 线程 | PyAudio 阻塞读取 |
| IATClient 线程 | WebSocket 收发 |
| HotkeyManager 线程 | keyboard 库全局钩子监听 |

线程间通过 Qt Signal/Slot 通信（线程安全）。

## 7. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 麦克风打开失败 | AudioCapture 发射 error → StateMachine → ERROR → 悬浮窗显示"麦克风不可用" |
| WebSocket 连接失败 | IATClient 发射 error → StateMachine → ERROR → 悬浮窗显示"网络连接失败" |
| 识别过程出错 | IATClient 发射 error → StateMachine → ERROR → 显示错误信息，可关闭 |
| 剪贴板操作失败 | TextInjector 捕获异常，尽力恢复剪贴板，上抛异常 |
| 录音中 ESC | HotkeyManager 检测 → AudioCapture.stop() + IATClient.disconnect() → IDLE |
| 网络断开 | WebSocket on_error 回调 → IATClient 发射 error → 同上 |

## 8. 新增依赖

```
pip install pyaudio          # 麦克风音频采集
pip install websocket-client # WebSocket 通信
pip install pywin32          # Win32 API（剪贴板操作）
pip install keyboard         # 已有
```

## 9. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/modules/asr/__init__.py` | 新增 | 模块初始化 |
| `src/modules/asr/audio_capture.py` | 新增 | PyAudio 录音 |
| `src/modules/asr/iat_client.py` | 新增 | 讯飞 WebSocket 客户端 |
| `src/modules/injector/__init__.py` | 新增 | 模块初始化 |
| `src/modules/injector/text_injector.py` | 新增 | 剪贴板注入 |
| `src/shared/types/enums.py` | 修改 | 移除 PROCESSING 状态 |
| `src/modules/overlay/state_machine.py` | 修改 | 精简转换表 |
| `src/modules/overlay/overlay_window.py` | 修改 | LISTENING 状态显示流式文本 |
| `src/modules/hotkey/hotkey_manager.py` | 修改 | 集成 ASR 启停信号 |
| `src/core/config/settings.py` | 修改 | 增加 ASR 配置加载 |
| `src/app/main.py` | 修改 | 编排 ASR/注入模块 |
| `configs/settings.json` | 修改 | 增加 asr 配置节 |
| `configs/default_settings.json` | 修改 | 增加 asr 默认值 |

## 10. 测试要点

- 麦克风正常打开/关闭，设备不存在时的错误提示
- WebSocket 握手签名正确性，与讯飞服务器连通
- 音频帧发送频率准确（40ms ± 容忍度）
- 中间结果正确解析并叠加到悬浮窗
- 剪贴板保存/恢复正确（原始内容不丢失）
- Enter 确认 + ESC 取消两种路径
- 异常断开后状态可恢复（回到 IDLE）
