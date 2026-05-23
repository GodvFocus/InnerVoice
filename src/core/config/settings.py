"""配置管理 - JSON 文件读写, 带默认值"""

import json
from pathlib import Path
from typing import Any


DEFAULTS = {
    "hotkey": "right ctrl",
    "long_press_threshold_ms": 300,
    "panel_width": 480,
    "panel_height": 40,
    "panel_offset_y": 60,
    "font_size": 13,
    "idle_timeout_seconds": 30,
}

CONFIG_FILENAME = "settings.json"


class Settings:
    """用户配置管理, 默认值 + JSON 持久化"""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent.parent / "configs"
        self._config_dir = Path(config_dir)
        self._config_path = self._config_dir / CONFIG_FILENAME
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    def _load(self):
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def all(self) -> dict[str, Any]:
        return dict(self._data)
