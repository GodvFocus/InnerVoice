"""润色风格管理页 + 编辑/新增弹窗"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox,
)

from modules.polish.prompt_manager import PromptManager

# ── 样式常量 ──────────────────────────────────────────────
BG_COLOR = "#1e1e2e"
TEXT_COLOR = "#cdd6f4"
SUB_TEXT_COLOR = "#a6adc4"
INPUT_BG = "#313244"
BORDER_COLOR = "#585b70"
BTN_CONFIRM_BG = "#cba6f7"
BTN_CONFIRM_TEXT = "#1e1e2e"
ROW_ALT_BG = "#252537"
BLUE_COLOR = "#89b4fa"
YELLOW_COLOR = "#f9e2af"
RED_COLOR = "#f38ba8"
GREEN_COLOR = "#a6e3a1"


def _button_style(bg: str, fg: str) -> str:
    return f"""
        QPushButton {{
            background: {bg};
            color: {fg};
            border: none;
            border-radius: 5px;
            padding: 5px 14px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            opacity: 0.85;
        }}
    """


class StyleDialog(QDialog):
    """新增 / 编辑风格的弹窗"""

    def __init__(self, title: str, name: str = "", prompt: str = "",
                 parent=None):
        super().__init__(parent)
        self._prefilled_name = name
        self.setWindowTitle(title)
        self.setFixedSize(500, 340)
        self._setup_ui()
        self._setup_style()
        if name:
            self._name_edit.setText(name)
        if prompt:
            self._prompt_edit.setPlainText(prompt)

    # ── UI 搭建 ──────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # 风格名称
        name_label = QLabel("风格名称")
        name_label.setFont(QFont("Microsoft YaHei", 10))
        name_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(name_label)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText(
            "例如：邮件、小红书、技术文档..."
        )
        self._name_edit.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(self._name_edit)

        # 系统提示词
        prompt_label = QLabel("系统提示词")
        prompt_label.setFont(QFont("Microsoft YaHei", 10))
        prompt_label.setStyleSheet(f"color: {TEXT_COLOR};")
        layout.addWidget(prompt_label)

        self._prompt_edit = QTextEdit()
        self._prompt_edit.setPlaceholderText(
            "输入润色时使用的系统提示词，例如："
            "\"你是一位专业的文案润色师，请将以下文本润色得更正式...\""
        )
        self._prompt_edit.setFont(QFont("Microsoft YaHei", 10))
        self._prompt_edit.setMinimumHeight(140)
        layout.addWidget(self._prompt_edit)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._cancel_btn)

        confirm_label = "保存" if self._prefilled_name else "新增"
        self._confirm_btn = QPushButton(confirm_label)
        self._confirm_btn.clicked.connect(self._on_confirm)
        self._confirm_btn.setDefault(True)
        btn_layout.addWidget(self._confirm_btn)

        layout.addLayout(btn_layout)

    def _setup_style(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_COLOR};
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QLineEdit {{
                background: {INPUT_BG};
                color: {TEXT_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QTextEdit {{
                background: {INPUT_BG};
                color: {TEXT_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 13px;
            }}
        """)
        self._cancel_btn.setStyleSheet(
            _button_style("transparent", SUB_TEXT_COLOR)
            + f"border: 1px solid {BORDER_COLOR};"
        )
        self._confirm_btn.setStyleSheet(
            _button_style(BTN_CONFIRM_BG, BTN_CONFIRM_TEXT)
        )

    # ── 验证与取值 ───────────────────────────────────────

    def _on_confirm(self):
        """确认前校验非空"""
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "提示", "风格名称不能为空")
            return
        if not self._prompt_edit.toPlainText().strip():
            QMessageBox.warning(self, "提示", "系统提示词不能为空")
            return
        self.accept()

    def style_name(self) -> str:
        return self._name_edit.text().strip()

    def style_prompt(self) -> str:
        return self._prompt_edit.toPlainText().strip()


class PolishPage(QWidget):
    """润色风格管理页面"""

    styles_changed = Signal()

    def __init__(self, manager: PromptManager, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._setup_ui()
        self._setup_style()
        self._refresh_table()

    # ── UI 搭建 ──────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # 标题行
        header_layout = QHBoxLayout()
        title_label = QLabel("润色风格管理")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet(f"color: {TEXT_COLOR};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self._add_btn = QPushButton("＋ 新增风格")
        self._add_btn.clicked.connect(self._on_add)
        header_layout.addWidget(self._add_btn)
        layout.addLayout(header_layout)

        # 表格
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "风格名称", "提示词", "默认", "操作"
        ])
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)

        # 列宽
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 100)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 50)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 120)

        layout.addWidget(self._table)

    def _setup_style(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_COLOR};
            }}
        """)
        self._add_btn.setStyleSheet(
            _button_style(BTN_CONFIRM_BG, BTN_CONFIRM_TEXT)
        )
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_COLOR};
                alternate-background-color: {ROW_ALT_BG};
                color: {TEXT_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                gridline-color: transparent;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 6px 8px;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {BG_COLOR};
                color: {SUB_TEXT_COLOR};
                border: none;
                border-bottom: 1px solid {BORDER_COLOR};
                padding: 6px 8px;
                font-size: 12px;
                font-weight: bold;
            }}
        """)

    # ── 操作 ─────────────────────────────────────────────

    def _on_add(self):
        dlg = StyleDialog("新增润色风格", parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._manager.add(dlg.style_name(), dlg.style_prompt())
            self._refresh_table()
            self.styles_changed.emit()

    def _on_edit(self, style: dict):
        dlg = StyleDialog(
            "编辑润色风格",
            name=style["name"],
            prompt=style["prompt"],
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._manager.update(
                style["id"], dlg.style_name(), dlg.style_prompt()
            )
            self._refresh_table()
            self.styles_changed.emit()

    def _on_delete(self, style: dict):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除风格「{style['name']}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._manager.delete(style["id"])
            self._refresh_table()
            self.styles_changed.emit()

    def _on_set_default(self, style: dict):
        self._manager.set_default(style["id"])
        self._refresh_table()
        self.styles_changed.emit()

    def _refresh_table(self):
        styles = self._manager.get_all()
        self._table.setRowCount(0)
        self._table.setRowCount(len(styles))

        for row, style in enumerate(styles):
            # 风格名称
            name_item = QTableWidgetItem(style["name"])
            name_item.setForeground(QColor(TEXT_COLOR))
            self._table.setItem(row, 0, name_item)

            # 提示词（截断）
            prompt_text = style["prompt"]
            if len(prompt_text) > 40:
                prompt_text = prompt_text[:40] + "..."
            prompt_item = QTableWidgetItem(prompt_text)
            prompt_item.setForeground(QColor(SUB_TEXT_COLOR))
            self._table.setItem(row, 1, prompt_item)

            # 默认标记
            default_item = QTableWidgetItem(
                "✓" if style["is_default"] else ""
            )
            if style["is_default"]:
                default_item.setForeground(QColor(GREEN_COLOR))
            self._table.setItem(row, 2, default_item)

            # 操作按钮容器
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(4)

            edit_btn = QPushButton("编辑")
            edit_btn.setStyleSheet(
                _button_style("transparent", BLUE_COLOR)
                + f"border: 1px solid {BLUE_COLOR};"
            )
            edit_btn.clicked.connect(
                lambda checked, s=style: self._on_edit(s)
            )
            actions_layout.addWidget(edit_btn)

            if not style["is_default"]:
                set_default_btn = QPushButton("设默认")
                set_default_btn.setStyleSheet(
                    _button_style("transparent", YELLOW_COLOR)
                    + f"border: 1px solid {YELLOW_COLOR};"
                )
                set_default_btn.clicked.connect(
                    lambda checked, s=style: self._on_set_default(s)
                )
                actions_layout.addWidget(set_default_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet(
                _button_style("transparent", RED_COLOR)
                + f"border: 1px solid {RED_COLOR};"
            )
            delete_btn.clicked.connect(
                lambda checked, s=style: self._on_delete(s)
            )
            actions_layout.addWidget(delete_btn)

            self._table.setCellWidget(row, 3, actions_widget)
            self._table.setRowHeight(row, 40)
