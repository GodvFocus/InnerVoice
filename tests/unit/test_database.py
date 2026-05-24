"""数据库模块单元测试"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

# 将 src 加入 path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from db.database import DB_FILENAME, PRESET_STYLES, init_db, get_connection


class TestDatabase:
    """数据库初始化与连接单元测试"""

    @pytest.fixture
    def db_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)

    def test_init_creates_db_file(self, db_dir):
        """init_db 应在指定目录下创建 db 文件"""
        db_path = init_db(db_dir)
        assert Path(db_path).exists()
        assert db_path == str(db_dir / DB_FILENAME)

    def test_init_inserts_presets(self, db_dir):
        """初始化后数据库中应有 3 条预设风格记录"""
        init_db(db_dir)
        db_path = db_dir / DB_FILENAME
        conn = sqlite3.connect(str(db_path))
        try:
            count = conn.execute("SELECT COUNT(*) FROM polish_styles").fetchone()[0]
            assert count == 3
        finally:
            conn.close()

    def test_presets_have_correct_data(self, db_dir):
        """验证三条预设数据的 name、is_preset、is_default 字段正确"""
        init_db(db_dir)
        conn = get_connection(str(db_dir / DB_FILENAME))
        try:
            rows = conn.execute(
                "SELECT name, is_preset, is_default, sort_order FROM polish_styles ORDER BY sort_order"
            ).fetchall()

            assert len(rows) == 3

            # 正式
            assert rows[0]["name"] == "正式"
            assert rows[0]["is_preset"] == 1
            assert rows[0]["is_default"] == 1
            assert rows[0]["sort_order"] == 0

            # 日常
            assert rows[1]["name"] == "日常"
            assert rows[1]["is_preset"] == 1
            assert rows[1]["is_default"] == 0
            assert rows[1]["sort_order"] == 1

            # 简洁
            assert rows[2]["name"] == "简洁"
            assert rows[2]["is_preset"] == 1
            assert rows[2]["is_default"] == 0
            assert rows[2]["sort_order"] == 2
        finally:
            conn.close()

    def test_init_is_idempotent(self, db_dir):
        """重复调用 init_db 不应产生重复数据"""
        init_db(db_dir)
        init_db(db_dir)
        conn = sqlite3.connect(str(db_dir / DB_FILENAME))
        try:
            count = conn.execute("SELECT COUNT(*) FROM polish_styles").fetchone()[0]
            assert count == 3
        finally:
            conn.close()

    def test_only_one_default_preset(self, db_dir):
        """所有预设中只应有一条 is_default=1 的记录"""
        init_db(db_dir)
        conn = sqlite3.connect(str(db_dir / DB_FILENAME))
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM polish_styles WHERE is_default = 1"
            ).fetchone()[0]
            assert count == 1
        finally:
            conn.close()

    def test_unique_name_constraint(self, db_dir):
        """插入重复的 name 应触发 IntegrityError"""
        init_db(db_dir)
        conn = sqlite3.connect(str(db_dir / DB_FILENAME))
        try:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO polish_styles (name, prompt, is_preset, is_default, sort_order) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("正式", "test prompt", 0, 0, 9),
                )
                conn.commit()
        finally:
            conn.close()
