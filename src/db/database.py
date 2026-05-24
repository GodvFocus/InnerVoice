"""数据库初始化与连接管理模块"""

import sqlite3
from pathlib import Path

DB_FILENAME = "polish.db"

PRESET_STYLES = [
    {
        "name": "正式",
        "prompt": "请将以下口语化的内容转换为正式、规范的书面中文表达，保持原意不变，"
        "使用恰当的书面语词汇和句式，避免口语化表达。",
        "is_preset": 1,
        "is_default": 1,
        "sort_order": 0,
    },
    {
        "name": "日常",
        "prompt": "请将以下内容转换为自然流畅的日常对话风格，保持亲切友好的语气，"
        "适合日常交流场景。",
        "is_preset": 1,
        "is_default": 0,
        "sort_order": 1,
    },
    {
        "name": "简洁",
        "prompt": "请将以下内容精简为简洁明了的表达，去除冗余信息，"
        "保留核心内容，使文本更加精炼易读。",
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

INSERT_PRESET_SQL = """
INSERT INTO polish_styles (name, prompt, is_preset, is_default, sort_order)
VALUES (?, ?, ?, ?, ?)
"""


def init_db(db_dir: Path) -> str:
    """初始化数据库：创建目录、建表、写入预设数据（仅首次）"""
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(db_dir / DB_FILENAME)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(CREATE_TABLE_SQL)

        # 检查是否已有数据，若无则插入预设风格
        row_count = conn.execute("SELECT COUNT(*) FROM polish_styles").fetchone()[0]
        if row_count == 0:
            for style in PRESET_STYLES:
                conn.execute(
                    INSERT_PRESET_SQL,
                    (
                        style["name"],
                        style["prompt"],
                        style["is_preset"],
                        style["is_default"],
                        style["sort_order"],
                    ),
                )
            conn.commit()
    finally:
        conn.close()

    return db_path


def get_connection(db_path: str) -> sqlite3.Connection:
    """获取数据库连接，使用 sqlite3.Row 作为行工厂"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
