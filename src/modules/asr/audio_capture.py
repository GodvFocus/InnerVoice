"""音频采集 - PyAudio 麦克风流式读取 PCM 数据"""

import threading
import pyaudio

from PySide6.QtCore import QObject, Signal


class AudioCapture(QObject):
    """从麦克风捕获 PCM 音频流, 每 40ms 发射一帧

    用法:
        cap = AudioCapture()
        cap.audio_chunk.connect(on_audio)
        cap.error_occurred.connect(on_error)
        cap.start()  # 开始录音
        cap.stop()   # 停止录音
    """

    audio_chunk = Signal(bytes)   # 1280 字节 PCM 数据
    error_occurred = Signal(str)  # 错误描述

    RATE = 16000
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    CHUNK = 640         # 40ms @ 16kHz = 640 frames = 1280 bytes
    CHUNK_BYTES = 1280

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pa: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def is_active(self) -> bool:
        return self._running

    def start(self) -> bool:
        """打开麦克风并启动读取线程, 返回是否成功"""
        if self._running:
            return True
        try:
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )
        except OSError as e:
            self.error_occurred.emit(f"麦克风打开失败: {e}")
            self._cleanup_pa()
            return False

        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """停止录音并释放资源"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._cleanup_stream()
        self._cleanup_pa()

    def _read_loop(self):
        """后台线程: 循环读取 PCM 数据并发射信号"""
        while self._running:
            try:
                data = self._stream.read(self.CHUNK, exception_on_overflow=False)
                self.audio_chunk.emit(data)
            except OSError as e:
                if self._running:
                    self.error_occurred.emit(f"录音错误: {e}")
                break

    def _cleanup_stream(self):
        if self._stream:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
            except OSError:
                pass
            self._stream = None

    def _cleanup_pa(self):
        if self._pa:
            self._pa.terminate()
            self._pa = None
