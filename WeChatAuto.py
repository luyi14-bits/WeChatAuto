import sys
import os
import json
import subprocess
import re
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import (
    Qt, QTimer, QProcess, pyqtSignal, QObject, QThread,
    QUrl, QSize,
)
from PyQt5.QtGui import QFont, QIcon, QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
    QFileDialog, QMessageBox, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QCheckBox, QSystemTrayIcon, QMenu, QAction, QComboBox,
    QStyle, QSizePolicy, QSplitter, QFrame,
)

CRON_REGEX = re.compile(
    r"^(\*|([0-5]?\d)) (\*|(1?\d|2[0-3])) (\*|([1-9]|[12]\d|3[01])) (\*|(1[0-2]|[1-9])) (\*|([0-6]))$"
)

APP_NAME = "WeChatAuto"
VERSION = "1.0.0"
AUTHOR = "WeChatAuto Contributors"


def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def app_data_path(filename: str = "") -> str:
    base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
    os.makedirs(base, exist_ok=True)
    if filename:
        return os.path.join(base, filename)
    return base


def discover_wechat_path() -> str:
    candidates = []

    strategy_1 = os.path.join(
        os.environ.get("SystemDrive", "C:"), "Program Files", "Tencent", "WeChat", "WeChat.exe"
    )
    candidates.append(strategy_1)

    strategy_2 = os.path.join(
        os.environ.get("SystemDrive", "C:"),
        "Program Files (x86)",
        "Tencent",
        "WeChat",
        "WeChat.exe",
    )
    candidates.append(strategy_2)

    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for subkey in (
                r"SOFTWARE\Tencent\WeChat",
                r"SOFTWARE\WOW6432Node\Tencent\WeChat",
            ):
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        path, _ = winreg.QueryValueEx(key, "InstallPath")
                        if path:
                            exe = os.path.join(path, "WeChat.exe")
                            if os.path.isfile(exe):
                                candidates.append(exe)
                except OSError:
                    pass
    except Exception:
        pass

    strategy_4 = shutil.which("WeChat.exe")
    if strategy_4:
        candidates.append(strategy_4)

    strategy_5 = r"C:\Program Files\Tencent\WeChat\WeChat.exe"
    if os.path.isfile(strategy_5):
        candidates.append(strategy_5)

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return ""


def gerontological_styles() -> str:
    return """
    QMainWindow {
        background-color: #f0fdf4;
    }
    QWidget {
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        font-size: 14px;
    }
    QLabel {
        color: #14532d;
        font-weight: bold;
    }
    QGroupBox {
        border: 2px solid #86efac;
        border-radius: 10px;
        margin-top: 14px;
        padding-top: 18px;
        font-weight: bold;
        color: #166534;
        background-color: #dcfce7;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: #166534;
    }
    QLineEdit, QTextEdit, QSpinBox, QComboBox {
        border: 2px solid #bbf7d0;
        border-radius: 6px;
        padding: 6px 10px;
        background-color: #ffffff;
        color: #14532d;
        font-size: 14px;
    }
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border-color: #22c55e;
        background-color: #f0fdf4;
    }
    QPushButton {
        background-color: #16a34a;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: bold;
        font-size: 15px;
        min-height: 20px;
    }
    QPushButton:hover {
        background-color: #15803d;
    }
    QPushButton:pressed {
        background-color: #166534;
    }
    QPushButton:disabled {
        background-color: #a7f3d0;
        color: #86efac;
    }
    QPushButton#deleteBtn {
        background-color: #dc2626;
    }
    QPushButton#deleteBtn:hover {
        background-color: #b91c1c;
    }
    QTabWidget::pane {
        border: 2px solid #86efac;
        border-radius: 8px;
        background-color: #f0fdf4;
    }
    QTabBar::tab {
        background-color: #dcfce7;
        color: #166534;
        padding: 10px 24px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 2px;
        font-weight: bold;
        font-size: 15px;
    }
    QTabBar::tab:selected {
        background-color: #22c55e;
        color: #ffffff;
    }
    QTabBar::tab:hover:!selected {
        background-color: #bbf7d0;
    }
    QTableWidget {
        border: 2px solid #bbf7d0;
        border-radius: 6px;
        gridline-color: #dcfce7;
        background-color: #ffffff;
        font-size: 14px;
    }
    QTableWidget::item {
        padding: 4px 8px;
    }
    QTableWidget::item:selected {
        background-color: #86efac;
        color: #14532d;
    }
    QHeaderView::section {
        background-color: #16a34a;
        color: #ffffff;
        padding: 6px 8px;
        border: none;
        font-weight: bold;
        font-size: 14px;
    }
    QCheckBox {
        color: #14532d;
        font-weight: bold;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #22c55e;
        border-radius: 4px;
        background-color: #ffffff;
    }
    QCheckBox::indicator:checked {
        background-color: #16a34a;
        border-color: #16a34a;
    }
    QScrollBar:vertical {
        border: none;
        background: #dcfce7;
        width: 12px;
        border-radius: 6px;
    }
    QScrollBar::handle:vertical {
        background: #22c55e;
        border-radius: 6px;
        min-height: 30px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """


@dataclass
class ScheduledTask:
    recipient: str = ""
    text: str = ""
    image: str = ""
    cron: str = ""
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(
            recipient=d.get("recipient", ""),
            text=d.get("text", ""),
            image=d.get("image", ""),
            cron=d.get("cron", ""),
            enabled=d.get("enabled", True),
            created_at=d.get("created_at", ""),
            last_run=d.get("last_run", ""),
        )


class SendWorker(QObject):
    finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)

    def __init__(self, recipient: str, text: str = "", image: str = ""):
        super().__init__()
        self.recipient = recipient
        self.text = text
        self.image = image
        self._process: Optional[QProcess] = None

    def run(self):
        script_path = resource_path("auto_test.py")
        args = ["-r", self.recipient]
        if self.text:
            args.extend(["-t", self.text])
        if self.image and os.path.isfile(self.image):
            args.extend(["-i", self.image])

        self._process = QProcess()
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)
        self._process.start(sys.executable, [script_path] + args)

    def _on_stdout(self):
        if self._process:
            data = self._process.readAllStandardOutput().data().decode(
                "utf-8", errors="replace"
            )
            for line in data.strip().splitlines():
                if line:
                    self.log_message.emit(line)

    def _on_finished(self, exit_code, exit_status):
        success = exit_code == 0 and exit_status == QProcess.NormalExit
        msg = "发送成功" if success else f"发送失败 (exit code: {exit_code})"
        self.finished.emit(success, msg)
        self._process = None

    def stop(self):
        if self._process and self._process.state() != QProcess.NotRunning:
            self._process.kill()
            self._process.waitForFinished(3000)


class WeChatAutomator:
    def __init__(self, wechat_path: str):
        self.wechat_path = wechat_path

    def ensure_wechat_running(self):
        if not self.wechat_path or not os.path.isfile(self.wechat_path):
            return False
        import ctypes
        from ctypes import wintypes

        hwnd = ctypes.windll.user32.FindWindowW(None, "微信")
        if hwnd:
            SW_SHOW = 5
            SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return True
        try:
            subprocess.Popen(
                [self.wechat_path],
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )
            return True
        except Exception:
            return False

    def send_message(
        self, recipient: str, text: str = "", image: str = ""
    ) -> bool:
        script_path = resource_path("auto_test.py")
        args = [sys.executable, script_path, "-r", recipient]
        if text:
            args.extend(["-t", text])
        if image and os.path.isfile(image):
            args.extend(["-i", image])

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False


class WeChatAutomationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        icon_path = resource_path("wechat.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.settings_file = app_data_path("settings.json")
        self.tasks_file = app_data_path("tasks.json")

        self.wechat_path: str = ""
        self.tasks: list[ScheduledTask] = []
        self._worker: Optional[SendWorker] = None
        self._scheduler_timer: Optional[QTimer] = None

        self._load_settings()
        self._load_tasks()

        self._init_ui()
        self._start_scheduler()
        self._init_tray()

        QTimer.singleShot(100, self._ensure_wechat)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        header = QLabel(
            f'<h2 style="color:#166534;margin:0;">{APP_NAME}</h2>'
            f'<p style="color:#15803d;margin:4px 0 0 0;">Windows 微信自动发送工具 v{VERSION}</p>'
        )
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self._build_instant_tab()
        self._build_schedule_tab()
        self._build_settings_tab()

        self.status_bar = QLabel("就绪")
        self.status_bar.setStyleSheet(
            "color:#14532d;padding:4px 8px;background:#dcfce7;border-radius:4px;font-size:13px;"
        )
        main_layout.addWidget(self.status_bar)

        self.resize(900, 680)

    def _build_instant_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        group = QGroupBox("即时发送消息")
        form = QFormLayout(group)
        form.setSpacing(8)

        self.instant_recipient = QLineEdit()
        self.instant_recipient.setPlaceholderText("输入联系人名称或群名")
        form.addRow("联系人:", self.instant_recipient)

        self.instant_text = QTextEdit()
        self.instant_text.setPlaceholderText("输入要发送的文字消息（可选）")
        self.instant_text.setMaximumHeight(120)
        form.addRow("消息:", self.instant_text)

        image_row = QHBoxLayout()
        self.instant_image = QLineEdit()
        self.instant_image.setPlaceholderText("选择图片文件（可选）")
        self.instant_image.setReadOnly(True)
        image_row.addWidget(self.instant_image)
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_instant_image)
        image_row.addWidget(browse_btn)
        form.addRow("图片:", image_row)

        layout.addWidget(group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.send_btn = QPushButton("立即发送")
        self.send_btn.setMinimumWidth(140)
        self.send_btn.setMinimumHeight(42)
        self.send_btn.clicked.connect(self._on_send_instant)
        btn_row.addWidget(self.send_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.instant_log = QTextEdit()
        self.instant_log.setReadOnly(True)
        self.instant_log.setMaximumHeight(120)
        self.instant_log.setPlaceholderText("发送日志...")
        layout.addWidget(self.instant_log)

        layout.addStretch()
        self.tabs.addTab(tab, "即时发送")

    def _build_schedule_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        group = QGroupBox("添加定时任务")
        form = QFormLayout(group)
        form.setSpacing(8)

        self.sched_recipient = QLineEdit()
        self.sched_recipient.setPlaceholderText("输入联系人名称或群名")
        form.addRow("联系人:", self.sched_recipient)

        self.sched_text = QTextEdit()
        self.sched_text.setPlaceholderText("定时发送的文字消息（可选）")
        self.sched_text.setMaximumHeight(100)
        form.addRow("消息:", self.sched_text)

        image_row = QHBoxLayout()
        self.sched_image = QLineEdit()
        self.sched_image.setPlaceholderText("选择图片文件（可选）")
        self.sched_image.setReadOnly(True)
        image_row.addWidget(self.sched_image)
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_sched_image)
        image_row.addWidget(browse_btn)
        form.addRow("图片:", image_row)

        cron_row = QHBoxLayout()
        self.sched_cron = QLineEdit()
        self.sched_cron.setPlaceholderText("例如: 0 8 * * * （每天8:00）")
        self.sched_cron.setToolTip(
            "5字段cron表达式: 分 时 日 月 星期\n"
            "示例: 0 8 * * * 每天8:00\n"
            "30 12 * * 1-5 工作日12:30"
        )
        cron_row.addWidget(self.sched_cron)
        layout.addWidget(group)

        add_btn = QPushButton("添加任务")
        add_btn.setMinimumHeight(38)
        add_btn.clicked.connect(self._on_add_task)
        cron_row.addWidget(add_btn)
        form.addRow("Cron:", cron_row)

        layout.addWidget(group)

        task_group = QGroupBox("任务列表")
        task_layout = QVBoxLayout(task_group)

        self.task_table = QTableWidget(0, 6)
        self.task_table.setHorizontalHeaderLabels(
            ["联系人", "消息", "Cron", "启用", "上次执行", "操作"]
        )
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        task_layout.addWidget(self.task_table)

        layout.addWidget(task_group)

        self._refresh_task_table()
        self.tabs.addTab(tab, "定时发送")

    def _build_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        group = QGroupBox("微信路径设置")
        form = QFormLayout(group)
        form.setSpacing(8)

        path_row = QHBoxLayout()
        self.wechat_path_edit = QLineEdit()
        self.wechat_path_edit.setText(self.wechat_path)
        self.wechat_path_edit.setPlaceholderText("微信安装路径（WeChat.exe）")
        path_row.addWidget(self.wechat_path_edit)
        browse_btn = QPushButton("浏览")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_wechat_path)
        path_row.addWidget(browse_btn)
        form.addRow("路径:", path_row)

        detect_row = QHBoxLayout()
        detect_btn = QPushButton("自动发现")
        detect_btn.clicked.connect(self._on_detect_wechat)
        detect_row.addWidget(detect_btn)

        self.wechat_status = QLabel("")
        self.wechat_status.setStyleSheet("color:#166534;font-weight:normal;")
        detect_row.addWidget(self.wechat_status)
        detect_row.addStretch()
        form.addRow("", detect_row)

        layout.addWidget(group)

        save_btn = QPushButton("保存设置")
        save_btn.setMinimumHeight(38)
        save_btn.clicked.connect(self._on_save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()
        self.tabs.addTab(tab, "设置")

    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = resource_path("wechat.ico")
        icon = QIcon(icon_path) if os.path.isfile(icon_path) else self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def _browse_instant_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.instant_image.setText(path)

    def _browse_sched_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if path:
            self.sched_image.setText(path)

    def _browse_wechat_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择微信程序", "", "Executable (*.exe)"
        )
        if path:
            self.wechat_path_edit.setText(path)

    def _on_detect_wechat(self):
        path = discover_wechat_path()
        if path:
            self.wechat_path_edit.setText(path)
            self.wechat_status.setText("已自动发现微信路径 ✓")
            self.wechat_status.setStyleSheet("color:#16a34a;font-weight:normal;")
        else:
            self.wechat_status.setText("未找到微信，请手动选择")
            self.wechat_status.setStyleSheet("color:#dc2626;font-weight:normal;")

    def _on_save_settings(self):
        self.wechat_path = self.wechat_path_edit.text().strip()
        self._save_settings()
        QMessageBox.information(self, "保存成功", "设置已保存。")

    def _load_settings(self):
        try:
            if os.path.isfile(self.settings_file):
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.wechat_path = data.get("wechat_path", "")
            else:
                self.wechat_path = discover_wechat_path()
                self._save_settings()
        except Exception:
            self.wechat_path = discover_wechat_path()

    def _save_settings(self):
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump({"wechat_path": self.wechat_path}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_tasks(self):
        try:
            if os.path.isfile(self.tasks_file):
                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.tasks = [
                    ScheduledTask.from_dict(t) for t in data.get("tasks", [])
                ]
        except Exception:
            self.tasks = []

    def _save_tasks(self):
        try:
            with open(self.tasks_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"tasks": [t.to_dict() for t in self.tasks]},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass

    def _ensure_wechat(self):
        if self.wechat_path:
            automator = WeChatAutomator(self.wechat_path)
            automator.ensure_wechat_running()

    def _on_send_instant(self):
        recipient = self.instant_recipient.text().strip()
        text = self.instant_text.toPlainText().strip()
        image = self.instant_image.text().strip()

        if not recipient:
            QMessageBox.warning(self, "参数错误", "请输入联系人名称。")
            return
        if not text and not image:
            QMessageBox.warning(self, "参数错误", "请输入消息文本或选择图片。")
            return
        if image and not os.path.isfile(image):
            QMessageBox.warning(self, "参数错误", f"图片文件不存在: {image}")
            return

        if self._worker is not None:
            QMessageBox.warning(self, "正在发送", "当前有消息正在发送中，请稍候。")
            return

        self.send_btn.setEnabled(False)
        self.status_bar.setText("正在发送...")
        self.instant_log.clear()

        self._worker = SendWorker(recipient, text, image)
        self._worker.log_message.connect(self._on_worker_log)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.run()

    def _on_worker_log(self, msg: str):
        self.instant_log.append(msg)

    def _on_worker_finished(self, success: bool, msg: str):
        self.instant_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        self.status_bar.setText("就绪" if success else msg)
        self.send_btn.setEnabled(True)
        self._worker = None

    def _on_add_task(self):
        recipient = self.sched_recipient.text().strip()
        text = self.sched_text.toPlainText().strip()
        image = self.sched_image.text().strip()
        cron = self.sched_cron.text().strip()

        if not recipient:
            QMessageBox.warning(self, "参数错误", "请输入联系人名称。")
            return
        if not text and not image:
            QMessageBox.warning(self, "参数错误", "请输入消息文本或选择图片。")
            return
        if not CRON_REGEX.match(cron):
            QMessageBox.warning(
                self,
                "Cron格式错误",
                "请输入有效的5字段cron表达式。\n示例: 0 8 * * * （每天8:00）",
            )
            return

        task = ScheduledTask(
            recipient=recipient,
            text=text,
            image=image,
            cron=cron,
        )
        self.tasks.append(task)
        self._save_tasks()
        self._refresh_task_table()

        self.sched_recipient.clear()
        self.sched_text.clear()
        self.sched_image.clear()
        self.sched_cron.clear()

    def _refresh_task_table(self):
        self.task_table.setRowCount(len(self.tasks))
        for i, task in enumerate(self.tasks):
            self.task_table.setItem(i, 0, QTableWidgetItem(task.recipient))
            self.task_table.setItem(i, 1, QTableWidgetItem(task.text[:50]))
            self.task_table.setItem(i, 2, QTableWidgetItem(task.cron))

            chk = QCheckBox()
            chk.setChecked(task.enabled)
            chk.stateChanged.connect(lambda state, idx=i: self._on_task_toggle(idx, state))
            self.task_table.setCellWidget(i, 3, chk)

            last_run = task.last_run[:16] if task.last_run else "从未"
            self.task_table.setItem(i, 4, QTableWidgetItem(last_run))

            del_btn = QPushButton("删除")
            del_btn.setObjectName("deleteBtn")
            del_btn.setFixedSize(60, 28)
            font = del_btn.font()
            font.setPointSize(11)
            del_btn.setFont(font)
            del_btn.clicked.connect(lambda checked, idx=i: self._on_delete_task(idx))
            self.task_table.setCellWidget(i, 5, del_btn)

        self.task_table.resizeRowsToContents()

    def _on_task_toggle(self, idx: int, state):
        if 0 <= idx < len(self.tasks):
            self.tasks[idx].enabled = bool(state)
            self._save_tasks()

    def _on_delete_task(self, idx: int):
        if 0 <= idx < len(self.tasks):
            del self.tasks[idx]
            self._save_tasks()
            self._refresh_task_table()

    def _start_scheduler(self):
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.setInterval(30_000)
        self._scheduler_timer.timeout.connect(self._tick_scheduler)
        self._scheduler_timer.start()

    def _tick_scheduler(self):
        now = datetime.now()
        for task in self.tasks:
            if not task.enabled:
                continue
            if not cron_matches(task.cron, now):
                continue
            if self._worker is not None:
                continue

            if not self.wechat_path:
                continue

            self.status_bar.setText(f"正在执行定时任务: 发送给 {task.recipient}...")

            self._worker = SendWorker(task.recipient, task.text, task.image)
            self._worker.finished.connect(
                lambda success, msg, t=task: self._on_scheduled_finished(t, success, msg)
            )
            self._worker.run()

    def _on_scheduled_finished(self, task: ScheduledTask, success: bool, msg: str):
        task.last_run = datetime.now().isoformat()
        self._save_tasks()
        self._refresh_task_table()
        self.status_bar.setText("就绪")
        self._worker = None

    def _quit_app(self):
        if self._scheduler_timer:
            self._scheduler_timer.stop()
        if self._worker:
            self._worker.stop()
        self._save_settings()
        self._save_tasks()
        QApplication.quit()

    def closeEvent(self, event):
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                APP_NAME, "程序已最小化到系统托盘", QSystemTrayIcon.Information, 2000
            )
            event.ignore()
        else:
            self._quit_app()


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
        minute, hour, day, month, dow = parts
        fields = {
            "minute": (minute, dt.minute),
            "hour": (hour, dt.hour),
            "day": (day, dt.day),
            "month": (month, dt.month),
            "dow": (dow, (dt.weekday() + 1) % 7),
        }
        for name, (pattern, value) in fields.items():
            if pattern == "*":
                continue
            options = set()
            for part in pattern.split(","):
                part = part.strip()
                if "-" in part and "/" in part:
                    rng, step = part.split("/")
                    lo, hi = rng.split("-")
                    options.update(range(int(lo), int(hi) + 1, int(step)))
                elif "-" in part:
                    lo, hi = part.split("-")
                    options.update(range(int(lo), int(hi) + 1))
                elif "/" in part:
                    base, step = part.split("/")
                    if base == "*":
                        lo, hi = 0, 59
                    else:
                        lo = int(base)
                        hi = 59
                    options.update(range(lo, hi + 1, int(step)))
                else:
                    options.add(int(part))
            if value not in options:
                return False
        return True
    except Exception:
        return False


def cli_send(args):
    if not args.recipient:
        print("ERROR: --recipient is required")
        sys.exit(1)
    if not args.text and not args.image:
        print("ERROR: At least one of --text or --image must be provided")
        sys.exit(1)

    wechat_path = discover_wechat_path()
    if not wechat_path:
        print("ERROR: WeChat.exe not found. Please install WeChat first.")
        sys.exit(1)

    automator = WeChatAutomator(wechat_path)
    automator.ensure_wechat_running()

    import time
    time.sleep(2)

    success = automator.send_message(args.recipient, args.text or "", args.image or "")
    if success:
        print("OK: Message sent successfully")
    else:
        print("FAIL: Message send failed")
        sys.exit(1)


def main():
    if "--send" in sys.argv:
        sys.argv.remove("--send")
        import argparse as cli_argparse

        parser = cli_argparse.ArgumentParser(
            description="WeChatAuto CLI — send WeChat messages from command line"
        )
        parser.add_argument("--recipient", "-r", default="", help="Target contact name")
        parser.add_argument("--text", "-t", default="", help="Text message")
        parser.add_argument("--image", "-i", default="", help="Image file path")
        args = parser.parse_args()
        cli_send(args)
        return

    app = QApplication(sys.argv)
    app.setStyleSheet(gerontological_styles())
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(AUTHOR)

    icon_path = resource_path("wechat.ico")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = WeChatAutomationApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
