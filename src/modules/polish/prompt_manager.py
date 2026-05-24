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
        """删除风格。如果是默认风格，先自动切换到排序最前的预设风格"""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT is_default FROM polish_styles WHERE id = ?", (style_id,)
            ).fetchone()
            if row and row["is_default"]:
                conn.execute(
                    "UPDATE polish_styles SET is_default = 1 "
                    "WHERE id = (SELECT id FROM polish_styles "
                    "WHERE is_preset = 1 ORDER BY sort_order LIMIT 1)"
                )
            conn.execute("DELETE FROM polish_styles WHERE id = ?", (style_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_default(self, style_id: int):
        """设置指定风格为默认"""
        conn = get_connection(self._db_path)
        try:
            conn.execute("UPDATE polish_styles SET is_default = 0")
            conn.execute(
                "UPDATE polish_styles SET is_default = 1 WHERE id = ?", (style_id,)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
