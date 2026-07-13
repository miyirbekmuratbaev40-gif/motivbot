"""
generate_video.py (v3 - qiziqarli faktlar, ovozli, real fon videoli)
----------------------------------------------------------------------
1) Tasodifiy qiziqarli fakt tanlaydi (facts.json)
2) Matnni o'zbekcha tabiiy ovozga aylantiradi (Microsoft Edge TTS,
   uz-UZ-SardorNeural / uz-UZ-MadinaNeural - bepul, API kalit shart emas)
3) Pexels'dan mavzuga mos bepul stock-video (fon) yuklab oladi
4) "BILASIZMI?" hook + fakt matnini shaffof PNG sifatida chizadi
5) ffmpeg orqali hammasini birlashtirib, ovozli, 1080x1920 Reels video yaratadi

Kerakli muhit o'zgaruvchisi:
    PEXELS_API_KEY   (bepul, pexels.com/api dan olinadi)
"""

import asyncio
import json
import os
import random
import subprocess
import sys
import textwrap
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
FONT_BOLD = "fonts/Font-Bold.ttf"
FONT_REGULAR = "fonts/Font-Regular.ttf"
FACTS_FILE = "facts.json"
STATE_FILE = "state.json"
OUTPUT_DIR = "output"

VOICES = ["uz-UZ-SardorNeural", "uz-UZ-MadinaNeural"]

# Pexels qidiruv so'zlari - fan/tabiat/koinot mavzusiga mos, "vau-effekt" beruvchi fon videolar
BACKGROUND_THEMES = [
    "space galaxy stars",
    "ocean underwater deep",
    "wildlife animals nature",
    "aurora borealis northern lights",
    "microscope science lab",
    "planet earth from space",
    "rainforest jungle aerial",
    "volcano lava nature",
    "desert dunes aerial",
    "coral reef underwater",
]


def load_facts():
    with open(FACTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"used_indices": [], "last_run": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_fact(facts, state):
    used = set(state.get("used_indices", []))
    remaining = [i for i in range(len(facts)) if i not in used]
    if not remaining:
        used = set()
        remaining = list(range(len(facts)))
    idx = random.choice(remaining)
    used.add(idx)
    state["used_indices"] = list(used)
    state["last_run"] = datetime.utcnow().isoformat()
    return facts[idx], state


def generate_speech(fact_text, out_path):
    import edge_tts

    voice = random.choice(VOICES)
    spoken_text = f"Bilasizmi?... {fact_text}"

    async def _run():
        communicate = edge_tts.Communicate(spoken_text, voice, rate="-5%")
        await communicate.save(out_path)

    asyncio.run(_run())
    print(f"Ovoz yaratildi ({voice}): {out_path}")
    return voice


def get_audio_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def fetch_background_video(out_path):
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        print("OGOHLANTIRISH: PEXELS_API_KEY topilmadi, gradient fon ishlatiladi.")
        return None

    theme = random.choice(BACKGROUND_THEMES)
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": theme, "orientation": "portrait", "per_page": 15, "size": "medium"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            print(f"Pexels'da '{theme}' uchun natija topilmadi, gradient fon ishlatiladi.")
            return None

        video = random.choice(videos)
        files = sorted(
            video["video_files"],
            key=lambda f: abs((f.get("width") or 0) - WIDTH),
        )
        best = next((f for f in files if (f.get("height") or 0) > (f.get("width") or 0)), files[0])

        video_resp = requests.get(best["link"], timeout=60)
        video_resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(video_resp.content)

        print(f"Fon video yuklandi (mavzu: '{theme}'): {out_path}")
        return out_path
    except Exception as e:
        print(f"OGOHLANTIRISH: Pexels'dan video yuklab bo'lmadi ({e}), gradient fon ishlatiladi.")
        return None


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


def render_text_overlay(fact_text):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    hook_font = ImageFont.truetype(FONT_BOLD, 58)
    font_size = 68
    font = ImageFont.truetype(FONT_BOLD, font_size)
    max_width = WIDTH - 160

    lines = wrap_text(draw, fact_text, font, max_width)
    while len(lines) > 7 and font_size > 40:
        font_size -= 4
        font = ImageFont.truetype(FONT_BOLD, font_size)
        lines = wrap_text(draw, fact_text, font, max_width)

    line_height = int(font_size * 1.35)
    hook_h = 100
    total_h = hook_h + line_height * len(lines) + 60
    box_top = (HEIGHT - total_h) // 2 - 60
    box_bottom = box_top + total_h + 40

    # O'qish qulay bo'lishi uchun matn ortida yarim shaffof qora panel
    draw.rectangle([(0, box_top - 40), (WIDTH, box_bottom + 40)], fill=(0, 0, 0, 150))

    # "BILASIZMI?" hook - diqqatni tortuvchi sariq belgi
    hook_text = "BILASIZMI?"
    hw = draw.textlength(hook_text, font=hook_font)
    hook_y = box_top
    # Hook ortida kichik rangli chiziq/badge
    draw.rounded_rectangle(
        [(WIDTH // 2 - hw / 2 - 30, hook_y - 12), (WIDTH // 2 + hw / 2 + 30, hook_y + 68)],
        radius=20, fill=(255, 200, 40, 230),
    )
    draw.text((WIDTH // 2 - hw / 2, hook_y), hook_text, font=hook_font, fill=(20, 20, 20, 255))

    start_y = hook_y + hook_h + 20
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = (WIDTH - w) // 2
        y = start_y + i * line_height
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 160))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    overlay_path = os.path.join(OUTPUT_DIR, "overlay.png")
    img.save(overlay_path)
    return overlay_path


def render_gradient_fallback():
    palette_top, palette_bottom = (20, 24, 38), (64, 43, 110)
    img = Image.new("RGB", (WIDTH, HEIGHT), palette_top)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(palette_top[0] * (1 - t) + palette_bottom[0] * t)
        g = int(palette_top[1] * (1 - t) + palette_bottom[1] * t)
        b = int(palette_top[2] * (1 - t) + palette_bottom[2] * t)
        for x in range(0, WIDTH, 4):
            img.putpixel((x, y), (r, g, b))
    path = os.path.join(OUTPUT_DIR, "fallback_bg.png")
    img.save(path)
    return path


def compose_video(background_path, overlay_path, audio_path, duration, is_video_bg):
    out_path = os.path.join(OUTPUT_DIR, "video.mp4")
    fade_out_start = max(duration - 0.6, 0)

    if is_video_bg:
        bg_filter = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},eq=brightness=-0.04,"
            f"fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out_start}:d=0.6"
        )
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", background_path,
            "-i", overlay_path,
            "-i", audio_path,
            "-filter_complex", f"[0:v]{bg_filter}[bg];[bg][1:v]overlay=0:0[v]",
            "-map", "[v]", "-map", "2:a",
            "-t", str(duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k",
            out_path,
        ]
    else:
        zoom_filter = (
            f"zoompan=z='min(zoom+0.0007,1.15)':d={int(duration * 30)}:s={WIDTH}x{HEIGHT}:fps=30,"
            f"fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out_start}:d=0.6"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", background_path,
            "-i", overlay_path,
            "-i", audio_path,
            "-filter_complex", f"[0:v]{zoom_filter}[bg];[bg][1:v]overlay=0:0[v]",
            "-map", "[v]", "-map", "2:a",
            "-t", str(duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k",
            out_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFMPEG XATOSI:", result.stderr[-2000:])
        sys.exit(1)
    return out_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    facts = load_facts()
    state = load_state()
    fact, state = pick_fact(facts, state)
    save_state(state)

    audio_path = os.path.join(OUTPUT_DIR, "audio.mp3")
    generate_speech(fact["text"], audio_path)
    duration = get_audio_duration(audio_path) + 1.0

    bg_video_path = os.path.join(OUTPUT_DIR, "background.mp4")
    fetched = fetch_background_video(bg_video_path)
    is_video_bg = fetched is not None
    background_path = fetched if fetched else render_gradient_fallback()

    overlay_path = render_text_overlay(fact["text"])

    video_path = compose_video(background_path, overlay_path, audio_path, duration, is_video_bg)

    caption = (
        f"🤯 Bilasizmi?\n\n{fact['text']}\n\n"
        f"Sizga qaysi fakt yoqdi? Izohda yozing! 👇\n\n"
        f"#qiziqarlifaktlar #bilasizmi #fakt #ilm #dunyo #tabiat #fan #qiziqarli"
    )
    with open(os.path.join(OUTPUT_DIR, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"Video tayyor: {video_path} (davomiyligi: {duration:.1f}s)")
    print(f"Caption:\n{caption}")


if __name__ == "__main__":
    main()
