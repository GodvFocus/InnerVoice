"""主窗口 — 侧边导航 + 页面容器"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel,
    QSystemTrayIcon, QMenu, QApplication,
)
from PySide6.QtGui import QPixmap, QPainter, QColor

from ui.polish_page import PolishPage


class MainWindow(QMainWindow):
    """InnerVoice 桌面主窗口"""

    def __init__(self, prompt_manager, parent=None):
        super().__init__(parent)
        self._prompt_manager = prompt_manager
        self._setup_window()
        self._setup_ui()
        self._setup_tray()

    def _setup_window(self):
        self.setWindowTitle("InnerVoice")
        self.setFixedSize(700, 480)
        self.setStyleSheet("QMainWindow { background-color: #181825; }")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 侧边栏 ---
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet("background-color: #11111b;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 16, 0, 16)
        sidebar_layout.setSpacing(0)

        logo = QLabel("  InnerVoice")
        logo.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        logo.setStyleSheet("color: #cba6f7; padding: 0 16px 20px;")
        sidebar_layout.addWidget(logo)

        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet("""
            QListWidget {
                background: transparent; border: none;
                color: #a6adc4; font-size: 13px;
            }
            QListWidget::item {
                padding: 10px 16px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:selected {
                background-color: #1e1e2e;
                color: #89b4fa;
                border-left: 3px solid #89b4fa;
            }
            QListWidget::item:hover { color: #cdd6f4; }
        """)

        nav_items = [
            ("  ✏️  润色风格",),
            ("  ℹ️  关于",),
        ]
        for (label,) in nav_items:
            self._nav_list.addItem(QListWidgetItem(label))
        self._nav_list.setCurrentRow(0)
        sidebar_layout.addWidget(self._nav_list)
        sidebar_layout.addStretch()

        version_label = QLabel("  v1.0")
        version_label.setStyleSheet("color: #585b70; font-size: 11px; padding: 0 16px;")
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(sidebar)

        # --- 页面容器 ---
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background-color: #1e1e2e;")

        self._polish_page = PolishPage(self._prompt_manager)
        self._stack.addWidget(self._polish_page)

        about_page = QWidget()
        about_layout = QVBoxLayout(about_page)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label = QLabel(
            "InnerVoice v1.0\n\n"
            "轻量级语音输入法 — 说你所想，落笔生花\n\n"
            "Powered by PySide6 + DeepSeek"
        )
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label.setStyleSheet("color: #a6adc4; font-size: 13px; line-height: 1.8;")
        about_layout.addWidget(about_label)
        self._stack.addWidget(about_page)

        main_layout.addWidget(self._stack)
        self._nav_list.currentRowChanged.connect(self._stack.setCurrentIndex)

    def _setup_tray(self):
        # 程序化生成图标 (32x32 紫色圆角方块)
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#cba6f7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 4, 24, 24, 6, 6)
        painter.end()
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(QIcon(pixmap))
        self._tray.setToolTip("InnerVoice — 语音输入法")

        menu = QMenu()
        show_action = QAction("显示主窗口")
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("退出")
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _on_quit(self):
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def polish_page(self) -> PolishPage:
        return self._polish_page
