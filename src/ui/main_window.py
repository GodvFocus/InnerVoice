"""Main application window with a custom title bar."""

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ui.polish_page import PolishPage


class _TitleBar(QWidget):
    """Custom title bar with manual drag support."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._window = window
        self._drag_pos = None
        self.setFixedHeight(46)
        self.setObjectName("titleBar")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self._window.isMaximized():
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QPushButton):
                super().mousePressEvent(event)
                return
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self._window.move(self._window.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QPushButton):
                super().mouseDoubleClickEvent(event)
                return
            self._window._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class _ResizeEventFilter(QObject):
    """Handle resize hit testing even when the mouse is over child widgets."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self._window = window

    def eventFilter(self, watched, event):
        if self._window.isMaximized():
            return False

        if event.type() == QEvent.Type.MouseMove and hasattr(event, "globalPosition"):
            global_pos = event.globalPosition().toPoint()
            if not self._window._point_in_title_bar(global_pos):
                self._window._update_cursor_from_global(global_pos)
        elif (
            event.type() == QEvent.Type.MouseButtonPress
            and hasattr(event, "globalPosition")
            and event.button() == Qt.MouseButton.LeftButton
        ):
            global_pos = event.globalPosition().toPoint()
            if self._window._point_in_title_bar(global_pos):
                return False
            edges = self._window._hit_test_resize_edges_from_global(global_pos)
            if edges != Qt.Edge(0):
                handle = self._window.windowHandle()
                if handle is not None:
                    handle.startSystemResize(edges)
                    return True
        elif event.type() == QEvent.Type.Leave:
            self._window.unsetCursor()
        return False


class MainWindow(QMainWindow):
    """InnerVoice desktop main window."""

    def __init__(self, prompt_manager, parent=None, app_icon: QIcon | None = None):
        super().__init__(parent)
        self._prompt_manager = prompt_manager
        self._app_icon = app_icon or QIcon()
        self._resize_margin = 8
        self._resize_filter = _ResizeEventFilter(self)
        self._setup_window()
        self._setup_ui()
        self._setup_tray()

    def _setup_window(self):
        self.setWindowTitle("Flow")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setMinimumSize(920, 620)
        self.resize(1120, 760)
        self.setStyleSheet("QMainWindow { background-color: #181825; }")
        if not self._app_icon.isNull():
            self.setWindowIcon(self._app_icon)
        self.installEventFilter(self._resize_filter)
        QApplication.instance().installEventFilter(self._resize_filter)

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("windowRoot")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._title_bar = _TitleBar(self)
        root_layout.addWidget(self._title_bar)
        self._setup_title_bar()

        body = QWidget()
        body.setObjectName("windowBody")
        main_layout = QHBoxLayout(body)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 18, 0, 16)
        sidebar_layout.setSpacing(0)

        logo = QLabel("  心流")
        logo.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        logo.setStyleSheet("color: #cba6f7; padding: 0 18px 22px;")
        sidebar_layout.addWidget(logo)

        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet(
            """
            QListWidget {
                background: transparent;
                border: none;
                color: #a6adc4;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                padding: 14px 18px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #1e1e2e;
                color: #89b4fa;
                border: none;
                outline: none;
            }
            QListWidget::item:hover {
                color: #cdd6f4;
            }
        """
        )

        for label in ("  Pencil  润色风格", "  About  关于"):
            self._nav_list.addItem(QListWidgetItem(label))
        self._nav_list.setCurrentRow(0)
        sidebar_layout.addWidget(self._nav_list)
        sidebar_layout.addStretch()

        version_label = QLabel("  v1.0")
        version_label.setStyleSheet("color: #585b70; font-size: 11px; padding: 0 18px;")
        sidebar_layout.addWidget(version_label)
        main_layout.addWidget(sidebar)

        self._stack = QStackedWidget()
        self._stack.setObjectName("pageStack")
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._polish_page = PolishPage(self._prompt_manager)
        self._stack.addWidget(self._polish_page)

        about_page = QWidget()
        about_layout = QVBoxLayout(about_page)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label = QLabel(
            "InnerVoice v1.0\n\n"
            "心流语音输入法，所见即心声\n\n"
            "Powered by PySide6 + DeepSeek"
        )
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_label.setStyleSheet("color: #a6adc4; font-size: 13px; line-height: 1.8;")
        about_layout.addWidget(about_label)
        self._stack.addWidget(about_page)

        main_layout.addWidget(self._stack)
        root_layout.addWidget(body)

        self._nav_list.currentRowChanged.connect(self._stack.setCurrentIndex)

        central.setStyleSheet(
            """
            QWidget#windowRoot {
                background-color: #181825;
            }
            QWidget#windowBody {
                background-color: #181825;
            }
            QWidget#titleBar {
                background-color: #181825;
                border-bottom: 1px solid #313244;
            }
            QWidget#sidebar {
                background-color: #11111b;
            }
            QStackedWidget#pageStack {
                background-color: #1e1e2e;
                border: none;
            }
        """
        )

    def _setup_title_bar(self):
        layout = QHBoxLayout(self._title_bar)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(10)

        icon_label = QLabel()
        if not self._app_icon.isNull():
            icon_label.setPixmap(self._app_icon.pixmap(18, 18))
        icon_label.setFixedSize(20, 20)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        title_label = QLabel("Flow")
        title_label.setStyleSheet("color: #e6e9f5; font-size: 13px;")
        layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()

        self._min_button = self._build_title_button("min", "最小化")
        self._min_button.clicked.connect(self.showMinimized)
        layout.addWidget(self._min_button)

        self._max_button = self._build_title_button("max", "最大化")
        self._max_button.clicked.connect(self._toggle_maximize)
        layout.addWidget(self._max_button)

        self._close_button = self._build_title_button("close", "关闭", danger=True)
        self._close_button.clicked.connect(self.close)
        layout.addWidget(self._close_button)

    def _build_title_button(self, kind: str, tooltip: str, danger: bool = False) -> QPushButton:
        button = QPushButton()
        button.setFixedSize(44, 32)
        button.setIcon(self._create_title_icon(kind))
        button.setIconSize(QSize(14, 14))
        button.setToolTip(tooltip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {"#f38ba8" if danger else "#313244"};
            }}
        """
        )
        return button

    def _create_title_icon(self, kind: str) -> QIcon:
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#e6e9f5"))
        pen.setWidth(2)
        painter.setPen(pen)
        if kind == "min":
            painter.drawLine(3, 10, 11, 10)
        elif kind == "max":
            painter.drawRect(3, 3, 8, 8)
        elif kind == "restore":
            painter.drawRect(5, 3, 6, 6)
            painter.drawLine(3, 5, 3, 11)
            painter.drawLine(3, 11, 9, 11)
            painter.drawLine(9, 11, 9, 9)
        else:
            painter.drawLine(3, 3, 11, 11)
            painter.drawLine(11, 3, 3, 11)
        painter.end()
        return QIcon(pixmap)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_maximize_button()

    def _sync_maximize_button(self):
        kind = "restore" if self.isMaximized() else "max"
        self._max_button.setIcon(self._create_title_icon(kind))
        self._max_button.setToolTip("还原" if self.isMaximized() else "最大化")

    def _setup_tray(self):
        self._tray = QSystemTrayIcon()
        if not self._app_icon.isNull():
            self._tray.setIcon(self._app_icon)
        self._tray.setToolTip("Flow - 语音输入法")

        menu = QMenu()
        show_action = QAction("显示主窗口")
        show_action.triggered.connect(self.showNormal)
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
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _on_quit(self):
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_maximize_button()
        super().changeEvent(event)

    def _point_in_title_bar(self, global_pos: QPoint) -> bool:
        local_pos = self._title_bar.mapFromGlobal(global_pos)
        return self._title_bar.rect().contains(local_pos)

    def _hit_test_resize_edges_from_global(self, global_pos: QPoint) -> Qt.Edge:
        pos = self.mapFromGlobal(global_pos)
        rect = self.rect()
        margin = self._resize_margin
        if not rect.adjusted(margin, margin, -margin, -margin).contains(pos):
            edges = Qt.Edge(0)
            if pos.x() < margin:
                edges |= Qt.Edge.LeftEdge
            elif pos.x() >= rect.width() - margin:
                edges |= Qt.Edge.RightEdge
            if pos.y() < margin:
                edges |= Qt.Edge.TopEdge
            elif pos.y() >= rect.height() - margin:
                edges |= Qt.Edge.BottomEdge
            return edges
        return Qt.Edge(0)

    def _update_cursor_from_global(self, global_pos: QPoint):
        if not self.isVisible() or self.isMaximized():
            self.unsetCursor()
            return

        window_rect = self.frameGeometry()
        expanded = QRect(
            window_rect.left() - self._resize_margin,
            window_rect.top() - self._resize_margin,
            window_rect.width() + self._resize_margin * 2,
            window_rect.height() + self._resize_margin * 2,
        )
        if not expanded.contains(global_pos):
            self.unsetCursor()
            return

        edges = self._hit_test_resize_edges_from_global(global_pos)
        if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edges in (
            Qt.Edge.LeftEdge | Qt.Edge.TopEdge,
            Qt.Edge.RightEdge | Qt.Edge.BottomEdge,
        ):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edges in (
            Qt.Edge.RightEdge | Qt.Edge.TopEdge,
            Qt.Edge.LeftEdge | Qt.Edge.BottomEdge,
        ):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.unsetCursor()

    def polish_page(self) -> PolishPage:
        return self._polish_page
