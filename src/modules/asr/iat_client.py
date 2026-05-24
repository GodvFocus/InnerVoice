"""讯飞语音听写(流式版) IAT WebSocket 客户端"""

import base64
import datetime
import hashlib
import hmac
import json
import threading
import uuid

import websocket

from PySide6.QtCore import QObject, Signal


# IAT WebSocket 地址
IAT_URL = "wss://iat-api.xfyun.cn/v2/iat"
HOST = "iat-api.xfyun.cn"
URI = "/v2/iat"


class IATClient(QObject):
    """讯飞语音听写 WebSocket 客户端

    用法:
        client = IATClient(appid, apikey, apisecret)
        client.partial_result.connect(on_partial)
        client.final_result.connect(on_final)
        client.error_occurred.connect(on_error)
        client.connect()
        client.send_audio(pcm_bytes)
        client.send_end()
    """

    partial_result = Signal(str)   # 中间识别文本
    final_result = Signal(str)     # 最终识别文本
    error_occurred = Signal(str)   # 错误信息
    connected = Signal()           # 握手成功
    disconnected = Signal()        # 连接断开

    def __init__(
        self,
        appid: str,
        apikey: str,
        apisecret: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._appid = appid
        self._apikey = apikey
        self._apisecret = apisecret
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._running

    def connect(self):
        """建立 WebSocket 连接并握手"""
        if self._running:
            return
        url = self._build_url()
        self._running = True
        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._thread.start()

    def send_audio(self, data: bytes):
        """发送音频帧 (status=1, 中间帧)"""
        if not self._ws or not self._running:
            return
        frame = {
            "data": {
                "status": 1,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": base64.b64encode(data).decode("utf-8"),
            }
        }
        try:
            self._ws.send(json.dumps(frame))
        except Exception as e:
            self.error_occurred.emit(f"发送音频失败: {e}")

    def send_end(self):
        """发送结束帧 (status=2)"""
        if not self._ws or not self._running:
            return
        frame = {
            "data": {
                "status": 2,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": "",
            }
        }
        try:
            self._ws.send(json.dumps(frame))
        except Exception as e:
            self.error_occurred.emit(f"发送结束帧失败: {e}")

    def disconnect(self):
        """主动断开连接"""
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    # --- WebSocket 回调 ---

    def _on_open(self, ws):
        """握手成功, 发送首帧"""
        first_frame = {
            "common": {"app_id": self._appid},
            "business": {
                "domain": "iat",
                "language": "zh_cn",
                "accent": "mandarin",
                "dwa": "wpgs",
                "vinfo": 1,
                "vad_eos": 10000,
            },
            "data": {
                "status": 0,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": base64.b64encode(b"").decode("utf-8"),
            },
        }
        ws.send(json.dumps(first_frame))
        self.connected.emit()

    def _on_message(self, ws, message):
        """接收识别结果"""
        try:
            result = json.loads(message)
        except json.JSONDecodeError:
            return

        code = result.get("code", -1)
        if code != 0:
            err_msg = result.get("message", f"错误码: {code}")
            self.error_occurred.emit(err_msg)
            return

        data = result.get("data", {})
        status = data.get("status", 0)
        text = self._extract_text(data)

        if status == 1:
            self.partial_result.emit(text)
        elif status == 2:
            self.final_result.emit(text)

    def _on_error(self, ws, error):
        self.error_occurred.emit(f"WebSocket 错误: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        self._running = False
        self.disconnected.emit()

    # --- 签名 & URL 构建 ---

    def _build_url(self) -> str:
        """构建带鉴权签名的 WebSocket URL"""
        now = datetime.datetime.now(datetime.timezone.utc)
        date_str = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

        # HMAC-SHA256 签名
        signature_origin = (
            f"host: {HOST}\n"
            f"date: {date_str}\n"
            f"GET {URI} HTTP/1.1"
        )
        signature = base64.b64encode(
            hmac.new(
                self._apisecret.encode("utf-8"),
                signature_origin.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        # authorization 头
        authorization_origin = (
            f'api_key="{self._apikey}",'
            f'algorithm="hmac-sha256",'
            f'headers="host date request-line",'
            f'signature="{signature}"'
        )
        authorization = base64.b64encode(
            authorization_origin.encode("utf-8")
        ).decode("utf-8")

        # 拼接 URL
        from urllib.parse import urlencode
        params = urlencode({
            "authorization": authorization,
            "date": date_str,
            "host": HOST,
        })
        return f"{IAT_URL}?{params}"

    def _extract_text(self, data: dict) -> str:
        """从返回数据中提取识别文本"""
        result = data.get("result", {})
        ws_list = result.get("ws", [])
        words = []
        for ws_item in ws_list:
            cw_list = ws_item.get("cw", [])
            for cw in cw_list:
                w = cw.get("w", "")
                if w:
                    words.append(w)
        return "".join(words)
