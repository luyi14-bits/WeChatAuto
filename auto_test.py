import argparse
import sys
import time
import os


def main():
    parser = argparse.ArgumentParser(
        description="WeChat message sender (wxauto subprocess)"
    )
    parser.add_argument(
        "--recipient", "-r", required=True, help="Target contact or group name"
    )
    parser.add_argument(
        "--text", "-t", default="", help="Text message content"
    )
    parser.add_argument(
        "--image", "-i", default="", help="Path to image file to send"
    )
    args = parser.parse_args()

    if not args.text and not args.image:
        sys.exit("ERROR: At least one of --text or --image must be provided")

    if args.image and not os.path.isfile(args.image):
        sys.exit(f"ERROR: Image file not found: {args.image}")

    try:
        from wxauto import WeChat
    except ImportError:
        sys.exit(
            "ERROR: wxauto is not installed. Run: pip install wxauto"
        )

    wx = WeChat()

    try:
        wx.ChatWith(args.recipient)
        time.sleep(1.0)
    except Exception:
        pass

    if args.text:
        try:
            wx.SendMsg(args.text)
            time.sleep(0.5)
        except Exception as e:
            sys.exit(f"ERROR sending text: {e}")

    if args.image:
        try:
            wx.SendFiles(args.image)
            time.sleep(0.5)
        except Exception as e:
            sys.exit(f"ERROR sending image: {e}")

    print("OK")


if __name__ == "__main__":
    main()
