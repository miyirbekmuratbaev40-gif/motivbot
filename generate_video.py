"""
generate_video.py
------------------
Motivatsion iqtibos matnidan avtomatik ravishda vertikal (1080x1920,
Instagram Reels formati) video yaratadi. Sekin zoom effekti va
fade-in/fade-out bilan.

Chiqish: output/video.mp4 va output/caption.txt
"""

import json
import os
import random
import subprocess
import textwrap
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1080, 1920
FONT_BOLD = "fonts/Font-Bold.ttf"
FONT_REGULAR = "fonts/Font-Regular.ttf"
QUOTES_FILE = "quotes.json"
STATE_FILE = "state.json"
OUTPUT_DIR = "output"

# Bir-biriga mos keladigan gradient rang palitralari (top, bottom)
PALETTES = [
    ((20, 24, 38), (64, 43, 110)),
    ((10, 30, 45), (14, 90, 100)),
    ((35, 15, 45), (110, 40, 70)),
    ((15, 35, 25), (30, 90, 60)),
    ((40, 20, 15), (110, 60, 20)),
    ((15, 15, 40), (50, 50, 120)),
]


def load_quotes():
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"used_indices": [], "last_run": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_quote(quotes, state):
    used = set(state.get("used_indices", []))
    remaining = [i for i in range(len(quotes)) if i not in used]
    if not remaining:
        # Barcha iqtiboslar ishlatilgan - qaytadan boshlaymiz
        used = set()
        remaining = list(range(len(quotes)))
    idx = random.choice(remaining)
    used.add(idx)
    state["used_indices"] = list(used)
    state["last_run"] = datetime.utcnow().isoformat()
    return quotes[idx], state


def make_gradient(top_color, bottom_color):
    base = Image.new("RGB", (WIDTH, HEIGHT), top_color)
    top = Image.new("RGB", (1, HEIGHT), top_color)
    bottom = Image.new("RGB", (1, HEIGHT), bottom_color)
    gradient_col = Image.blend(top, bottom, 0)
    grad = Image.new("RGB", (1, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        grad.putpixel((0, y), (r, g, b))
    return grad.resize((WIDTH, HEIGHT))


def add_texture(img):
    # Yengil noise/vignette effekti bilan chuqurlik qo'shamiz
    overlay = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(overlay)
    for i in range(0, 260, 4):
        alpha = int(140 * (i / 260))
        draw.rectangle([i, i, WIDTH - i, HEIGHT - i], outline=alpha)
    overlay = overlay.filter(ImageFilter.GaussianBlur(80))
    black = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    img = Image.composite(black, img, overlay.point(lambda p: int(p * 0.55)))
    return img


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_frame(quote_text, author):
    palette = random.choice(PALETTES)
    img = make_gradient(*palette)
    img = add_texture(img)
    draw = ImageDraw.Draw(img)

    font_size = 78
    font = ImageFont.truetype(FONT_BOLD, font_size)
    max_width = WIDTH - 160

    lines = wrap_text(draw, quote_text, font, max_width)
    while len(lines) > 6 and font_size > 40:
        font_size -= 4
        font = ImageFont.truetype(FONT_BOLD, font_size)
        lines = wrap_text(draw, quote_text, font, max_width)

    line_height = int(font_size * 1.35)
    total_h = line_height * len(lines)
    start_y = (HEIGHT - total_h) // 2 - 60

    # Yuqori bezak chizig'i
    draw.line([(WIDTH // 2 - 60, start_y - 70), (WIDTH // 2 + 60, start_y - 70)],
               fill=(255, 255, 255), width=6)

    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = (WIDTH - w) // 2
        y = start_y + i * line_height
        # Yengil soya
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))

    # Muallif
    author_font = ImageFont.truetype(FONT_REGULAR, 42)
    author_text = f"— {author}"
    w = draw.textlength(author_text, font=author_font)
    y = start_y + len(lines) * line_height + 40
    draw.text(((WIDTH - w) // 2, y), author_text, font=author_font, fill=(220, 220, 220))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    frame_path = os.path.join(OUTPUT_DIR, "frame.png")
    img.save(frame_path)
    return frame_path


def build_video(frame_path, duration=8):
    """ffmpeg zoompan filtri yordamida sekin zoom-in video yaratamiz."""
    out_path = os.path.join(OUTPUT_DIR, "video.mp4")
    fps = 30
    total_frames = duration * fps
    filter_str = (
        f"zoompan=z='min(zoom+0.0007,1.15)':d={total_frames}:s={WIDTH}x{HEIGHT}:fps={fps},"
        f"fade=t=in:st=0:d=0.6,fade=t=out:st={duration - 0.6}:d=0.6"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", frame_path,
        "-vf", filter_str,
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def main():
    quotes = load_quotes()
    state = load_state()
    quote, state = pick_quote(quotes, state)
    save_state(state)

    frame_path = render_frame(quote["text"], quote["author"])
    video_path = build_video(frame_path)

    caption = (
        f"{quote['text']}\n\n— {quote['author']}\n\n"
        f"#motivatsiya #ozini_rivojlantirish #maqsad #ilhom #kunlikmotivatsiya"
    )
    with open(os.path.join(OUTPUT_DIR, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"Video tayyor: {video_path}")
    print(f"Caption:\n{caption}")


if __name__ == "__main__":
    main()
