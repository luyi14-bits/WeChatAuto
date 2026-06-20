# 自主测试纠错系统 Checklist

- [x] SmartSendExecutor 类已添加到 WeChatAuto.py
- [x] SmartSendExecutor.execute() 实现了 3 策略循环 + 降级逻辑
- [x] 策略1（侧边栏 Click+Enter）实现在 _s1_sidebar
- [x] 策略2（Ctrl+F+Esc+Enter）实现在 _s2_ctrl_f_esc
- [x] 策略3（Ctrl+F+Down+Enter）实现在 _s3_ctrl_f_down
- [x] _walk_list_item UIA树遍历正确查找 depth≥7 的 ListItemControl
- [x] WeChatAutomator.execute_send_flow 已委托给 SmartSendExecutor
- [x] auto_test.py 脚本已创建，接受 3 个命令行参数
- [x] auto_test.py 创建了 QApplication 实例（剪贴板依赖）
- [x] auto_test.py 输出详细步骤日志
- [x] 运行 `python auto_test.py "文件传输助手" "测试测试test123" "D:\Desktop\test.jpg"` 无崩溃
- [x] 测试完成，策略1成功发送 (exit_code=0)
