"""PromptManager 单元测试"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

# 将 src 加入 path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from db.database import init_db
from modules.polish.prompt_manager import PromptManager


class TestPromptManager:
    """PromptManager CRUD 操作单元测试"""

    @pytest.fixture
    def pm(self):
        """创建临时数据库并返回 PromptManager 实例"""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = init_db(Path(tmp))
            yield PromptManager(db_path)

    def test_get_all_returns_3_presets(self, pm):
        """初始化后 get_all 应返回 3 条预设记录"""
        styles = pm.get_all()
        assert len(styles) == 3

    def test_get_default_returns_formal(self, pm):
        """默认风格名称应为"正式"且 is_default=1"""
        style = pm.get_default()
        assert style is not None
        assert style["name"] == "正式"
        assert style["is_default"] == 1

    def test_get_by_name_found(self, pm):
        """get_by_name("正式") 应返回字典"""
        style = pm.get_by_name("正式")
        assert style is not None
        assert isinstance(style, dict)
        assert style["name"] == "正式"

    def test_get_by_name_not_found(self, pm):
        """get_by_name("不存在的风格") 应返回 None"""
        style = pm.get_by_name("不存在的风格")
        assert style is None

    def test_add_custom_style(self, pm):
        """新增自定义风格后应能查询到，且 is_preset=0"""
        new_id = pm.add("邮件风格", "写成专业邮件")
        assert new_id > 0
        style = pm.get_by_name("邮件风格")
        assert style is not None
        assert style["prompt"] == "写成专业邮件"
        assert style["is_preset"] == 0

    def test_add_duplicate_name_raises(self, pm):
        """重复添加同名风格应触发 IntegrityError"""
        pm.add("测试风格", "测试提示词")
        with pytest.raises(sqlite3.IntegrityError):
            pm.add("测试风格", "重复的提示词")

    def test_update_style(self, pm):
        """更新风格后名称和提示词应同步变更"""
        new_id = pm.add("旧名称", "旧提示词")
        pm.update(new_id, "新名称", "新提示词")
        style = pm.get_by_name("新名称")
        assert style is not None
        assert style["prompt"] == "新提示词"
        # 旧名称应不可查
        assert pm.get_by_name("旧名称") is None

    def test_delete_custom_style(self, pm):
        """删除自定义风格后查询返回 None"""
        new_id = pm.add("待删除", "将被删除")
        pm.delete(new_id)
        assert pm.get_by_name("待删除") is None

    def test_delete_default_switches_to_formal(self, pm):
        """删除自定义默认风格后，默认自动回退为"正式"风格"""
        # 新增一个自定义风格并设为默认
        custom_id = pm.add("自定义默认", "自定义提示")
        pm.set_default(custom_id)
        assert pm.get_default()["id"] == custom_id

        # 删除该自定义默认风格
        pm.delete(custom_id)

        # 验证默认回退到"正式"
        new_default = pm.get_default()
        assert new_default is not None
        assert new_default["name"] == "正式"
        assert new_default["is_default"] == 1

    def test_set_default(self, pm):
        """设置新风格为默认后，get_default 应返回该风格"""
        new_id = pm.add("我的风格", "自定义提示词")
        pm.set_default(new_id)

        default = pm.get_default()
        assert default is not None
        assert default["id"] == new_id
        assert default["is_default"] == 1

    def test_added_style_appears_in_get_all(self, pm):
        """新增 2 个风格后 get_all 应返回 5 条记录"""
        pm.add("风格A", "提示A")
        pm.add("风格B", "提示B")
        styles = pm.get_all()
        assert len(styles) == 5
