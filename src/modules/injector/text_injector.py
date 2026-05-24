"""文本注入 - 恢复目标窗口焦点后使用剪贴板 + Ctrl+V 粘贴"""

import time

import keyboard
import win32clipboard
import win32con
import win32gui


class TextInjector:
    """将文本注入到目标输入窗口。"""

    @staticmethod
    def inject(text: str) -> bool:
        """注入到当前前台窗口。"""
        return TextInjector.inject_to_window(text, None)

    @staticmethod
    def inject_to_window(text: str, target_window: int | None) -> bool:
        """先恢复目标窗口焦点，再通过剪贴板 + Ctrl+V 注入文本。"""
        if not text:
            return False

        original = TextInjector._get_clipboard()

        try:
            if target_window:
                TextInjector._activate_window(target_window)
                time.sleep(0.05)

            TextInjector._set_clipboard(text)
            keyboard.send("ctrl+v")
            time.sleep(0.05)
        finally:
            time.sleep(0.05)
            TextInjector._set_clipboard(original)

        return True

    @staticmethod
    def current_window() -> int | None:
        """获取当前前台窗口句柄。"""
        try:
            hwnd = win32gui.GetForegroundWindow()
        except Exception:
            return None
        return hwnd or None

    @staticmethod
    def _activate_window(hwnd: int):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

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
