"""TextInjector 单元测试 (mock win32clipboard + keyboard)"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest

from modules.injector.text_injector import TextInjector


class TestTextInjector:
    """TextInjector 测试"""

    def test_inject_empty_text_returns_false(self):
        assert TextInjector.inject("") is False

    @patch("modules.injector.text_injector.keyboard")
    @patch("modules.injector.text_injector.win32clipboard")
    def test_inject_saves_and_restores_clipboard(self, mock_clip, mock_kb):
        original_text = "原始内容"
        get_calls = [original_text, "注入文本"]

        def get_clipboard():
            return get_calls.pop(0) if get_calls else ""

        mock_clip.GetClipboardData.side_effect = get_clipboard

        ok = TextInjector.inject("注入文本")
        assert ok is True
        mock_kb.send.assert_called_once_with("ctrl+v")

    @patch("modules.injector.text_injector.keyboard")
    @patch("modules.injector.text_injector.win32clipboard")
    def test_inject_handles_clipboard_error(self, mock_clip, mock_kb):
        mock_clip.OpenClipboard.side_effect = OSError("clipboard busy")

        ok = TextInjector.inject("测试")
        assert ok is True
