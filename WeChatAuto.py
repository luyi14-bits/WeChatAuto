# -*- coding:utf-8 -*-
import sys
import os
import json
import psutil
import time
from datetime import datetime, timedelta
import winreg
import uiautomation as auto

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QLabel, QLineEdit, QTextEdit, QPushButton,
                             QFileDialog, QMessageBox, QStatusBar, QGroupBox,
                             QDateTimeEdit, QCheckBox, QSpinBox, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer, QUrl, QMimeData, QProcess
from PyQt5.QtGui import QIcon, QFont


# ==========================================
# 1. 环境寻址与资源管理模块
# ==========================================
def resource_path(relative_path):
    """
    动态解析资源绝对路径。
    兼容本地开发环境与 PyInstaller --onefile 释放的 _MEIPASS 临时目录。
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def discover_wechat_path():
    """
    多策略自动发现微信安装路径（零配置，长辈友好）：
    策略1: 正在运行的微信进程 → 策略2: 注册表 → 策略3: 开始菜单快捷键 →
    策略4: 多盘符常见路径 → 策略5: 系统PATH搜索
    返回 str，找不到返回 ""
    """
    found_path = ""

    # —— 策略1: 检查正在运行的微信进程（最快最准） ——
    for pid in psutil.pids():
        try:
            proc = psutil.Process(pid)
            if proc.name().lower() == 'wechat.exe':
                path = proc.exe()
                if os.path.exists(path):
                    return path
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # —— 策略2: 注册表扫描 ——
    registry_paths = [
        [winreg.HKEY_CURRENT_USER, "Software\\Tencent\\WeChat"],
        [winreg.HKEY_LOCAL_MACHINE, "Software\\Tencent\\WeChat"],
        [winreg.HKEY_LOCAL_MACHINE, "Software\\WOW6432Node\\Tencent\\WeChat"]
    ]
    for hkey, path in registry_paths:
        try:
            with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                try:
                    install_dir, _ = winreg.QueryValueEx(key, "InstallPath")
                    full_path = os.path.join(install_dir, "WeChat.exe")
                    if os.path.exists(full_path):
                        return full_path
                except OSError:
                    pass
        except OSError:
            continue

    # —— 策略3: 开始菜单快捷方式解析 ——
    try:
        from comtypes.client import CreateObject
        shell = CreateObject("WScript.Shell")
        start_roots = [
            os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
                        "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.environ.get("APPDATA", ""),
                        "Microsoft\\Windows\\Start Menu\\Programs"),
        ]
        for start_root in start_roots:
            if not os.path.exists(start_root):
                continue
            for root, dirs, files in os.walk(start_root):
                for f in files:
                    name_lower = f.lower()
                    if ('微信' in f or 'wechat' in name_lower) and f.endswith('.lnk'):
                        try:
                            shortcut = shell.CreateShortcut(os.path.join(root, f))
                            target = shortcut.TargetPath
                            if target and os.path.exists(target) and target.lower().endswith('wechat.exe'):
                                return target
                        except Exception:
                            pass
    except Exception:
        pass

    # —— 策略4: 多盘符常见安装路径扫描 ——
    drives = ['C:', 'D:', 'E:', 'F:']
    patterns = [
        'Program Files\\Tencent\\WeChat\\WeChat.exe',
        'Program Files (x86)\\Tencent\\WeChat\\WeChat.exe',
    ]
    for drive in drives:
        for p in patterns:
            full = os.path.join(drive, os.sep, p)
            if os.path.exists(full):
                return full

    # —— 策略5: 系统 PATH 搜索 ——
    try:
        import subprocess
        result = subprocess.run(
            ['where', 'WeChat.exe'],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0 and result.stdout.strip():
            first_path = result.stdout.strip().split('\n')[0].strip()
            if os.path.exists(first_path):
                return first_path
    except Exception:
        pass

    return ""


# ==========================================
# 2. 任务调度模块（QProcess 子进程，零线程）
# ==========================================
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class SendWorker(QObject):
    finished = pyqtSignal(str, bool)

    def __init__(self, recipient, message, file_path, parent=None):
        super().__init__(parent)
        self._recipient = recipient
        self._msg = message or ""
        self._file = file_path or ""
        self._proc = None

    def start(self):
        self._proc = QProcess()
        self._proc.finished.connect(self._on_done)
        script = os.path.join(_SCRIPT_DIR, "auto_test.py")
        self._proc.start(sys.executable, [script, self._recipient, self._msg, self._file])

    def _on_done(self, exit_code, exit_status):
        raw = bytes(self._proc.readAllStandardOutput()).decode('utf-8', errors='replace')
        lines = [l for l in raw.split('\n') if l.strip()]
        last = lines[-1] if lines else ""
        if exit_code == 0:
            self.finished.emit(last or f"发送完成 → {self._recipient}", True)
        else:
            self.finished.emit(last or "发送失败", False)
        self.deleteLater()


# ==========================================
# 3. 微信核心自动化引擎（基于 wxauto）
# ==========================================
class WeChatAutomator:
    def __init__(self, wechat_path):
        self.wechat_path = wechat_path

    def is_running(self):
        for pid in psutil.pids():
            try:
                proc_name = psutil.Process(pid).name().lower()
                if proc_name in ('wechat.exe', 'wechat'):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def execute_send_flow(self, target_name, text_msg, file_path=None):
        from wxauto import WeChat
        wx = WeChat()

        if text_msg:
            wx.SendMsg(text_msg, target_name)

        if file_path and os.path.exists(file_path):
            wx.SendFiles(file_path, target_name)

        return f"发送完成 → {target_name}"


class ScheduledTask:
    def __init__(self, task_id, recipient, message, file_path, send_time, repeat=False, interval=60):
        self.id = task_id
        self.recipient = recipient
        self.message = message
        self.file_path = file_path
        self.send_time = send_time
        self.repeat = repeat
        self.interval = interval
        self.status = "等待中"
        self.error_msg = ""

    def to_dict(self):
        return {
            "id": self.id,
            "recipient": self.recipient,
            "message": self.message,
            "file_path": self.file_path,
            "send_time": self.send_time.strftime("%Y-%m-%d %H:%M:%S"),
            "repeat": self.repeat,
            "interval": self.interval,
            "status": self.status,
            "error_msg": self.error_msg
        }

    @staticmethod
    def from_dict(d):
        task = ScheduledTask(
            task_id=d["id"],
            recipient=d["recipient"],
            message=d["message"],
            file_path=d["file_path"],
            send_time=datetime.strptime(d["send_time"], "%Y-%m-%d %H:%M:%S"),
            repeat=d.get("repeat", False),
            interval=d.get("interval", 60)
        )
        task.status = d.get("status", "等待中")
        task.error_msg = d.get("error_msg", "")
        return task


# ==========================================
# 4. 适老化 GUI 表现层与控制器
# ==========================================
class WeChatAutomationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("微信自动消息助手")
        self.setGeometry(100, 100, 980, 780)
        self.setWindowIcon(QIcon(resource_path("wechat.ico")))

        self.automator = WeChatAutomator(discover_wechat_path())
        self.scheduled_tasks = []
        self.next_task_id = 1
        self.sending_task_id = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_scheduled_tasks)
        self.timer.start(1000)

        self.setup_ui()
        self.apply_gerontological_styles()
        self.load_tasks()

    def apply_gerontological_styles(self):
        """
        注入经过人体工效学计算的 Qt 样式表 (QSS)。
        解决老年人视力退化与精细动作困难的痛点。
        """
        qss = """
        /* 提升全局字号至 15pt，采用深色文字搭配浅灰背景，提供大于 7:1 的对比度 */
        QWidget {
            font-family: "Microsoft YaHei", "Arial";
            font-size: 15pt;
            color: #212529;
            background-color: #F8F9FA;
        }
        /* 遵循菲茨定律，提供大面积、高对比度的操作按钮 */
        QPushButton {
            background-color: #198754; 
            color: #FFFFFF;
            border-radius: 8px;
            padding: 15px;
            min-width: 140px;
            min-height: 50px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #157347; }
        QPushButton:pressed { background-color: #146c43; }
        QPushButton:disabled { background-color: #CED4DA; color: #6C757D; }

        /* 增加输入框的内边距，提供清晰的视觉聚焦边界 */
        QLineEdit, QTextEdit, QDateTimeEdit, QSpinBox {
            border: 2px solid #ADB5BD;
            border-radius: 6px;
            padding: 12px;
            background-color: #FFFFFF;
            min-height: 40px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border: 3px solid #0D6EFD;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #DEE2E6;
            border-radius: 8px;
            margin-top: 25px;
            padding-top: 20px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 20px;
            padding: 0 10px;
        }
        /* 优化选项卡的外观，使其形似物理按钮 */
        QTabBar::tab {
            background-color: #E9ECEF;
            padding: 15px 30px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 5px;
            border: 1px solid #DEE2E6;
        }
        QTabBar::tab:selected {
            background-color: #FFFFFF;
            color: #0D6EFD;
            border-top: 4px solid #0D6EFD;
            border-bottom: none;
        }
        """
        self.setStyleSheet(qss)

    def setup_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.create_send_tab()
        self.create_schedule_tab()
        self.create_control_tab()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪，添加定时任务后到点自动发送消息和照片。")

    def create_send_tab(self):
        self.send_tab = QWidget()
        self.tabs.addTab(self.send_tab, "📸 即时发送")
        layout = QVBoxLayout(self.send_tab)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("要发送给谁："))
        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("请输入微信好友或群的准确名字")
        h1.addWidget(self.recipient_input)
        layout.addLayout(h1)

        layout.addWidget(QLabel("附加说明文字："))
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("如：这是自动发送的消息，一切正常")
        self.message_input.setMaximumHeight(100)
        layout.addWidget(self.message_input)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("选择照片："))
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_input.setPlaceholderText("尚未选择任何照片")
        h2.addWidget(self.file_input)

        self.browse_btn = QPushButton("浏览并选择...")
        self.browse_btn.clicked.connect(self.browse_file)
        h2.addWidget(self.browse_btn)
        layout.addLayout(h2)

        self.send_btn = QPushButton("🚀 立即发送")
        self.send_btn.clicked.connect(self.trigger_send)
        layout.addWidget(self.send_btn, alignment=Qt.AlignRight)
        layout.addStretch()

    def create_schedule_tab(self):
        self.schedule_tab = QWidget()
        self.tabs.addTab(self.schedule_tab, "⏰ 定时发送")
        layout = QVBoxLayout(self.schedule_tab)

        schedule_group = QGroupBox("新建定时任务")
        sg_layout = QVBoxLayout()

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("收件人："))
        self.sch_recipient_input = QLineEdit()
        self.sch_recipient_input.setPlaceholderText("请输入微信好友或群的准确名字")
        h1.addWidget(self.sch_recipient_input)
        sg_layout.addLayout(h1)

        sg_layout.addWidget(QLabel("消息内容："))
        self.sch_message_input = QTextEdit()
        self.sch_message_input.setPlaceholderText("输入要发送的消息...")
        self.sch_message_input.setMaximumHeight(80)
        sg_layout.addWidget(self.sch_message_input)

        h2 = QHBoxLayout()
        h2.addWidget(QLabel("附件文件："))
        self.sch_file_input = QLineEdit()
        self.sch_file_input.setReadOnly(True)
        self.sch_file_input.setPlaceholderText("尚未选择文件")
        h2.addWidget(self.sch_file_input)
        sch_browse_btn = QPushButton("浏览...")
        sch_browse_btn.clicked.connect(self.browse_schedule_file)
        h2.addWidget(sch_browse_btn)
        sg_layout.addLayout(h2)

        h3 = QHBoxLayout()
        h3.addWidget(QLabel("⏰ 发送时间："))
        self.sch_datetime_input = QDateTimeEdit()
        self.sch_datetime_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.sch_datetime_input.setDateTime(datetime.now())
        self.sch_datetime_input.setCalendarPopup(True)
        h3.addWidget(self.sch_datetime_input)

        self.sch_repeat_check = QCheckBox("重复发送")
        h3.addWidget(self.sch_repeat_check)

        self.sch_interval_spin = QSpinBox()
        self.sch_interval_spin.setRange(1, 1440)
        self.sch_interval_spin.setValue(60)
        self.sch_interval_spin.setSuffix(" 分钟")
        self.sch_interval_spin.setEnabled(False)
        self.sch_repeat_check.toggled.connect(self.sch_interval_spin.setEnabled)
        h3.addWidget(self.sch_interval_spin)
        h3.addStretch()
        sg_layout.addLayout(h3)

        add_task_btn = QPushButton("➕ 添加到任务队列")
        add_task_btn.clicked.connect(self.add_scheduled_task)
        sg_layout.addWidget(add_task_btn)
        sg_layout.addStretch()

        schedule_group.setLayout(sg_layout)
        layout.addWidget(schedule_group)

        task_group = QGroupBox("任务队列")
        tg_layout = QVBoxLayout()

        self.task_table = QTableWidget()
        self.task_table.setColumnCount(8)
        self.task_table.setHorizontalHeaderLabels(["序号", "发送时间", "收件人", "消息内容", "附件", "重复", "状态", "操作"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.setColumnWidth(0, 40)
        self.task_table.setColumnWidth(1, 130)
        self.task_table.setColumnWidth(2, 90)
        self.task_table.setColumnWidth(3, 130)
        self.task_table.setColumnWidth(4, 130)
        self.task_table.setColumnWidth(5, 70)
        self.task_table.setColumnWidth(6, 70)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        tg_layout.addWidget(self.task_table)

        clear_btn = QPushButton("🗑 清除已完成任务")
        clear_btn.clicked.connect(self.clear_completed_tasks)
        tg_layout.addWidget(clear_btn)

        task_group.setLayout(tg_layout)
        layout.addWidget(task_group)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "请选择要发送的照片或文件", "", "所有文件 (*.*)")
        if path:
            self.file_input.setText(path)

    def browse_schedule_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "请选择要发送的照片或文件", "", "所有文件 (*.*)")
        if path:
            self.sch_file_input.setText(path)

    def create_control_tab(self):
        self.control_tab = QWidget()
        self.tabs.addTab(self.control_tab, "⚙️ 系统设置")
        layout = QVBoxLayout(self.control_tab)

        h1 = QHBoxLayout()
        h1.addWidget(QLabel("微信安装位置："))
        self.path_input = QLineEdit(self.automator.wechat_path)
        self.path_input.setPlaceholderText("自动搜索中...若为空可手动输入微信路径")
        h1.addWidget(self.path_input)

        self.rescan_btn = QPushButton("🔍 重新搜索微信")
        self.rescan_btn.clicked.connect(self.refresh_wechat_path)
        h1.addWidget(self.rescan_btn)
        layout.addLayout(h1)

        if not self.automator.wechat_path:
            hint = QLabel("⚠ 未自动检测到微信，请确认微信已安装后点击「重新搜索微信」")
            hint.setStyleSheet("color: #DC3545; font-weight: bold; padding: 10px;")
            layout.addWidget(hint)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("系统运行日志："))
        layout.addWidget(self.log_output)

    def refresh_wechat_path(self):
        self.rescan_btn.setEnabled(False)
        self.log("正在自动搜索微信安装位置，请稍候...")
        new_path = discover_wechat_path()
        if new_path:
            self.automator.wechat_path = new_path
            self.path_input.setText(new_path)
            self.log(f"已找到微信 → {new_path}")
            QMessageBox.information(self, "搜索成功", f"已自动找到微信！\n位置：{new_path}")
        else:
            self.log("未能找到微信，请确认微信已安装")
            QMessageBox.warning(self, "未找到微信",
                "自动搜索也未能找到微信安装位置。\n\n"
                "请确认电脑上已安装了微信 PC 版。\n"
                "如果确定已安装，可以手动输入路径。")
        self.rescan_btn.setEnabled(True)

    def log(self, msg):
        time_str = datetime.now().strftime('%H:%M:%S')
        self.log_output.append(f"[{time_str}] {msg}")
        self.status_bar.showMessage(msg)

    def trigger_send(self):
        """ 收集参数，启动工作线程，防止主界面阻塞。 """
        recipient = self.recipient_input.text().strip()
        message = self.message_input.toPlainText().strip()
        file_path = self.file_input.text().strip()

        if not recipient:
            QMessageBox.warning(self, "操作提醒", "您必须填写要发送给谁！")
            return
        if not message and not file_path:
            QMessageBox.warning(self, "操作提醒", "您必须填写文字内容或选择一个文件！")
            return

        # 禁用按钮，防止多次重复触发导致系统逻辑混乱
        self.send_btn.setEnabled(False)
        self.log(f"正在准备向【{recipient}】发送消息...")

        self.worker = SendWorker(recipient, message, file_path, parent=self)
        self.worker.finished.connect(self.on_send_finished)
        self.worker.start()

    def on_send_finished(self, msg, success):
        self.send_btn.setEnabled(True)
        self.log(msg)
        if success:
            QMessageBox.information(self, "执行成功", f"消息已经成功发送！")
        else:
            QMessageBox.critical(self, "执行遇到问题",
                                 f"抱歉，发送未能完成。\n原因：{msg}\n请确保微信已经登录并在屏幕上可见。")

    def on_scheduled_send_finished(self, msg, success, task):
        if success:
            if task.repeat:
                task.send_time = datetime.now() + timedelta(minutes=task.interval)
                task.status = "等待中"
                next_str = task.send_time.strftime("%m月%d日 %H:%M:%S")
                self.log(f"定时任务#{task.id} 重复模式：发送成功，下次发送 {next_str}")
            else:
                task.status = "已发送"
                self.log(f"定时任务#{task.id} 发送成功 → {task.recipient}")
        else:
            task.status = "发送失败"
            task.error_msg = msg
            self.log(f"定时任务#{task.id} 发送失败: {msg}")
        self.sending_task_id = None
        self._sch_worker = None
        self.refresh_task_table()
        self.save_tasks()

    def check_scheduled_tasks(self):
        try:
            if self.sending_task_id is not None:
                return
            now = datetime.now()
            for task in self.scheduled_tasks:
                if task.status == "等待中" and task.send_time <= now:
                    if task.file_path and not os.path.exists(task.file_path):
                        task.status = "发送失败"
                        task.error_msg = f"文件不存在: {task.file_path}"
                        self.log(f"定时任务#{task.id} 失败: 文件不存在")
                        self.refresh_task_table()
                        self.save_tasks()
                        continue
                    if not task.message and not task.file_path:
                        task.status = "发送失败"
                        task.error_msg = "消息内容和文件均为空"
                        self.log(f"定时任务#{task.id} 失败: 无内容")
                        self.refresh_task_table()
                        self.save_tasks()
                        continue
                    task.status = "发送中"
                    self.sending_task_id = task.id
                    self.refresh_task_table()
                    self.log(f"定时任务#{task.id} 开始执行 → {task.recipient}")
                    self._sch_worker = SendWorker(task.recipient, task.message, task.file_path, parent=self)
                    self._sch_worker.finished.connect(lambda msg, ok, t=task: self.on_scheduled_send_finished(msg, ok, t))
                    self._sch_worker.start()
                    break
        except Exception as e:
            self.log(f"定时检查出错: {e}")

    def add_scheduled_task(self):
        try:
            recipient = self.sch_recipient_input.text().strip()
            message = self.sch_message_input.toPlainText().strip()
            file_path = self.sch_file_input.text().strip()

            if not recipient:
                QMessageBox.warning(self, "操作提醒", "您必须填写要发送给谁！")
                return

            send_time = self.sch_datetime_input.dateTime().toPyDateTime()
            if send_time <= datetime.now():
                reply = QMessageBox.question(self, "时间提醒",
                    "您设定的发送时间已经过了！\n是否仍然添加到队列？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return

            repeat = self.sch_repeat_check.isChecked()
            interval = self.sch_interval_spin.value()

            task = ScheduledTask(self.next_task_id, recipient, message, file_path, send_time, repeat, interval)
            self.next_task_id += 1
            self.scheduled_tasks.append(task)
            self.refresh_task_table()
            self.save_tasks()
            send_time_str = send_time.strftime("%m月%d日 %H:%M:%S")
            mode = f"重复(每{interval}分钟)" if repeat else "单次"
            self.log(f"已添加定时任务#{task.id} → {recipient}，{mode}，预定 {send_time_str} 发送")
            QMessageBox.information(self, "添加成功",
                f"任务已加入队列！\n{mode}\n预定 {send_time_str} 发送到【{recipient}】\n请保持微信登录且窗口可见。")
        except Exception as e:
            QMessageBox.critical(self, "添加失败", f"添加任务时发生错误：\n{str(e)}")
            self.log(f"添加任务失败: {e}")

    def remove_scheduled_task(self, task_id):
        for task in self.scheduled_tasks:
            if task.id == task_id and task.status == "等待中":
                self.scheduled_tasks.remove(task)
                self.log(f"已删除定时任务#{task_id}")
                self.refresh_task_table()
                self.save_tasks()
                return

    def refresh_task_table(self):
        self.task_table.setRowCount(0)
        for i, task in enumerate(self.scheduled_tasks):
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)

            id_item = QTableWidgetItem(str(task.id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setItem(row, 0, id_item)

            time_str = task.send_time.strftime("%m-%d %H:%M")
            self.task_table.setItem(row, 1, QTableWidgetItem(time_str))
            self.task_table.setItem(row, 2, QTableWidgetItem(task.recipient))

            msg_display = task.message[:20] + "..." if len(task.message) > 20 else task.message
            self.task_table.setItem(row, 3, QTableWidgetItem(msg_display))

            file_display = os.path.basename(task.file_path) if task.file_path else "-"
            self.task_table.setItem(row, 4, QTableWidgetItem(file_display))

            repeat_display = f"每{task.interval}分" if task.repeat else "单次"
            repeat_item = QTableWidgetItem(repeat_display)
            repeat_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setItem(row, 5, repeat_item)

            status_item = QTableWidgetItem(task.status)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setItem(row, 6, status_item)

            if task.status == "等待中":
                del_btn = QPushButton("删除")
                del_btn.clicked.connect(lambda checked, tid=task.id: self.remove_scheduled_task(tid))
                self.task_table.setCellWidget(row, 7, del_btn)
            else:
                self.task_table.setItem(row, 7, QTableWidgetItem("-"))

        pending_count = sum(1 for t in self.scheduled_tasks if t.status == "等待中")
        self.status_bar.showMessage(f"当前队列中有 {pending_count} 个待发送任务")

    def clear_completed_tasks(self):
        before = len(self.scheduled_tasks)
        self.scheduled_tasks = [t for t in self.scheduled_tasks if t.status == "等待中"]
        removed = before - len(self.scheduled_tasks)
        self.log(f"已清除 {removed} 个已完成/失败的任务")
        self.refresh_task_table()
        self.save_tasks()

    def save_tasks(self):
        pending_tasks = [t.to_dict() for t in self.scheduled_tasks if t.status == "等待中"]
        save_data = {
            "next_task_id": self.next_task_id,
            "tasks": pending_tasks
        }
        try:
            with open(resource_path("tasks.json"), "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存任务失败: {e}")

    def load_tasks(self):
        try:
            path = resource_path("tasks.json")
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.next_task_id = data.get("next_task_id", 1)
            for task_dict in data.get("tasks", []):
                task = ScheduledTask.from_dict(task_dict)
                if task.send_time > datetime.now():
                    self.scheduled_tasks.append(task)
                else:
                    task.status = "已过期"
                    task.error_msg = "任务已过时"
                    self.scheduled_tasks.append(task)
            if self.scheduled_tasks:
                self.refresh_task_table()
                self.log(f"已加载 {len(self.scheduled_tasks)} 个历史任务")
        except Exception as e:
            self.log(f"加载任务失败: {e}")

    def closeEvent(self, event):
        self.save_tasks()
        event.accept()


if __name__ == '__main__':
    import traceback
    from PyQt5.QtCore import QThread
    def global_exception_hook(exctype, value, tb):
        err_text = ''.join(traceback.format_exception(exctype, value, tb))
        print(err_text)
        if QThread.currentThread() == QApplication.instance().thread():
            try:
                QMessageBox.critical(None, "程序异常", f"发生未捕获的异常：\n{value}\n\n详情已输出到控制台。")
            except Exception:
                pass
        sys.__excepthook__(exctype, value, tb)
    sys.excepthook = global_exception_hook

    app = QApplication(sys.argv)
    window = WeChatAutomationApp()
    window.show()
    sys.exit(app.exec_())