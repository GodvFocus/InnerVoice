"""IATClient 单元测试 (mock WebSocket)"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from PySide6.QtCore import QCoreApplication

_app = QCoreApplication.instance()
if _app is None:
    _app = QCoreApplication([])

from modules.asr.iat_client import IATClient


# 模拟返回数据
PARTIAL_MSG = json.dumps({
    "code": 0,
    "message": "success",
    "sid": "test-sid",
    "data": {
        "status": 1,
        "result": {
            "ws": [{"cw": [{"w": "今天"}, {"w": "天气"}]}],
        },
    },
})

FINAL_MSG = json.dumps({
    "code": 0,
    "message": "success",
    "sid": "test-sid",
    "data": {
        "status": 2,
        "result": {
            "ws": [{"cw": [{"w": "今天天气不错"}]}],
        },
    },
})


class TestIATClient:
    """IATClient 测试 (mock WebSocket)"""

    @pytest.fixture
    def client(self):
        return IATClient("test_appid", "test_apikey", "test_apisecret")

    def test_initial_state_not_connected(self, client):
        assert client.is_connected is False

    def test_build_url(self, client):
        url = client._build_url()
        assert url.startswith("wss://iat-api.xfyun.cn/v2/iat?")
        assert "authorization=" in url
        assert "date=" in url
        assert "host=" in url

    def test_extract_text_partial(self, client):
        data = json.loads(PARTIAL_MSG)["data"]
        text = client._extract_text(data)
        assert text == "今天天气"

    def test_extract_text_empty(self, client):
        data = {"result": {"ws": []}}
        text = client._extract_text(data)
        assert text == ""

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_connect_and_disconnect(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws

        client.connect()
        assert client.is_connected is True

        client.disconnect()
        assert client.is_connected is False

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_send_audio(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws

        client.connect()
        client.send_audio(b"\x00" * 1280)
        assert mock_ws.send.called
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["data"]["status"] == 1

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_on_message_emits_partial_result(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        results = []
        client.partial_result.connect(lambda t: results.append(t))

        client._on_message(None, PARTIAL_MSG)
        assert len(results) == 1
        assert results[0] == "今天天气"

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_on_message_emits_final_result(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        results = []
        client.final_result.connect(lambda t: results.append(t))

        client._on_message(None, FINAL_MSG)
        assert len(results) == 1
        assert results[0] == "今天天气不错"

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_on_error(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        errors = []
        client.error_occurred.connect(lambda e: errors.append(e))

        client._on_error(None, "连接超时")
        assert len(errors) == 1
        assert "连接超时" in errors[0]

    @patch("modules.asr.iat_client.websocket.WebSocketApp")
    def test_send_end_frame(self, mock_ws_app, client):
        mock_ws = MagicMock()
        mock_ws_app.return_value = mock_ws
        client.connect()

        client.send_end()
        sent_data = json.loads(mock_ws.send.call_args[0][0])
        assert sent_data["data"]["status"] == 2
        assert sent_data["data"]["audio"] == ""
