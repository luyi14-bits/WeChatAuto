import struct
import os


def generate_wechat_icon():
    size = 32
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "wechat.ico"
    )

    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    green_bg = (7, 193, 96)
    green_dark = (5, 153, 75)
    white = (255, 255, 255)

    r = size // 2 - 2
    cx, cy = size // 2, size // 2

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=green_bg)

    ear_r = r // 3
    ear_offset = r - ear_r + 1
    for dx in (-1, 1):
        ex = cx + dx * ear_offset
        ey = cy - ear_offset
        draw.ellipse(
            [ex - ear_r, ey - ear_r, ex + ear_r, ey + ear_r],
            fill=green_bg,
            outline=green_dark,
        )

    bubble_w = int(r * 0.85)
    bubble_h = int(r * 0.55)
    bubble_x = cx - bubble_w // 2
    bubble_y = cy - bubble_h // 2

    draw.rounded_rectangle(
        [bubble_x, bubble_y, bubble_x + bubble_w, bubble_y + bubble_h],
        radius=bubble_h // 3,
        fill=white,
    )

    eye_r = max(1, bubble_h // 8)
    eye_y = bubble_y + bubble_h // 3
    for dx_eye in (-bubble_w // 5, bubble_w // 5):
        ex_eye = cx + dx_eye
        draw.ellipse(
            [
                ex_eye - eye_r,
                eye_y - eye_r,
                ex_eye + eye_r,
                eye_y + eye_r,
            ],
            fill=green_bg,
        )

    mouth_y = bubble_y + int(bubble_h * 0.65)
    mouth_w = bubble_w // 3
    draw.arc(
        [
            cx - mouth_w // 2,
            mouth_y - mouth_w // 3,
            cx + mouth_w // 2,
            mouth_y + mouth_w // 3,
        ],
        start=0,
        end=180,
        fill=green_bg,
        width=max(1, bubble_h // 10),
    )

    img.save(output_path, format="ICO", sizes=[(size, size)])
    print(f"Created: {output_path}")


if __name__ == "__main__":
    generate_wechat_icon()
