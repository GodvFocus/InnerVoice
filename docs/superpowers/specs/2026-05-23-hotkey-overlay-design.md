# 全局语音触发 + 基础 UI 面板 — 设计文档

**日期**: 2026-05-23  
**范围**: F1 全局语音触发、F3 基础 UI 面板 (MVP T0)  
**平台**: Windows 桌面 / Python 3.10

## 技术选型

| 决策项 | 选型 | 理由 |
|--------|------|------|
| UI 框架 | PySide6 | 悬浮窗(无边框透明窗口)支持完善, 波形动画方便 |
| 全局热键 | keyboard 库 | 支持长按检测, API 简洁 |
| ASR 服务 | 待定(下阶段) | 本设计聚焦 UI 面板与快捷键触发的框架 |
| 文本注入 | 待定(下阶段) | Preview 状态后通过信号桥接 |

## UI 设计

### 布局

- 横向底栏, 屏幕底部居中
- 紧凑排列: 指示灯 → 状态标签 → 预览文本 → 确认/取消按钮
- 无边框, 置顶(WindowStaysOnTopHint), 不抢占焦点

### 录音状态反馈

**脉动指示灯方案**(选项 A):
- IDLE → 隐藏
- LISTENING → 红色指示灯呼吸闪烁 + 文本光标闪烁
- PROCESSING → 黄色指示灯旋转
- PREVIEW → 绿色指示灯静态
- ERROR → 红色指示灯快闪 + 错误文本

### 交互快捷键

| 按键 | 作用 |
|------|------|
| 长按右 Ctrl | 唤起开始录音 |
| 松开右 Ctrl | 停止录音, 进入处理 |
| Enter | 确认注入文本 |
| Escape | 取消/丢弃文本 |

## 状态机

```
IDLE → (长按右Ctrl) → LISTENING → (松开/静音超时) → PROCESSING → (ASR结果) → PREVIEW → (确认) → IDLE
                                                                                → (取消) → IDLE
任意状态 → (异常) → ERROR → (关闭/重试) → IDLE
```

### 状态定义

| 状态 | 面板显隐 | 指示灯 | 文本区 | 按钮 |
|------|----------|--------|--------|------|
| IDLE | 隐藏 | - | - | - |
| LISTENING | 显示 | 红色脉动 | 流式实时预览 + 光标 | 无 |
| PROCESSING | 显示 | 黄色旋转 | "识别中..." | 无 |
| PREVIEW | 显示 | 绿色静态 | 完整转写文本 | 确认 + 取消 |
| ERROR | 显示 | 红色快闪 | 错误消息 | 关闭 |

## 组件架构

```
src/
├── app/
│   └── main.py                # 应用入口, QApplication 创建与模块初始化
├── modules/
│   ├── hotkey/
│   │   └── hotkey_manager.py  # keyboard 全局热键监听, 长按检测状态机
│   └── overlay/
│       ├── overlay_window.py  # PySide6 悬浮窗: 无边框、置顶、底部居中
│       ├── status_indicator.py # 脉动指示灯 (QPropertyAnimation)
│       └── state_machine.py   # 5 状态转换规则, PySide6 Signal 通信
├── core/
│   └── config/
│       └── settings.py        # JSON 配置文件读写
└── shared/
    └── types/
        └── enums.py           # AppState 枚举
```

### 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| `hotkey_manager` | 监听全局键盘事件, 检测长按右Ctrl, 触发状态变更 | keyboard |
| `overlay_window` | 悬浮窗生命周期: 创建/显示/隐藏/位置控制 | state_machine |
| `status_indicator` | QWidget 子类, 绘制脉动动画 | QPropertyAnimation |
| `state_machine` | 管理状态转换规则, 发射状态变更 Signal | enums |
| `settings` | JSON 读写, 快捷键/面板样式等可配置项 | 无 |

### 数据流

```
键盘按下 → hotkey_manager 检测长按
  → state_machine.transition(LISTENING) [Signal]
  → overlay_window.show() + status_indicator.start_pulse()
  → (预留) ASR 流式结果 → overlay_window.setText()
  → 松开右Ctrl → state_machine.transition(PROCESSING)
  → (预留) ASR 返回 → state_machine.transition(PREVIEW)
  → 确认 → (预留)文本注入 → state_machine.transition(IDLE) → overlay_window.hide()
```

## API / 接口预留

### ASR 接收入口

```python
# state_machine 或 overlay_window 对外暴露
def on_asr_partial(text: str): ...    # 流式中间结果
def on_asr_final(text: str): ...      # 最终识别结果
```

### 文本注入出口

```python
# state_machine 对外暴露
def on_text_confirmed(text: str): ...  # 用户确认后, 传递文本给注入模块
```

## 异常处理

| 场景 | 处理 |
|------|------|
| 键盘钩子注册失败 | 弹系统通知"需要管理员权限", 状态机进入 ERROR |
| 无网络 | 不做 ASR 调用, PREVIEW 阶段显示"网络异常" |
| 录音设备不可用 | 进入 ERROR 状态, 提示"麦克风不可用" |

## 测试策略

- `hotkey_manager`: 模拟 keyboard 事件, 验证长按阈值和触发逻辑
- `state_machine`: 单元测试所有合法/非法状态转换
- `overlay_window`: 人工验证悬浮窗位置/显隐/动画效果
- `status_indicator`: 单元测试脉动动画参数

## 未覆盖项(留待后续设计)

- ASR 服务接入
- 文本注入到目标窗口
- AI 润色模块
- 热词词典
