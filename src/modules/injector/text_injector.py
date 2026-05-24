"""文本注入 - 剪贴板 + Ctrl+V 注入到当前活动窗口"""

import time
import win32clipboard
import win32con
import keyboard


class TextInjector:
    """将文本通过剪贴板粘贴注入到当前活动窗口

    用法:
        TextInjector.inject("你好世界")
    """

    @staticmethod
    def inject(text: str) -> bool:
        """注入文本到当前活动窗口, 返回是否成功"""
        if not text:
            return False

        # 保存原始剪贴板内容
        original = TextInjector._get_clipboard()

        try:
            TextInjector._set_clipboard(text)
            keyboard.send("ctrl+v")
            time.sleep(0.05)
        finally:
            time.sleep(0.05)
            TextInjector._set_clipboard(original)
        return True

    @staticmethod
    def _get_clipboard() -> str | None:
        try:
            win32clipboard.OpenClipboard()
            try:
                return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except (TypeError, OSError):
                return ""
        except OSError:
            return ""
        finally:
            try:
                win32clipboard.CloseClipboard()
            except OSError:
                pass

    @staticmethod
    def _set_clipboard(text: str | None):
        if text is None:
            text = ""
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            if text:
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
        except OSError:
            pass
        finally:
            try:
                win32clipboard.CloseClipboard()
            except OSError:
                pass
