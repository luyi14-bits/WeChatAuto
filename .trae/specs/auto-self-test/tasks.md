# 自主测试纠错系统 Tasks

- [x] Task 1: 创建 `SmartSendExecutor` 类（新增到 WeChatAuto.py 中 WeChatAutomator 类之前）
  - 构造函数接受 `wechat_automator` 实例
  - 实现 `execute(target_name, text_msg, file_path)` 方法——3 策略循环，每个策略执行后直接发送文本+图片
  - 策略1：`_s1_sidebar(wechat_win, target_name)` — Esc×3 → 树遍历 depth≥7 ListItemControl → Click+Enter
  - 策略2：`_s2_ctrl_f_esc(wechat_win, target_name)` — Ctrl+F → 打字 → Esc → Enter
  - 策略3：`_s3_ctrl_f_down(wechat_win, target_name)` — Ctrl+F → 打字 → Down×3 → Enter
  - 发送消息+照片部分复用原有逻辑

- [x] Task 2: 改造 `WeChatAutomator.execute_send_flow`，委托给 SmartSendExecutor
  - 保留方法签名不变
  - 内部实例化 SmartSendExecutor → 调用 executor.execute()
  - 删除了旧的 `_find_sidebar_list_item` 方法（已移至 SmartSendExecutor）

- [x] Task 3: 创建 `auto_test.py` 独立测试脚本
  - 命令行接受 3 个参数：target_name text_msg file_path
  - 创建 QApplication 实例（剪贴板依赖）
  - 直接 import WeChatAuto 模块
  - 输出详细步骤日志
  - 成功 exit(0)，失败 exit(1)

- [x] Task 4: 执行自主测试
  - 运行 `python auto_test.py "文件传输助手" "测试测试test123" "D:\Desktop\test.jpg"`
  - **结果: 策略1成功** (exit_code=0)
  - 策略：Esc×3 → UIA树遍历找depth≥7的ListItemControl → Click → Enter → 发送文字+图片

# Task Dependencies
- Task 2 depends on Task 1
- Task 4 depends on Task 1 + 2 + 3
- Task 3 can parallel with Task 1 + 2
