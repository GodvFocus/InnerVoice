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

            results = []
            client.result_ready.connect(lambda r: results.append(r))
            client.polish("今天下午我们开了会", "正式", "k", "u", "m")

            with qtbot.waitSignal(client.result_ready, timeout=3000):
                pass

            assert results == [expected]

    def test_api_call_parameters(self, client, qtbot):
        with patch("modules.polish.polish_client.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "结果"
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client

            client.polish("口语文本", "系统提示词", "my-key",
                          "https://api.deepseek.com", "deepseek-chat")

            with qtbot.waitSignal(client.result_ready, timeout=3000):
                pass

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

            errors = []
            client.error_occurred.connect(lambda e: errors.append(e))
            client.polish("文本", "提示词", "k", "u", "m")

            with qtbot.waitSignal(client.error_occurred, timeout=3000):
                pass

            assert len(errors) == 1
            assert "API 错误" in errors[0]
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
            client.polish("文本2", "提示词", "k", "u", "m")

            with qtbot.waitSignal(client.result_ready, timeout=3000):
                pass

            assert len(errors) == 1
            assert "正在进行中" in errors[0]
