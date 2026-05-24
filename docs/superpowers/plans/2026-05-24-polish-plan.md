# 口语化→书面化 AI 润色 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现语音转写文本的 AI 自动润色功能，新增桌面主窗口和 SQLite 风格管理

**Architecture:** 新增 `src/db/`、`src/modules/polish/`、`src/ui/` 三个模块。数据库用 SQLite，LLM 用 DeepSeek，异步调用通过 QThread+Signal 实现。主窗口用 QMainWindow+侧边栏导航，系统托盘最小化。

**Tech Stack:** Python 3.10+, PySide6, openai SDK, sqlite3 (内置)

---

## PR 1: 润色后端

### Task 1: 扩展配置支持 polish 节

**Files:**
- Modify: `configs/default_settings.json`
- Modify: `configs/settings.json`
- Modify: `src/core/config/settings.py`

- [ ] **Step 1: 更新 DEFAULTS 字典**

修改 `src/core/config/settings.py`，在 `DEFAULTS` 中增加 `polish` 节：

```python
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
    "polish": {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
}
```

- [ ] **Step 2: 更新 default_settings.json**

修改 `configs/default_settings.json`，增加 polish 节：

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
  },
  "polish": {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat"
  }
}
```

- [ ] **Step 3: 更新 settings.json**

修改 `configs/settings.json`，增加空 polish 节：

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
  },
  "polish": {
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat"
  }
}
```

- [ ] **Step 4: 运行现有测试确认未破坏**

```bash
D:/anaconda3/envs/any/python.exe -m pytest tests/unit/test_settings.py -v
```

- [ ] **Step 5: Commit**

```bash
git add configs/default_settings.json configs/settings.json src/core/config/settings.py
git commit -m "feat(config): 增加 polish 配置节支持 DeepSeek API"
```

---

### Task 2: SQLite 数据库基础设施

**Files:**
- Create: `src/db/__init__.py`
- Create: `src/db/database.py`
- Create: `tests/unit/test_database.py`

- [ ] **Step 1: 编写数据库模块**

创建 `src/db/__init__.py`：

```python
"""数据库层 — SQLite 连接与初始化"""
```

创建 `src/db/database.py`：

```python
"""SQLite 数据库初始化和连接管理"""

import sqlite3
from pathlib import Path


DB_FILENAME = "polish.db"

PRESET_STYLES = [
    {
        "name": "正式",
        "prompt": (
            "你是一个专业的文本润色助手。请将用户输入的口语化文本改写为正式、规范的书面语。要求：\n"
            "1. 消除口头禅和填充词（如"嗯""那个""就是说"）\n"
            "2. 修正语序不通顺的表达\n"
            "3. 使用正式词汇替换口语词汇\n"
            "4. 保持原意不变\n"
            "5. 只返回润色后的文本，不要解释"
        ),
        "is_preset": 1,
        "is_default": 1,
        "sort_order": 0,
    },
    {
        "name": "日常",
        "prompt": (
            "你是一个文本润色助手。请将用户输入的口语化文本改写为自然流畅的日常对话风格。要求：\n"
            "1. 消除明显口头禅和冗余重复\n"
            "2. 保留口语的亲切感和自然节奏\n"
            "3. 修正语法错误和不通顺表达\n"
            "4. 保持原意不变\n"
            "5. 只返回润色后的文本，不要解释"
        ),
        "is_preset": 1,
        "is_default": 0,
        "sort_order": 1,
    },
    {
        "name": "简洁",
        "prompt": (
            "你是一个文本精简助手。请将用户输入的口语化文本精简至核心要点。要求：\n"
            "1. 去除冗余修饰和重复表达\n"
            "2. 保留所有关键信息\n"
            "3. 使用简洁清晰的表达\n"
            "4. 保持原意不变\n"
            "5. 只返回精简后的文本，不要解释"
        ),
        "is_preset": 1,
        "is_default": 0,
        "sort_order": 2,
    },
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS polish_styles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    UNIQUE NOT NULL,
    prompt     TEXT    NOT NULL,
    is_preset  INTEGER DEFAULT 0,
    is_default INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);
"""


def init_db(db_dir: Path) -> str:
    """初始化数据库，返回 db 文件路径。首次调用时建表并插入预设数据。"""
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(db_dir / DB_FILENAME)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)

    cursor.execute("SELECT COUNT(*) FROM polish_styles")
    if cursor.fetchone()[0] == 0:
        for style in PRESET_STYLES:
            cursor.execute(
                "INSERT INTO polish_styles (name, prompt, is_preset, is_default, sort_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (style["name"], style["prompt"], style["is_preset"],
                 style["is_default"], style["sort_order"]),
            )
        conn.commit()

    conn.close()
    return db_path


def get_connection(db_path: str) -> sqlite3.Connection:
    """获取数据库连接，启用 Row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

- [ ] **Step 2: 编写数据库测试**

创建 `tests/unit/test_database.py`：

```python
"""数据库模块测试"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from db.database import init_db, get_connection, PRESET_STYLES


class TestDatabase:
    """数据库初始化与预设数据测试"""

    @pytest.fixture
    def temp_db_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    @pytest.fixture
    def db_path(self, temp_db_dir):
        return init_db(temp_db_dir)

    def test_init_creates_db_file(self, temp_db_dir):
        db_path = init_db(temp_db_dir)
        assert Path(db_path).exists()

    def test_init_inserts_presets(self, temp_db_dir):
        db_path = init_db(temp_db_dir)
        conn = get_connection(db_path)
        rows = conn.execute("SELECT * FROM polish_styles ORDER BY sort_order").fetchall()
        conn.close()
        assert len(rows) == 3

    def test_presets_have_correct_data(self, temp_db_dir):
        db_path = init_db(temp_db_dir)
        conn = get_connection(db_path)
        rows = conn.execute("SELECT * FROM polish_styles ORDER BY sort_order").fetchall()
        conn.close()

        assert rows[0]["name"] == "正式"
        assert rows[0]["is_preset"] == 1
        assert rows[0]["is_default"] == 1
        assert rows[1]["name"] == "日常"
        assert rows[2]["name"] == "简洁"

    def test_init_is_idempotent(self, temp_db_dir):
        init_db(temp_db_dir)
        init_db(temp_db_dir)
        db_path = str(temp_db_dir / "polish.db")
        conn = get_connection(db_path)
        count = conn.execute("SELECT COUNT(*) FROM polish_styles").fetchone()[0]
        conn.close()
        assert count == 3

    def test_only_one_default_preset(self, temp_db_dir):
        db_path = init_db(temp_db_dir)
        conn = get_connection(db_path)
        defaults = conn.execute(
            "SELECT COUNT(*) FROM polish_styles WHERE is_default = 1"
        ).fetchone()[0]
        conn.close()
        assert defaults == 1

    def test_unique_name_constraint(self, temp_db_dir):
        db_path = init_db(temp_db_dir)
        conn = get_connection(db_path)
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO polish_styles (name, prompt) VALUES (?, ?)",
                ("正式", "重复名称"),
            )
        conn.close()
```

- [ ] **Step 3: 运行测试，确认通过**

```bash
D:/anaconda3/envs/any/python.exe -m pytest tests/unit/test_database.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/db/ tests/unit/test_database.py
git commit -m "feat(db): 新增 SQLite 数据库基础设施与预设润色风格"
```

---

### Task 3: PromptManager 风格 CRUD

**Files:**
- Create: `src/modules/polish/__init__.py`
- Create: `src/modules/polish/prompt_manager.py`
- Create: `tests/unit/test_prompt_manager.py`

- [ ] **Step 1: 编写 PromptManager**

创建 `src/modules/polish/__init__.py`：

```python
"""润色模块 — LLM 客户端 + 提示词管理"""
```

创建 `src/modules/polish/prompt_manager.py`：

```python
"""提示词管理器 — 封装 polish_styles 表的 CRUD"""

from db.database import get_connection


class PromptManager:
    """润色风格数据管理

    用法:
        pm = PromptManager("path/to/polish.db")
        styles = pm.get_all()
        default_style = pm.get_default()
    """

    def __init__(self, db_path: str):
        self._db_path = db_path

    def get_all(self) -> list[dict]:
        """获取所有风格，按 sort_order 排序"""
        conn = get_connection(self._db_path)
        rows = conn.execute(
            "SELECT id, name, prompt, is_preset, is_default, sort_order "
            "FROM polish_styles ORDER BY sort_order"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_default(self) -> dict | None:
        """获取默认风格"""
        conn = get_connection(self._db_path)
        row = conn.execute(
            "SELECT id, name, prompt, is_preset, is_default, sort_order "
            "FROM polish_styles WHERE is_default = 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_by_name(self, name: str) -> dict | None:
        """按名称获取风格"""
        conn = get_connection(self._db_path)
        row = conn.execute(
            "SELECT id, name, prompt, is_preset, is_default, sort_order "
            "FROM polish_styles WHERE name = ?", (name,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def add(self, name: str, prompt: str) -> int:
        """新增自定义风格，返回新行 id"""
        conn = get_connection(self._db_path)
        # 新风格的 sort_order 放在预设之后
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM polish_styles"
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO polish_styles (name, prompt, is_preset, is_default, sort_order) "
            "VALUES (?, ?, 0, 0, ?)",
            (name, prompt, max_order + 1),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id

    def update(self, style_id: int, name: str, prompt: str):
        """更新风格名称和提示词"""
        conn = get_connection(self._db_path)
        conn.execute(
            "UPDATE polish_styles SET name = ?, prompt = ? WHERE id = ?",
            (name, prompt, style_id),
        )
        conn.commit()
        conn.close()

    def delete(self, style_id: int):
        """删除风格。如果是默认风格，则先自动切换默认到'正式'"""
        conn = get_connection(self._db_path)
        row = conn.execute(
            "SELECT is_default FROM polish_styles WHERE id = ?", (style_id,)
        ).fetchone()
        if row and row["is_default"]:
            conn.execute(
                "UPDATE polish_styles SET is_default = 1 WHERE name = '正式'"
            )
        conn.execute("DELETE FROM polish_styles WHERE id = ?", (style_id,))
        conn.commit()
        conn.close()

    def set_default(self, style_id: int):
        """设置指定风格为默认"""
        conn = get_connection(self._db_path)
        conn.execute("UPDATE polish_styles SET is_default = 0")
        conn.execute(
            "UPDATE polish_styles SET is_default = 1 WHERE id = ?", (style_id,)
        )
        conn.commit()
        conn.close()
```

- [ ] **Step 2: 编写 PromptManager 测试**

创建 `tests/unit/test_prompt_manager.py`：

```python
"""PromptManager 测试"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from db.database import init_db
from modules.polish.prompt_manager import PromptManager


class TestPromptManager:
    """PromptManager CRUD 测试"""

    @pytest.fixture
    def manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = init_db(Path(tmp))
            yield PromptManager(db_path)

    def test_get_all_returns_3_presets(self, manager):
        styles = manager.get_all()
        assert len(styles) == 3

    def test_get_default_returns_formal(self, manager):
        default = manager.get_default()
        assert default is not None
        assert default["name"] == "正式"
        assert default["is_default"] == 1

    def test_get_by_name_found(self, manager):
        style = manager.get_by_name("正式")
        assert style is not None
        assert style["name"] == "正式"

    def test_get_by_name_not_found(self, manager):
        style = manager.get_by_name("不存在的风格")
        assert style is None

    def test_add_custom_style(self, manager):
        new_id = manager.add("邮件风格", "写成专业邮件")
        assert new_id > 0
        style = manager.get_by_name("邮件风格")
        assert style is not None
        assert style["is_preset"] == 0
        assert style["prompt"] == "写成专业邮件"

    def test_add_duplicate_name_raises(self, manager):
        manager.add("邮件风格", "写成专业邮件")
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            manager.add("邮件风格", "另一个提示词")

    def test_update_style(self, manager):
        new_id = manager.add("测试", "原始提示词")
        manager.update(new_id, "测试修改", "新提示词")
        style = manager.get_by_name("测试修改")
        assert style is not None
        assert style["prompt"] == "新提示词"

    def test_delete_custom_style(self, manager):
        new_id = manager.add("待删除", "测试")
        manager.delete(new_id)
        assert manager.get_by_name("待删除") is None

    def test_delete_default_switches_to_formal(self, manager):
        default = manager.get_default()
        manager.delete(default["id"])
        new_default = manager.get_default()
        assert new_default is not None
        assert new_default["name"] == "正式"

    def test_set_default(self, manager):
        # 先新增一个风格，再设为默认
        new_id = manager.add("日常优先", "自定义提示词")
        manager.set_default(new_id)
        default = manager.get_default()
        assert default["id"] == new_id
        assert default["name"] == "日常优先"

    def test_added_style_appears_in_get_all(self, manager):
        manager.add("新风格A", "prompt A")
        manager.add("新风格B", "prompt B")
        styles = manager.get_all()
        assert len(styles) == 5
```

- [ ] **Step 3: 运行测试，确认通过**

```bash
D:/anaconda3/envs/any/python.exe -m pytest tests/unit/test_prompt_manager.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/modules/polish/ tests/unit/test_prompt_manager.py
git commit -m "feat(polish): 新增 PromptManager 风格 CRUD 管理器"
```

---

### Task 4: PolishClient DeepSeek 异步调用

**Files:**
- Create: `src/modules/polish/polish_client.py`
- Create: `tests/unit/test_polish_client.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 安装 openai 依赖**

```bash
D:/anaconda3/envs/any/python.exe -m pip install openai
```

- [ ] **Step 2: 更新 requirements.txt**

修改 `requirements.txt`，增加 `openai`：

```
keyboard==0.13.5
PyAudio==0.2.14
pyside6==6.11.1
pyside6_addons==6.11.1
pyside6_essentials==6.11.1
pytest==9.0.3
pywin32==311
websocket_client==1.9.0
openai
```

- [ ] **Step 3: 编写 PolishClient**

创建 `src/modules/polish/polish_client.py`：

```python
"""DeepSeek 润色客户端 — QThread 异步调用，通过 Signal 返回结果"""

from openai import OpenAI

from PySide6.QtCore import QObject, Signal, QThread


class PolishWorker(QObject):
    """在 QThread 中执行的润色工作对象"""

    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, text: str, system_prompt: str, api_key: str,
                 base_url: str, model: str, parent: QObject | None = None):
        super().__init__(parent)
        self._text = text
        self._system_prompt = system_prompt
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    def run(self):
        """在 QThread 中执行"""
        try:
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": self._text},
                ],
                temperature=0.3,
                timeout=30.0,
            )
            result = response.choices[0].message.content
            self.result_ready.emit(result.strip())
        except Exception as e:
            self.error_occurred.emit(str(e))


class PolishClient(QObject):
    """润色客户端，管理 QThread 生命周期

    用法:
        client = PolishClient()
        client.result_ready.connect(on_result)
        client.error_occurred.connect(on_error)
        client.polish("今天开会说了一下", "正式", api_key, base_url, model)
    """

    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: PolishWorker | None = None
        self._busy = False

    @property
    def busy(self) -> bool:
        return self._busy

    def polish(self, text: str, system_prompt: str, api_key: str,
               base_url: str, model: str):
        """异步发起润色请求，通过 result_ready/error_occurred 信号返回结果"""
        if self._busy:
            self.error_occurred.emit("润色正在进行中，请稍后再试")
            return

        self._busy = True
        self._thread = QThread()
        self._worker = PolishWorker(text, system_prompt, api_key, base_url, model)

        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result_ready.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, result: str):
        self._cleanup()
        self.result_ready.emit(result)

    def _on_error(self, error: str):
        self._cleanup()
        self.error_occurred.emit(error)

    def _cleanup(self):
        self._busy = False
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.quit()
            self._thread = None
```

- [ ] **Step 4: 编写 PolishClient 测试**

创建 `tests/unit/test_polish_client.py`：

```python
"""PolishClient 测试 — 使用 Mock 避免真实 API 调用"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from PySide6.QtCore import QCoreApplication

_app = QCoreApplication.instance()
if _app is None:
    _app = QCoreApplication([])

from modules.polish.polish_client import PolishClient


class TestPolishClient:
    """PolishClient 异步调用测试"""

    @pytest.fixture
    def client(self):
        return PolishClient()

    def test_busy_flag_during_polish(self, client, qtbot):
        with patch("modules.polish.polish_client.OpenAI") as mock_openai:
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "润色后的文本"
            mock_openai.return_value.chat.completions.create.return_value = mock_completion

            client.polish("测试文本", "测试提示词", "key", "url", "model")
            assert client.busy is True

            with qtbot.waitSignal(client.result_ready, timeout=3000):
                pass

            assert client.busy is False

    def test_result_ready_signal(self, client, qtbot):
        with patch("modules.polish.polish_client.OpenAI") as mock_openai:
            expected = "今日下午我们召开了项目会议"
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = expected
            mock_openai.return_value.chat.completions.create.return_value = mock_completion

            with qtbot.waitSignal(client.result_ready, timeout=3000) as blocker:
                client.polish("今天下午我们开了会", "正式", "k", "u", "m")

            assert blocker.args[0] == expected

    def test_api_call_parameters(self, client, qtbot):
        with patch("modules.polish.polish_client.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "结果"
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            with qtbot.waitSignal(client.result_ready, timeout=3000):
                client.polish("口语文本", "系统提示词", "my-key",
                              "https://api.deepseek.com", "deepseek-chat")

            mock_openai.assert_called_once_with(
                api_key="my-key",
                base_url="https://api.deepseek.com",
            )
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "deepseek-chat"
            assert call_kwargs["temperature"] == 0.3
            assert len(call_kwargs["messages"]) == 2
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][0]["content"] == "系统提示词"
            assert call_kwargs["messages"][1]["role"] == "user"
            assert call_kwargs["messages"][1]["content"] == "口语文本"

    def test_error_signal_on_exception(self, client, qtbot):
        with patch("modules.polish.polish_client.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API 错误")
            mock_openai.return_value = mock_client

            with qtbot.waitSignal(client.error_occurred, timeout=3000) as blocker:
                client.polish("文本", "提示词", "k", "u", "m")

            assert "API 错误" in blocker.args[0]
            assert client.busy is False

    def test_double_polish_rejected(self, client, qtbot):
        with patch("modules.polish.polish_client.OpenAI") as mock_openai:
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "结果"
            mock_openai.return_value.chat.completions.create.return_value = mock_completion

            errors = []
            client.error_occurred.connect(lambda e: errors.append(e))

            client.polish("文本1", "提示词", "k", "u", "m")
            # 第一次未完成时发起第二次
            client.polish("文本2", "提示词", "k", "u", "m")

            with qtbot.waitSignal(client.result_ready, timeout=3000):
                pass

            assert len(errors) == 1
            assert "正在进行中" in errors[0]
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
D:/anaconda3/envs/any/python.exe -m pytest tests/unit/test_polish_client.py -v
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/modules/polish/polish_client.py tests/unit/test_polish_client.py
git commit -m "feat(polish): 新增 PolishClient DeepSeek 异步润色客户端"
```

---

## PR 2: 桌面主窗口

### Task 5: 润色风格管理页 + 弹窗

**Files:**
- Create: `src/ui/__init__.py`
- Create: `src/ui/polish_page.py`

- [ ] **Step 1: 编写润色管理页**

创建 `src/ui/__init__.py`：

```python
"""UI 层 — 主窗口和设置页面"""
```

创建 `src/ui/polish_page.py`：

```python
"""润色风格管理页 — 表格 + 编辑/新增弹窗"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QDialog, QLabel, QLineEdit, QTextEdit,
    QMessageBox, QAbstractItemView,
)


class StyleDialog(QDialog):
    """编辑 / 新增润色风格的弹窗"""

    def __init__(self, title: str, name: str = "", prompt: str = "",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(500, 340)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLabel {
                color: #a6adc4;
                font-size: 12px;
            }
            QLineEdit, QTextEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QPushButton {
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 风格名称
        layout.addWidget(QLabel("风格名称"))
        self._name_edit = QLineEdit(name)
        self._name_edit.setPlaceholderText("例如：邮件、小红书、技术文档...")
        layout.addWidget(self._name_edit)

        # 提示词
        layout.addWidget(QLabel("系统提示词（指导 LLM 如何改写文本）"))
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setPlainText(prompt)
        self._prompt_edit.setMinimumHeight(140)
        self._prompt_edit.setPlaceholderText(
            "描述你希望 LLM 如何润色文本，例如：\n\n"
            "你是一个专业的文本润色助手。请将用户输入的口语化文本改写为xxx风格。要求：\n"
            "1. ...\n"
            "2. ...\n"
            "只返回润色后的文本，不要解释"
        )
        layout.addWidget(self._prompt_edit)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(
            "background: transparent; color: #a6adc4; border: 1px solid #585b70;"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self._confirm_btn = QPushButton("保存" if name else "新增")
        self._confirm_btn.setStyleSheet(
            "background: #cba6f7; color: #1e1e2e; border: none;"
        )
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self._confirm_btn)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        if not self._name_edit.text().strip():
            return
        if not self._prompt_edit.toPlainText().strip():
            return
        self.accept()

    def style_name(self) -> str:
        return self._name_edit.text().strip()

    def style_prompt(self) -> str:
        return self._prompt_edit.toPlainText().strip()


class PolishPage(QWidget):
    """润色风格管理页 — 主窗口的子页面"""

    styles_changed = Signal()  # 风格变更通知（供悬浮窗刷新下拉框）

    STYLE_COLORS = {
        "正式": "#89b4fa",
        "日常": "#a6e3a1",
        "简洁": "#f9e2af",
    }

    def __init__(self, manager, parent: QWidget | None = None):
        super().__init__(parent)
        self._manager = manager
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题行
        title_layout = QHBoxLayout()
        title = QLabel("润色风格管理")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setStyleSheet("color: #cdd6f4;")
        title_layout.addWidget(title)
        title_layout.addStretch()

        add_btn = QPushButton("＋ 新增风格")
        add_btn.setStyleSheet(
            "background: #a6e3a1; color: #1e1e2e; border: none; "
            "border-radius: 4px; padding: 6px 16px; font-size: 12px;"
        )
        add_btn.clicked.connect(self._on_add)
        title_layout.addWidget(add_btn)
        layout.addLayout(title_layout)

        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["风格名称", "提示词", "默认", "操作"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 100)
        self._table.setColumnWidth(2, 50)
        self._table.setColumnWidth(3, 120)

        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                alternate-background-color: #252537;
                border: 1px solid #313244;
                border-radius: 6px;
                gridline-color: #313244;
                color: #cdd6f4;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #313244;
            }
            QHeaderView::section {
                background-color: #181825;
                color: #a6adc4;
                padding: 8px 12px;
                border: none;
                border-bottom: 1px solid #45475a;
                font-size: 11px;
                font-weight: bold;
            }
        """)

        layout.addWidget(self._table)

    def _refresh_table(self):
        styles = self._manager.get_all()
        self._table.setRowCount(len(styles))

        for row, style in enumerate(styles):
            # 名称
            self._table.setItem(row, 0, QTableWidgetItem(style["name"]))

            # 提示词摘要（最多显示 40 个字符）
            prompt_preview = style["prompt"][:40] + "..." if len(style["prompt"]) > 40 else style["prompt"]
            prompt_item = QTableWidgetItem(prompt_preview)
            prompt_item.setForeground(Qt.GlobalColor.gray)
            self._table.setItem(row, 1, prompt_item)

            # 默认标记
            default_item = QTableWidgetItem("✓" if style["is_default"] else "")
            default_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if style["is_default"]:
                default_item.setForeground(Qt.GlobalColor.green)
            self._table.setItem(row, 2, default_item)

            # 操作按钮
            btn_widget = QWidget()
            btn_widget.setStyleSheet("background: transparent;")
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet(
                "background: #89b4fa; color: #1e1e2e; border: none; "
                "border-radius: 3px; padding: 3px 10px; font-size: 10px;"
            )
            edit_btn.clicked.connect(lambda _, s=style: self._on_edit(s))
            btn_layout.addWidget(edit_btn)

            # 预设风格没有默认按钮（用 set_default 替代）
            set_def_btn = QPushButton("设默认")
            set_def_btn.setStyleSheet(
                "background: #f9e2af; color: #1e1e2e; border: none; "
                "border-radius: 3px; padding: 3px 10px; font-size: 10px;"
            )
            set_def_btn.clicked.connect(lambda _, s=style: self._on_set_default(s))
            set_def_btn.setVisible(not style["is_default"])
            btn_layout.addWidget(set_def_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet(
                "background: #f38ba8; color: #1e1e2e; border: none; "
                "border-radius: 3px; padding: 3px 10px; font-size: 10px;"
            )
            delete_btn.clicked.connect(lambda _, s=style: self._on_delete(s))
            btn_layout.addWidget(delete_btn)

            self._table.setCellWidget(row, 3, btn_widget)

    def _on_add(self):
        dlg = StyleDialog("新增润色风格", parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._manager.add(dlg.style_name(), dlg.style_prompt())
            self._refresh_table()
            self.styles_changed.emit()

    def _on_edit(self, style: dict):
        dlg = StyleDialog(
            "编辑润色风格",
            name=style["name"],
            prompt=style["prompt"],
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._manager.update(style["id"], dlg.style_name(), dlg.style_prompt())
            self._refresh_table()
            self.styles_changed.emit()

    def _on_delete(self, style: dict):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除风格「{style['name']}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.delete(style["id"])
            self._refresh_table()
            self.styles_changed.emit()

    def _on_set_default(self, style: dict):
        self._manager.set_default(style["id"])
        self._refresh_table()
        self.styles_changed.emit()
```

- [ ] **Step 2: Commit**

```bash
git add src/ui/
git commit -m "feat(ui): 新增润色风格管理页与编辑弹窗"
```

---

### Task 6: MainWindow + 系统托盘 + 启动流程

**Files:**
- Create: `src/ui/main_window.py`
- Modify: `src/app/main.py`

- [ ] **Step 1: 编写 MainWindow**

创建 `src/ui/main_window.py`：

```python
"""主窗口 — 侧边导航 + 页面容器"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel,
    QSystemTrayIcon, QMenu, QApplication, QSizePolicy,
)

from ui.polish_page import PolishPage


NAV_ITEMS = [
    {"label": "润色风格", "icon": "✏️"},
    {"label": "关于", "icon": "ℹ️"},
]


class MainWindow(QMainWindow):
    """InnerVoice 桌面主窗口"""

    def __init__(self, prompt_manager, parent=None):
        super().__init__(parent)
        self._prompt_manager = prompt_manager
        self._setup_window()
        self._setup_ui()
        self._setup_tray()

    def _setup_window(self):
        self.setWindowTitle("InnerVoice")
        self.setFixedSize(700, 480)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #181825;
            }
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 侧边栏 ---
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("background-color: #11111b;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(0)

        # Logo
        logo = QLabel("  InnerVoice")
        logo.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        logo.setStyleSheet("color: #cba6f7; padding: 0 16px 20px;")
        sidebar_layout.addWidget(logo)

        # 导航列表
        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: #a6adc4;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 16px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:selected {
                background-color: #1e1e2e;
                color: #89b4fa;
                border-left: 3px solid #89b4fa;
            }
            QListWidget::item:hover {
                color: #cdd6f4;
            }
        """)
        for item_data in NAV_ITEMS:
            item = QListWidgetItem(f"  {item_data['icon']}  {item_data['label']}")
            self._nav_list.addItem(item)

        self._nav_list.setCurrentRow(0)
        sidebar_layout.addWidget(self._nav_list)
        sidebar_layout.addStretch()

        # 版本号
        version_label = QLabel("  v1.0")
        version_label.setStyleSheet("color: #585b70; font-size: 11px; padding: 0 16px;")
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(sidebar)

        # --- 页面容器 ---
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background-color: #1e1e2e;")

        # 页面 0: 润色风格管理
        self._polish_page = PolishPage(self._prompt_manager)
        self._stack.addWidget(self._polish_page)

        # 页面 1: 关于
        about_page = QWidget()
        about_layout = QVBoxLayout(about_page)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label = QLabel(
            "InnerVoice v1.0\n\n"
            "轻量级语音输入法 — 说你所想，落笔生花\n\n"
            "Powered by PySide6 + DeepSeek"
        )
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label.setStyleSheet("color: #a6adc4; font-size: 13px; line-height: 1.8;")
        about_layout.addWidget(about_label)
        self._stack.addWidget(about_page)

        main_layout.addWidget(self._stack)

        # 导航切换
        self._nav_list.currentRowChanged.connect(self._stack.setCurrentIndex)

    def _setup_tray(self):
        """创建系统托盘"""
        self._tray = QSystemTrayIcon()
        # 使用程序化生成图标 (16x16 紫色方块)
        from PySide6.QtGui import QPixmap, QPainter, QColor
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#cba6f7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 4, 24, 24, 6, 6)
        painter.end()
        self._tray.setIcon(QIcon(pixmap))
        self._tray.setToolTip("InnerVoice — 语音输入法")

        menu = QMenu()
        show_action = QAction("显示主窗口")
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("退出")
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _on_quit(self):
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """关闭窗口时最小化到托盘"""
        event.ignore()
        self.hide()

    def polish_page(self) -> PolishPage:
        return self._polish_page
```

- [ ] **Step 2: 修改 main.py 使用 MainWindow**

修改 `src/app/main.py`，将现有 `QApplication` + 悬浮窗直接启动改为 MainWindow 模式。

修改后的 `src/app/main.py`：

```python
"""InnerVoice 语音输入法 — 应用入口

编排顺序:
    1. 创建 QApplication
    2. 初始化 Settings → 初始化 SQLite DB → PromptManager
    3. 创建 MainWindow + 系统托盘
    4. 初始化 StateMachine → OverlayWindow → HotkeyManager → ASR 模块
    5. 进入事件循环
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
from ui.main_window import MainWindow
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

    # --- 初始化 ---
    settings = Settings()

    # 数据库 & 提示词管理
    data_dir = Path(__file__).parent.parent.parent / "data"
    db_path = init_db(data_dir)
    prompt_manager = PromptManager(db_path)

    # 主窗口 + 托盘
    main_window = MainWindow(prompt_manager)
    main_window.show()

    # ASR 相关模块
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

    # 绑定: IATClient 握手完成 -> 启动录音
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

    # 绑定: ASR 资源清理
    def on_cleanup(new_state: AppState, old_state: AppState):
        nonlocal target_window
        if new_state == AppState.IDLE and old_state in (AppState.LISTENING, AppState.PROCESSING):
            audio_capture.stop()
            iat_client.disconnect()
        if new_state == AppState.IDLE:
            target_window = None
            overlay.set_text("")

    state_machine.state_changed.connect(on_cleanup)

    # 在开始录音前记录当前输入窗口
    def on_asr_start():
        nonlocal target_window
        target_window = TextInjector.current_window()

    hotkey_manager.asr_start_requested.connect(on_asr_start)

    # 按钮
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
```

- [ ] **Step 3: Commit**

```bash
git add src/ui/main_window.py src/app/main.py
git commit -m "feat(ui): 新增 MainWindow + 系统托盘，重构启动流程"
```

---

## PR 3: 悬浮窗润色集成

### Task 7: OverlayWindow 增加风格下拉框 + 润色中状态

**Files:**
- Modify: `src/modules/overlay/overlay_window.py`

- [ ] **Step 1: 修改 OverlayWindow**

修改 `src/modules/overlay/overlay_window.py`，在 PREVIEW 状态增加风格下拉框和润色中状态：

修改 `_setup_ui` 方法，在确认按钮之前插入下拉框：

```python
# 在 _setup_ui 中，在 self._btn_confirm 之前添加下拉框

        # 风格下拉框
        self._style_combo = QComboBox()
        self._style_combo.setStyleSheet("""
            QComboBox {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #585b70;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 72px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                selection-background-color: #45475a;
            }
        """)
        self._style_combo.setVisible(False)
        self._style_combo.currentTextChanged.connect(self._on_style_changed)
        layout.addWidget(self._style_combo)
```

在 `__init__` 中添加信号声明（在类属性中）：

```python
class OverlayWindow(QWidget):
    """无边框悬浮窗, 底部居中"""

    style_changed = Signal(str)  # 用户切换风格
```

在文件顶部更新导入：

```python
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QComboBox, QApplication,
)
```

添加方法：

```python
    def _on_style_changed(self, style_name: str):
        """用户切换下拉框风格，发射信号"""
        if style_name:
            self.style_changed.emit(style_name)

    def load_styles(self, style_names: list[str]):
        """加载风格列表到下拉框"""
        current = self._style_combo.currentText()
        self._style_combo.blockSignals(True)
        self._style_combo.clear()
        self._style_combo.addItems(style_names)
        self._style_combo.addItem("原文")
        if current and current in style_names:
            self._style_combo.setCurrentText(current)
        self._style_combo.blockSignals(False)

    def set_polishing_state(self, polishing: bool):
        """设置润色中状态"""
        if polishing:
            self._status_label.setText("润色中")
            self._style_combo.setEnabled(False)
            self._btn_confirm.setEnabled(False)
            self._btn_cancel.setEnabled(False)
        else:
            self._status_label.setText("完成")
            self._style_combo.setEnabled(True)
            self._btn_confirm.setEnabled(True)
            self._btn_cancel.setEnabled(True)
```

修改 `on_state_changed` 中 PREVIEW 状态的逻辑：

```python
        elif new_state == AppState.PREVIEW:
            self._status_label.setText("润色中")
            self._style_combo.setVisible(True)
            self._style_combo.setEnabled(False)
            self._btn_confirm.setVisible(True)
            self._btn_confirm.setEnabled(False)
            self._btn_cancel.setVisible(True)
            self._btn_cancel.setEnabled(False)
            self._btn_cancel.setText("取消")
            self.show()
```

修改 IDLE 状态清理下拉框：

```python
        if new_state == AppState.IDLE:
            self._style_combo.setVisible(False)
            self.hide()
            return
```

重命名 `text()` 方法避免与 QWidget.text() 冲突：

```python
    def current_text(self) -> str:
        return self._text_label.text()
```

- [ ] **Step 2: 同步修改 main.py 中的 set_text_getter 调用**

修改 `src/app/main.py`，更新 text getter 的绑定：

```python
hotkey_manager.set_text_getter(overlay.current_text)
```

- [ ] **Step 3: Commit**

```bash
git add src/modules/overlay/overlay_window.py src/app/main.py
git commit -m "feat(overlay): PREVIEW 状态增加风格下拉框与润色中状态"
```

---

### Task 8: 自动润色流程编排

**Files:**
- Modify: `src/app/main.py`

- [ ] **Step 1: 在 main.py 中集成润色客户端 + 自动润色流程**

修改 `src/app/main.py`，在现有模块初始化后添加润色逻辑。

在导入区添加：

```python
from modules.polish.polish_client import PolishClient
```

在模块初始化区添加 PolishClient：

```python
    # 润色客户端
    polish_client = PolishClient()
    polish_config = settings.get("polish")
    _raw_text = ""  # 保持原始转写文本引用

    def start_polish(style_name: str = None):
        """开始润色，如果 style_name 为 None 则使用默认风格"""
        nonlocal _raw_text
        if not polish_config.get("api_key"):
            print("[Polish] API key 未配置，跳过润色")
            overlay.set_polishing_state(False)
            return

        if style_name is None:
            default_style = prompt_manager.get_default()
            if default_style is None:
                return
            style_name = default_style["name"]

        if style_name == "原文":
            overlay.set_text(_raw_text)
            overlay.set_polishing_state(False)
            return

        style = prompt_manager.get_by_name(style_name)
        if style is None:
            return

        overlay.set_polishing_state(True)
        polish_client.polish(
            text=_raw_text,
            system_prompt=style["prompt"],
            api_key=polish_config["api_key"],
            base_url=polish_config["base_url"],
            model=polish_config["model"],
        )
```

修改 `on_final_result` 以保存原始文本并触发自动润色：

```python
    def on_final_result(text: str):
        nonlocal _raw_text
        audio_capture.stop()
        iat_client.disconnect()
        _raw_text = text
        overlay.set_text(text)
        state_machine.transition(AppState.PREVIEW)
        # 加载风格列表并自动润色
        styles = prompt_manager.get_all()
        overlay.load_styles([s["name"] for s in styles])
        start_polish()  # 使用默认风格自动润色
```

绑定润色结果信号：

```python
    def on_polish_result(result: str):
        overlay.set_text(result)
        overlay.set_polishing_state(False)

    def on_polish_error(error: str):
        print(f"[Polish Error] {error}")
        overlay.set_text(_raw_text)
        overlay.set_polishing_state(False)

    polish_client.result_ready.connect(on_polish_result)
    polish_client.error_occurred.connect(on_polish_error)
```

绑定风格切换信号：

```python
    def on_style_switch(style_name: str):
        if state_machine.current_state == AppState.PREVIEW:
            start_polish(style_name)

    overlay.style_changed.connect(on_style_switch)
```

- [ ] **Step 2: 运行完整流程验证**

手动启动应用，测试完整流程：

1. `D:/anaconda3/envs/any/python.exe src/app/main.py`
2. 确认主窗口出现，系统托盘图标出现
3. 长按右 Ctrl → 说话 → 松开 → 等待自动润色
4. 确认润色后文本正确显示
5. 切换风格下拉框 → 确认重新润色
6. 选择"原文" → 确认显示原始转写
7. 确认按钮注入文本

- [ ] **Step 3: Commit**

```bash
git add src/app/main.py
git commit -m "feat(polish): 集成自动润色流程 — 转写完成后自动润色并支持风格切换"
```

---

## 最终验证

全部 3 个 PR 完成后，运行全部测试：

```bash
D:/anaconda3/envs/any/python.exe -m pytest tests/unit/ -v
```

预期全部通过。
