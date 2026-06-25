# WeChatAuto

基于 PyQt5 + wxauto 的 Windows 微信自动化工具。

## 功能

- **即时发送** — 输入联系人名称、消息文本和图片路径，一键发送
- **定时发送** — 设置 cron 表达式定时任务，自动在指定时间发送消息
- **设置管理** — 自动发现微信路径，支持手动指定
- **命令行模式** — 支持 `--send` 参数在命令行中直接发送消息
- **子进程隔离** — 发送操作在独立 QProcess 中运行，避免阻塞主界面

## 依赖

- Python 3.8+
- PyQt5
- wxauto

## 安装

```bash
pip install PyQt5 wxauto
```

## 使用

### 图形界面

```bash
python WeChatAuto.py
```

### 命令行发送

```bash
python WeChatAuto.py --send --recipient "联系人名称" --text "消息内容"
python WeChatAuto.py --send --recipient "联系人名称" --image "图片路径.png"
```

## 定时任务

定时任务使用标准 5 字段 cron 表达式：

| 表达式              | 含义             |
| ------------------- | ---------------- |
| `0 8 * * *`         | 每天早上 8:00    |
| `30 12 * * 1-5`     | 工作日中午 12:30 |
| `0 9 1 * *`         | 每月 1 号 9:00   |

定时任务保存在 `tasks.json` 文件中，程序启动时自动加载。

## 许可证

GNU Affero General Public License v3.0
