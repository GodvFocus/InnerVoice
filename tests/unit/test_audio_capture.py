"""AudioCapture 单元测试 (mock PyAudio)"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from PySide6.QtCore import QCoreApplication

_app = QCoreApplication.instance()
if _app is None:
    _app = QCoreApplication([])

from modules.asr.audio_capture import AudioCapture


class TestAudioCapture:
    """AudioCapture 测试 (mock PyAudio)"""

    @pytest.fixture
    def mock_pyaudio(self):
        with patch("modules.asr.audio_capture.pyaudio") as mock_pa:
            mock_stream = MagicMock()
            mock_stream.read.return_value = b"\x00" * 1280
            mock_stream.is_active.return_value = True
            mock_instance = MagicMock()
            mock_instance.open.return_value = mock_stream
            mock_pa.PyAudio.return_value = mock_instance
            yield mock_pa

    def test_start_stop(self, mock_pyaudio):
        cap = AudioCapture()
        ok = cap.start()
        assert ok is True
        assert cap.is_active is True
        cap.stop()
        assert cap.is_active is False

    def test_audio_chunk_emitted(self, mock_pyaudio):
        cap = AudioCapture()
        chunks = []
        cap.audio_chunk.connect(lambda data: chunks.append(data))
        cap.start()
        time.sleep(0.15)  # 等待几帧
        cap.stop()
        QCoreApplication.processEvents()  # 刷新跨线程信号队列
        assert len(chunks) > 0, f"未收到音频块, chunks={len(chunks)}"
        assert len(chunks[0]) == 1280

    def test_stop_when_not_active(self, mock_pyaudio):
        cap = AudioCapture()
        cap.stop()  # 不应抛异常

    def test_error_when_mic_fails(self):
        with patch("modules.asr.audio_capture.pyaudio") as mock_pa:
            mock_pa.PyAudio.side_effect = OSError("no mic")
            cap = AudioCapture()
            errors = []
            cap.error_occurred.connect(lambda msg: errors.append(msg))
            ok = cap.start()
            assert ok is False
            assert len(errors) == 1
            assert "麦克风打开失败" in errors[0]
