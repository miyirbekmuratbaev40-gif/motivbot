import json
import random
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy.editor import *
from moviepy.video.fx.all import fadein, fadeout
import edge_tts
import asyncio

# =============== KONFIGURATSIYA ===============
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

W, H = 1080, 1920  # Instagram Reels

COLORS = [
    ["#0f0c29", "#302b63"],
    ["#ff6b6b", "#ffa500"],
    ["#00b4db", "#0083b0"],
    ["#8e2de2", "#4a00e0"],
    ["#11998e", "#38ef7d"],
    ["#fc5c7d", "#6a82fb"],
    ["#1a1a2e", "#16213e"],
    ["#f7971e", "#ffd200"],
]


def create_gradient(w, h, color1, color2):
    from PIL import ImageColor
    img = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(img)
    r1, g1, b1 = ImageColor.getrgb(color1)
    r2, g2, b2 = ImageColor.getrgb(color2)
    for i in range(h):
        ratio = i / h
        r = int(r1 * (1 - ratio) + r2 * ratio)
        g = int(g1 * (1 - ratio) + g2 * ratio)
        b = int(b1 * (1 - ratio) + b2 * ratio)
        draw.line([(0, i), (w, i)], fill=(r, g, b))
    if random.random() > 0.5:
        for _ in range(random.randint(15, 40)):
            x = random.randint(0, w)
            y = random.randint(0, h)
            s = random.randint(1, 3)
            b = random.randint(180, 255)
            draw.ellipse([x, y, x + s, y + s], fill=(b, b, b))
    return img


def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        test = cur + " " + word if cur else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def make_frame(quote, author, frame_num, total_frames):
    c1, c2 = random.choice(COLORS)
    img = create_gradient(W, H, c1, c2)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    draw = ImageDraw.Draw(img)
    
    # Font
    font_paths = []
    if os.path.exists("fonts"):
        for f in os.listdir("fonts"):
            if f.endswith(".ttf") or f.endswith(".otf"):
                font_paths.append(os.path.join("fonts", f))
    
    if font_paths:
        quote_font = ImageFont.truetype(random.choice(font_paths), 58)
        author_font = ImageFont.truetype(random.choice(font_paths), 36)
        tag_font = ImageFont.truetype(random.choice(font_paths), 22)
    else:
        quote_font = ImageFont.load_default()
        author_font = ImageFont.load_default()
        tag_font = ImageFont.load_default()
    
    max_w = W - 160
    lines = wrap_text(quote, quote_font, max_w, draw)
    
    progress = frame_num / max(total_frames, 1)
    offset = int((1 - progress) * 40)
    
    line_h = 70
    total_h = len(lines) * line_h
    start_y = (H - total_h) // 2 - 40 + offset
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=quote_font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_h
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=quote_font, fill="black")
        draw.text((x, y), line, font=quote_font, fill="white")
    
    if author:
        author_text = f"— {author}"
        bbox = draw.textbbox((0, 0), author_text, font=author_font)
        aw = bbox[2] - bbox[0]
        ay = start_y + len(lines) * line_h + 20
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text(((W - aw) // 2 + dx, ay + dy), author_text, font=author_font, fill="black")
        draw.text(((W - aw) // 2, ay), author_text, font=author_font, fill="#FFD700")
    
    tag = "@motivbot"
    bbox = draw.textbbox((0, 0), tag, font=tag_font)
    tw = bbox[2] - bbox[0]
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx != 0 or dy != 0:
                draw.text(((W - tw) // 2 + dx, H - 70 + dy), tag, font=tag_font, fill="black")
    draw.text(((W - tw) // 2, H - 70), tag, font=tag_font, fill="#888888")
    
    return np.array(img)


async def gen_audio(text, path):
    try:
        voice = "uz-UZ-MadinaNeural"
        tts = edge_tts.Communicate(text, voice)
        await tts.save(path)
        return True
    except:
        try:
            voice = "ru-RU-DariyaNeural"
            tts = edge_tts.Communicate(text, voice)
            await tts.save(path)
            return True
        except:
            return False


def create_video(quote, author, output_path):
    print(f"🎬 Video yaratilmoqda...")
    
    audio_path = "temp_audio.mp3"
    asyncio.run(gen_audio(quote, audio_path))
    
    try:
        audio = AudioFileClip(audio_path)
        dur = audio.duration
    except:
        dur = 5.0
        audio = None
    
    fps = 24
    total = int(dur * fps) + 24
    
    print(f"   Kadrlar: {total} ta")
    frames = []
    for i in range(total):
        frames.append(make_frame(quote, author, i, total))
        if i % 20 == 0:
            print(f"   {i}/{total}")
    
    print("   Render...")
    clip = ImageSequenceClip(frames, fps=fps)
    
    if audio and os.path.exists(audio_path):
        clip = clip.set_audio(audio)
    
    clip = clip.fx(fadein, 0.3)
    clip = clip.fadeout(0.5)
    
    clip.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        fps=fps,
        preset='ultrafast',
        bitrate='4000k'
    )
    
    clip.close()
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    print(f"✅ Video tayyor: {output_path}")
    return output_path


if __name__ == "__main__":
    with open("facts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # *** TUZATISH: agar data list bo'lsa ***
    if isinstance(data, list):
        quotes = data
    else:
        quotes = data.get("quotes", data.get("facts", data))
    
    if isinstance(quotes, list):
        q = random.choice(quotes)
        if isinstance(q, dict):
            text = q.get("quote", q.get("text", q.get("fact", "")))
            author = q.get("author", "Unknown")
        else:
            text = str(q)
            author = "Unknown"
    else:
        text = str(quotes)
        author = "Unknown"
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(OUTPUT_DIR, f"reel_{ts}.mp4")
    
    create_video(text, author, out)
