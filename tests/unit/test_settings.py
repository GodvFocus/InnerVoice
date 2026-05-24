"""配置管理模块测试"""

import json
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

    def test_loads_default_settings_file(self, temp_config_dir):
        (temp_config_dir / "default_settings.json").write_text(
            json.dumps({
                "panel_width": 720,
                "asr": {
                    "appid": "demo-appid",
                    "apikey": "demo-apikey",
                    "apisecret": "demo-secret",
                },
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        settings = Settings(config_dir=temp_config_dir)
        asr = settings.get("asr")

        assert settings.get("panel_width") == 720
        assert asr["appid"] == "demo-appid"
        assert asr["apikey"] == "demo-apikey"
        assert asr["apisecret"] == "demo-secret"
        assert asr["language"] == "zh_cn"

    def test_nested_asr_config_is_deep_merged(self, temp_config_dir):
        (temp_config_dir / "default_settings.json").write_text(
            json.dumps({
                "asr": {
                    "appid": "demo-appid",
                    "apikey": "demo-apikey",
                    "apisecret": "demo-secret",
                    "language": "zh_cn",
                    "accent": "mandarin",
                },
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        (temp_config_dir / "settings.json").write_text(
            json.dumps({
                "asr": {
                    "language": "en_us",
                },
            }, ensure_ascii=False),
            encoding="utf-8",
        )

        settings = Settings(config_dir=temp_config_dir)
        asr = settings.get("asr")

        assert asr["appid"] == "demo-appid"
        assert asr["apikey"] == "demo-apikey"
        assert asr["apisecret"] == "demo-secret"
        assert asr["language"] == "en_us"
        assert asr["accent"] == "mandarin"
