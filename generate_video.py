import json
import random
import os
import sys
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import edge_tts

# MUHIM: moviepy import qilish
try:
    from moviepy.editor import ImageSequenceClip, AudioFileClip
    from moviepy.video.fx.all import fadein, fadeout
    print("✅ moviepy import qilindi")
except ImportError as e:
    print(f"❌ moviepy import xatosi: {e}")
    print("   Iltimos, kutubxonalarni o'rnating:")
    print("   pip install moviepy==1.0.3 imageio==2.34.0 imageio-ffmpeg==0.5.1")
    sys.exit(1)

# =============== SOZLAMALAR ===============
os.makedirs("output", exist_ok=True)
os.makedirs("fonts", exist_ok=True)

W, H = 1080, 1920

COLORS = [
    ["#0f0c29", "#302b63"],
    ["#ff6b6b", "#ffa500"],
    ["#00b4db", "#0083b0"],
    ["#8e2de2", "#4a00e0"],
    ["#11998e", "#38ef7d"],
    ["#fc5c7d", "#6a82fb"],
    ["#1a1a2e", "#16213e"],
    ["#f7971e", "#ffd200"],
    ["#667eea", "#764ba2"],
    ["#f12711", "#f5af19"],
    ["#0cebeb", "#20e3b2"],
    ["#e65c00", "#f9d423"],
]


def create_gradient(w, h, c1, c2):
    img = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(img)
    r1, g1, b1 = tuple(int(c1[i:i+2], 16) for i in (1, 3, 5))
    r2, g2, b2 = tuple(int(c2[i:i+2], 16) for i in (1, 3, 5))
    for i in range(h):
        ratio = i / h
        r = int(r1 * (1 - ratio) + r2 * ratio)
        g = int(g1 * (1 - ratio) + g2 * ratio)
        b = int(b1 * (1 - ratio) + b2 * ratio)
        draw.line([(0, i), (w, i)], fill=(r, g, b))
    if random.random() > 0.4:
        for _ in range(random.randint(20, 50)):
            x = random.randint(0, w)
            y = random.randint(0, h)
            s = random.randint(1, 4)
            br = random.randint(180, 255)
            draw.ellipse([x, y, x + s, y + s], fill=(br, br, br))
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
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    draw = ImageDraw.Draw(img)
    
    font = ImageFont.load_default()
    font_paths = [os.path.join("fonts", f) for f in os.listdir("fonts") 
                  if f.endswith((".ttf", ".otf"))] if os.path.exists("fonts") else []
    if font_paths:
        try:
            font = ImageFont.truetype(random.choice(font_paths), 56)
        except:
            pass
    
    max_w = W - 180
    lines = wrap_text(quote, font, max_w, draw)
    
    progress = frame_num / max(total_frames, 1)
    offset = int((1 - progress) * 50)
    
    line_h = 72
    total_h = len(lines) * line_h
    start_y = (H - total_h) // 2 - 60 + offset
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_h
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
    
    if author and author != "Unknown":
        author_text = f"— {author}"
        bbox = draw.textbbox((0, 0), author_text, font=font)
        aw = bbox[2] - bbox[0]
        ay = start_y + len(lines) * line_h + 30
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text(((W - aw) // 2 + dx, ay + dy), author_text, font=font, fill=(0, 0, 0))
        draw.text(((W - aw) // 2, ay), author_text, font=font, fill=(255, 215, 0))
    
    tag_text = "@motivbot_uz"
    bbox = draw.textbbox((0, 0), tag_text, font=font)
    tw = bbox[2] - bbox[0]
    ty = H - 90
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx != 0 or dy != 0:
                draw.text(((W - tw) // 2 + dx, ty + dy), tag_text, font=font, fill=(0, 0, 0))
    draw.text(((W - tw) // 2, ty), tag_text, font=font, fill=(200, 200, 200))
    
    return np.array(img)


async def generate_audio(text, path):
    voices = ["uz-UZ-MadinaNeural", "ru-RU-DariyaNeural", "en-US-JennyNeural"]
    for voice in voices:
        try:
            tts = edge_tts.Communicate(text, voice)
            await tts.save(path)
            if os.path.getsize(path) > 500:
                return True
        except:
            continue
    return False


def create_video(quote, author, output_path="output/video.mp4"):
    print("\n" + "="*50)
    print("🎬 VIDEO YARATISH BOSHLANDI")
    print("="*50)
    print(f"📝 Matn: {quote[:80]}...")
    print(f"✍️  Muallif: {author}")
    
    # CAPTION
    caption = f"{quote}\n\n— {author}\n\n#motivatsiya #iqtibos #kunilikiqtibos #motivbot_uz"
    with open("output/caption.txt", "w", encoding="utf-8") as f:
        f.write(caption)
    print("✅ caption.txt yaratildi")
    
    # AUDIO
    audio_path = "temp_audio.mp3"
    print("🎵 Ovoz yaratilmoqda...")
    audio_ok = asyncio.run(generate_audio(quote, audio_path))
    
    dur = 5.0
    audio = None
    if audio_ok and os.path.exists(audio_path):
        try:
            audio = AudioFileClip(audio_path)
            dur = audio.duration
            print(f"✅ Audio: {dur:.1f} sek")
        except Exception as e:
            print(f"⚠️ Audio xatosi: {e}")
    
    # KADRLAR
    fps = 24
    total_frames = int(dur * fps) + 24
    
    print(f"🖼️  Kadrlar: {total_frames} ta")
    frames = []
    for i in range(total_frames):
        frame = make_frame(quote, author, i, total_frames)
        frames.append(frame)
        if i % 15 == 0 or i == total_frames - 1:
            print(f"   Progress: {i+1}/{total_frames} ({(i+1)/total_frames*100:.0f}%)")
    
    # RENDER
    print("🎞️ Render...")
    clip = ImageSequenceClip(frames, fps=fps)
    
    if audio:
        clip = clip.set_audio(audio)
    
    clip = clip.fx(fadein, 0.3)
    clip = clip.fadeout(0.5)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    clip.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        fps=fps,
        preset='ultrafast',
        bitrate='3000k',
        threads=4,
        logger=None
    )
    
    clip.close()
    if audio and os.path.exists(audio_path):
        os.remove(audio_path)
    
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print("="*50)
    print(f"✅ VIDEO TAYYOR!")
    print(f"   📍 {output_path}")
    print(f"   📦 {size_mb:.1f} MB")
    print(f"   ⏱️  {dur:.1f} sek")
    print("="*50)
    return output_path


if __name__ == "__main__":
    try:
        with open("facts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ facts.json xatosi: {e}")
        data = [
            {"quote": "Muvaffaqiyatga erishishning kaliti - bu harakat qilishni boshlash!", "author": "MotivBot"},
            {"quote": "Kuniga 1% yaxshilanib boring. Bir yildan so'ng 37 barobar kuchli bo'lasiz!", "author": "James Clear"},
            {"quote": "Orzularingiz sari intiling! Hech qachon kech emas.", "author": "Unknown"},
        ]
    
    if isinstance(data, list):
        quotes = data
    elif isinstance(data, dict):
        quotes = data.get("quotes", data.get("facts", [{"quote": "Test", "author": "Test"}]))
        if isinstance(quotes, dict):
            quotes = list(quotes.values())
    else:
        quotes = [{"quote": str(data), "author": "Unknown"}]
    
    if quotes and len(quotes) > 0:
        q = random.choice(quotes)
        if isinstance(q, dict):
            text = q.get("quote", q.get("text", q.get("fact", "Test matni")))
            author = q.get("author", "Unknown")
        else:
            text = str(q)
            author = "Unknown"
    else:
        text = "Muvaffaqiyat sari intil!"
        author = "MotivBot"
    
    print(f"\n📖 Tanlangan: {text}")
    print(f"✍️  Muallif: {author}")
    create_video(text, author)
