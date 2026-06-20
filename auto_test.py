# -*- coding:utf-8 -*-
import sys
import os

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python auto_test.py <联系人> [文字内容] [图片路径]")
        sys.exit(1)

    target = sys.argv[1]
    text = sys.argv[2] if len(sys.argv) >= 3 else ""
    image = sys.argv[3] if len(sys.argv) >= 4 else ""

    if image and not os.path.exists(image):
        print(f"[错误] 图片不存在: {image}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"微信自动消息助手 - 自主测试")
    print(f"目标: {target}")
    print(f"文字: {text}")
    print(f"图片: {image or '无'}")
    print(f"{'='*60}")

    try:
        from wxauto import WeChat
        wx = WeChat()

        if text:
            wx.SendMsg(text, target)

        if image and os.path.exists(image):
            wx.SendFiles(image, target)

        print(f"\n{'='*60}")
        print(f"[结果] ✅ 发送完成 → {target}")
        print(f"{'='*60}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"[结果] ❌ 发送失败")
        print(f"[错误] {e}")
        print(f"{'='*60}")
        sys.exit(1)
