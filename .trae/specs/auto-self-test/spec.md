# 自主测试纠错系统 Spec

## Why
过去多轮反复修改 `execute_send_flow`，每次都靠用户反馈才知道是否成功，效率极低。新版微信（带朋友圈、小程序面板）UIA 控件行为极其不稳定，没有一种策略能在所有场景下可靠工作。需要一套自动化的自测+纠错机制——程序自主测试发送，检测结果，失败后切换策略重试，不再依赖人工反馈。

## What Changes
- 新增 `SmartSendExecutor` 类：多策略发送引擎，内置 3 种策略 + 结果验证 + 自动降级
- 改造 `WeChatAutomator.execute_send_flow`：委托给 SmartSendExecutor
- 新增 `auto_test.py` 独立测试脚本：直接在命令行运行，无需 GUI，自动测试验证
- **BREAKING**: `execute_send_flow` 行为变更——不再单次返回成功/失败，改为内部多次重试直到成功

## Impact
- Affected specs: 无（新功能）
- Affected code: `WeChatAuto.py`（新增 SmartSendExecutor 类 + 修改 execute_send_flow）、`auto_test.py`（新增）

## ADDED Requirements

### Requirement: SmartSendExecutor 多策略发送
系统 SHALL 提供一个 `SmartSendExecutor` 类，内置 3 种发送策略，按优先级依次尝试，每种策略执行后验证是否成功跳转到目标聊天窗口，成功则停止，失败则切换下一策略。

#### Scenario: 策略1——侧边栏直击成功
- **GIVEN** 微信主窗口可见且联系人存在于侧边栏
- **WHEN** 执行策略1：Esc×3 退出当前聊天 → UIA 树遍历找 depth≥7 的 ListItemControl → Click + Enter
- **THEN** 目标聊天窗口打开，"输入"框可见 → 验证通过 → 发送消息

#### Scenario: 策略1失败 → 策略2接管
- **WHEN** 策略1 执行后"输入"框不可见
- **THEN** 自动切换策略2：Ctrl+F → 逐字输入 → Esc → Enter → 验证"输入"框

#### Scenario: 策略2失败 → 策略3接管
- **WHEN** 策略2 执行后"输入"框不可见
- **THEN** 自动切换策略3：Ctrl+F → 逐字输入 → Down×3 导航到第一条结果 → Enter → 验证

#### Scenario: 全部策略失败
- **WHEN** 3 种策略全部执行完毕且"输入"框均不可见
- **THEN** 抛出包含所有策略错误信息的 Exception

### Requirement: 发送结果验证
系统 SHALL 在每个策略发送文字后，验证消息是否出现在目标聊天窗口的最近消息中。

#### Scenario: 验证发送成功
- **GIVEN** 文字已通过 SendKeys 发送
- **WHEN** 读取聊天窗口最新消息（UIA TextControl）
- **THEN** 若最近消息包含发送的文字内容 → 验证通过 → 返回成功

### Requirement: 独立自测脚本
系统 SHALL 提供一个 `auto_test.py` 脚本，接受命令行参数，执行发送并输出详细日志。

#### Scenario: 命令行调用
- **WHEN** 运行 `python auto_test.py "文件传输助手" "测试测试test123" "D:\Desktop\test.jpg"`
- **THEN** 输出每步操作日志 → 每个策略的验证结果 → 最终成功/失败报告
