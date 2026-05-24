# 口语化→书面化 AI 润色 — 设计文档

**日期:** 2026-05-24
**版本:** v1.0
**状态:** 已确认

---

## 1. 概述

在 InnerVoice 现有语音输入闭环基础上，新增 AI 润色能力。用户在任意应用内语音输入后，系统自动将口语化转写文本润色为正式书面语，并可通过下拉框切换风格实时重新润色。同时新增桌面主窗口，提供可视化的润色风格管理界面。

核心差异化：用户从"说话 → 转写"升级为"说话 → 转写 → 自动润色 → 注入"，省去手动修改步骤。

## 2. 技术选型

| 组件 | 选型 | 原因 |
|------|------|------|
| LLM 服务 | DeepSeek (`deepseek-chat`) | 中文能力强，API 兼容 OpenAI SDK，成本低 |
| 本地存储 | SQLite (`data/polish.db`) | 零配置，适合风格数据持久化，支持可视化 CRUD |
| Python 库 | `openai` | 标准库，兼容 DeepSeek 的 OpenAI 接口 |
| 桌面框架 | PySide6 (已有) | QMainWindow + QSystemTrayIcon + QDialog |

## 3. 交互设计

### 3.1 自动润色流程

```
ASR 转写完成(final_result)
  → 状态机进入 PREVIEW
  → 自动调用润色 API（默认"正式"风格）
  → 悬浮窗显示"◐ 润色中..."，按钮禁用
  → 润色完成 → 显示润色后文本，恢复可交互
```

### 3.2 风格切换

- 悬浮窗 PREVIEW 状态增加风格下拉框，选项从 SQLite 动态加载 + 末尾追加"原文"
- 用户切换下拉框 → 立即触发新风格润色
- 选择"原文" → 显示原始转写文本，不调用 API

### 3.3 设置面板

- 主窗口中润色风格管理页：表格展示所有风格（名称、提示词摘要、默认标记）
- 编辑：点击「编辑」→ QDialog 弹窗，名称 + 大文本区预填提示词
- 新增：点击「+ 新增风格」→ QDialog 弹窗，空白表单
- 删除：点击「删除」→ 确认对话框，如删除默认风格则自动切换默认到"正式"
- 默认：表格中有单选标识，只有一个风格为默认（首次启动自动润色的目标风格）

## 4. 架构设计

### 4.1 项目结构变更

```
src/
├── app/main.py                     # [修改] 创建 MainWindow + 托盘 + OverlayWindow 编排
├── core/config/settings.py         # [修改] 增加 polish 配置节
├── db/                             # [新增]
│   ├── __init__.py
│   └── database.py                 # SQLite 连接管理、建表、种子数据
├── modules/
│   ├── polish/                     # [新增]
│   │   ├── __init__.py
│   │   ├── polish_client.py        # DeepSeek API 异步调用
│   │   └── prompt_manager.py       # 风格数据 CRUD 封装
│   └── overlay/
│       └── overlay_window.py       # [修改] PREVIEW 增加风格下拉框 + 润色中状态
└── ui/                             # [新增]
    ├── __init__.py
    ├── main_window.py              # QMainWindow + 侧边栏导航 + 页面容器
    └── polish_page.py              # 润色风格管理页（含表格 + 编辑/新增 QDialog）
```

### 4.2 数据库设计

数据库文件：`data/polish.db`

```sql
CREATE TABLE IF NOT EXISTS polish_styles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    UNIQUE NOT NULL,
    prompt     TEXT    NOT NULL,
    is_preset  INTEGER DEFAULT 0,
    is_default INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);
```

预设种子数据（3 条，`is_preset=1`）：

| name | prompt 要点 |
|------|------------|
| 正式 | 消除口头禅，修正语序，使用正式词汇，保持原意，只返回润色文本 |
| 日常 | 改为自然流畅的日常对话风格，保留口语亲切感，去除冗余重复 |
| 简洁 | 精简至核心要点，去除冗余修饰，保持信息完整，只返回润色文本 |

首次启动时自动建表并插入 3 条预设，`正式` 设为默认（`is_default=1`）。

### 4.3 PolishClient

```
class PolishClient(QObject):
    result_ready = Signal(str)
    error_occurred = Signal(str)

    def polish(text: str, system_prompt: str, api_key: str, base_url: str, model: str)
```

- 使用 `openai.OpenAI` 客户端，在 `QThread` 中执行
- `temperature=0.3` 保证润色稳定性
- 调用完成后通过 Signal 返回，主线程安全

### 4.4 PromptManager

```
class PromptManager:
    def __init__(db_path: str)
    def get_all() -> list[dict]
    def get_default() -> dict | None
    def get_by_name(name: str) -> dict | None
    def add(name: str, prompt: str) -> int
    def update(id: int, name: str, prompt: str)
    def delete(id: int)
    def set_default(id: int)
```

- 封装 SQLite CRUD，返回 dict 列表
- 不直接暴露 SQL 给调用方

### 4.5 MainWindow

```
class MainWindow(QMainWindow):
    - 固定尺寸约 700×480
    - 左侧 QListWidget 导航
    - 右侧 QStackedWidget 页面容器
    - 页面1: 润色风格管理 (PolishPage)
    - 页面2: 关于页 (占位)
```

### 4.6 系统托盘

```
QSystemTrayIcon:
    - 图标: assets/tray.png
    - 右键菜单:
        - 显示主窗口
        - 语音输入开关 (checked/unchecked)
        - 退出
    - 关闭主窗口 → hide() 到托盘，不退出应用
```

### 4.7 悬浮窗改动

OverlayWindow PREVIEW 状态新增：

- 风格下拉框（`QComboBox`）：动态加载风格列表 + "原文"
- 润色中状态：指示灯变黄色旋转，按钮禁用，状态文字"润色中..."
- 切换下拉框 → 发射信号通知 main.py 触发 re-polish

### 4.8 配置扩展

`configs/default_settings.json` 增加：

```json
{
  "polish": {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat"
  }
}
```

`configs/settings.local.json` 填入实际密钥。

## 5. 数据流

```
ASR final_result
  → main.py 收到信号
  → PromptManager.get_default() 获取默认风格 system_prompt
  → PolishClient.polish() 异步调用 DeepSeek
  → result_ready 信号 → OverlayWindow.set_text() + 恢复按钮
  → 用户切换下拉框 → main.py 用新风格 prompt 重新 polish
  → 用户点确认 → TextInjector.inject(当前文本)
  → 用户点取消 → IDLE
```

## 6. 错误处理

| 场景 | 处理 |
|------|------|
| DeepSeek API 调用失败 | `error_occurred` 信号 → 悬浮窗保留原文 + 显示"润色失败"提示，用户可选其他风格重试 |
| 网络超时 | 同上，5 秒超时 |
| API key 未配置 | 启动时打印警告，润色功能不可用但不影响语音输入 |
| SQLite 初始化失败 | 启动时打印错误，润色功能降级为不可用 |
| 润色中用户取消 | 中断当前润色线程，回到 IDLE |

## 7. 新增依赖

```
openai  # DeepSeek API 调用（兼容 OpenAI SDK）
```

SQLite 使用 Python 内置 `sqlite3`，无需额外依赖。

## 8. PR 拆分

| PR | 内容 | 涉及文件 | 独立验证 |
|----|------|----------|----------|
| **PR1** 润色后端 | DB 基础设施 + PolishClient + PromptManager + 配置 | `src/db/`, `src/modules/polish/`, `src/core/config/`, `configs/` | 单元测试验证 API 调用和 CRUD |
| **PR2** 桌面主窗口 | MainWindow + 托盘 + 启动流程 + 润色管理页 + 弹窗 | `src/ui/`, `src/app/main.py`, `assets/` | 打开应用可视化管理风格 |
| **PR3** 悬浮窗润色集成 | OverlayWindow 改动 + 自动润色流程编排 | `src/modules/overlay/overlay_window.py`, `src/app/main.py` | 完整语音→润色→注入闭环 |

## 9. 文件变更清单

| 文件 | 操作 | PR |
|------|------|-----|
| `src/db/__init__.py` | 新增 | PR1 |
| `src/db/database.py` | 新增 | PR1 |
| `src/modules/polish/__init__.py` | 新增 | PR1 |
| `src/modules/polish/polish_client.py` | 新增 | PR1 |
| `src/modules/polish/prompt_manager.py` | 新增 | PR1 |
| `src/core/config/settings.py` | 修改 | PR1 |
| `configs/default_settings.json` | 修改 | PR1 |
| `configs/settings.json` | 修改 | PR1 |
| `requirements.txt` | 修改（+openai） | PR1 |
| `src/ui/__init__.py` | 新增 | PR2 |
| `src/ui/main_window.py` | 新增 | PR2 |
| `src/ui/polish_page.py` | 新增 | PR2 |
| `src/app/main.py` | 修改 | PR2 |
| `assets/tray.png` | 新增 | PR2 |
| `src/modules/overlay/overlay_window.py` | 修改 | PR3 |
| `src/app/main.py` | 修改 | PR3 |

## 10. 测试要点

- PR1: PolishClient API 正常/异常返回；PromptManager CRUD 正确性；预设数据初始化
- PR2: 主窗口导航切换；弹窗新增/编辑/删除；托盘显示/隐藏
- PR3: 自动润色触发时机；风格切换重新润色；润色中按钮禁用；"原文"选项正确显示；润色失败降级
