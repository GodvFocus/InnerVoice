"""配置管理 - JSON 文件读写, 带默认值, 支持 local.json 覆盖"""

import json
from copy import deepcopy
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
    "polish": {
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
}

CONFIG_FILENAME = "settings.json"
DEFAULT_CONFIG_FILENAME = "default_settings.json"
LOCAL_CONFIG_FILENAME = "settings.local.json"


class Settings:
    """用户配置管理, DEFAULTS -> settings.json -> settings.local.json"""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent.parent / "configs"
        self._config_dir = Path(config_dir)
        self._default_config_path = self._config_dir / DEFAULT_CONFIG_FILENAME
        self._config_path = self._config_dir / CONFIG_FILENAME
        self._local_config_path = self._config_dir / LOCAL_CONFIG_FILENAME
        self._data: dict[str, Any] = deepcopy(DEFAULTS)
        self._load()

    def _load(self):
        self._load_file(self._default_config_path)
        self._load_file(self._config_path)
        self._load_file(self._local_config_path)

    def _load_file(self, path: Path):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                self._deep_merge(self._data, stored)
            except (json.JSONDecodeError, OSError):
                pass

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def save(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def all(self) -> dict[str, Any]:
        return deepcopy(self._data)
