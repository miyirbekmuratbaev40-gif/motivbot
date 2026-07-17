import json
import random
import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import edge_tts
import asyncio

try:
    from moviepy.editor import *
    from moviepy.video.fx.all import fadein, fadeout
except ImportError:
    print("❌ moviepy o'rnatilmagan. O'rnatish: pip install moviepy")
    sys.exit(1)

# =============== KONFIGURATSIYA ===============
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
]


def create_gradient(w, h, c1, c2):
    """Gradient fon"""
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
    if random.random() > 0.5:
        for _ in range(random.randint(15, 40)):
            x = random.randint(0, w)
            y = random.randint(0, h)
            s = random.randint(1, 3)
            br = random.randint(180, 255)
            draw.ellipse([x, y, x + s, y + s], fill=(br, br, br))
    return img


def make_frame(quote, author, frame_num, total_frames):
    """1 kadr"""
    c1, c2 = random.choice(COLORS)
    img = create_gradient(W, H, c1, c2)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    draw = ImageDraw.Draw(img)
    
    # Font
    font = ImageFont.load_default()
    font_paths = []
    if os.path.exists("fonts"):
        for f in os.listdir("fonts"):
            if f.endswith(".ttf") or f.endswith(".otf"):
                font_paths.append(os.path.join("fonts", f))
    if font_paths:
        try:
            font = ImageFont.truetype(random.choice(font_paths), 50)
        except:
            pass
    
    # Matnni o'rash
    words = quote.split()
    lines = []
    cur = ""
    max_w = W - 160
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
    
    progress = frame_num / max(total_frames, 1)
    offset = int((1 - progress) * 40)
    
    line_h = 65
    total_h = len(lines) * line_h
    start_y = (H - total_h) // 2 - 50 + offset
    
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_h
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill="black")
        draw.text((x, y), line, font=font, fill="white")
    
    if author and author != "Unknown":
        author_text = f"— {author}"
        bbox = draw.textbbox((0, 0), author_text, font=font)
        aw = bbox[2] - bbox[0]
        ay = start_y + len(lines) * line_h + 20
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text(((W - aw) // 2 + dx, ay + dy), author_text, font=font, fill="black")
        draw.text(((W - aw) // 2, ay), author_text, font=font, fill="#FFD700")
    
    tag = "@motivbot"
    bbox = draw.textbbox((0, 0), tag, font=font)
    tw = bbox[2] - bbox[0]
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx != 0 or dy != 0:
                draw.text(((W - tw) // 2 + dx, H - 70 + dy), tag, font=font, fill="black")
    draw.text(((W - tw) // 2, H - 70), tag, font=font, fill="#888888")
    
    return np.array(img)


async def gen_audio(text, path):
    try:
        tts = edge_tts.Communicate(text, "uz-UZ-MadinaNeural")
        await tts.save(path)
        return True
    except:
        try:
            tts = edge_tts.Communicate(text, "ru-RU-DariyaNeural")
            await tts.save(path)
            return True
        except:
            try:
                tts = edge_tts.Communicate(text, "en-US-JennyNeural")
                await tts.save(path)
                return True
            except:
                return False


def create_video(quote, author):
    """Video yaratish va output/video.mp4 + output/caption.txt ga saqlash"""
    print("\n🎬 Video yaratilmoqda...")
    print(f"   Matn: {quote[:50]}...")
    print(f"   Muallif: {author}")
    
    # 1. caption.txt ni yaratish (BU MUHIM!)
    caption = f"{quote}\n\n— {author}\n\n#motivatsiya #iqtibos #kunilikiqtibos #motivbot"
    with open("output/caption.txt", "w", encoding="utf-8") as f:
        f.write(caption)
    print(f"   ✅ output/caption.txt yaratildi")
    
    # 2. Audio
    audio_path = "temp_audio.mp3"
    audio_ok = asyncio.run(gen_audio(quote, audio_path))
    
    dur = 5.0
    audio = None
    if audio_ok and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
        try:
            audio = AudioFileClip(audio_path)
            dur = audio.duration
            print(f"   Audio: {dur:.1f}s")
        except:
            audio = None
    
    # 3. Kadrlar
    fps = 24
    total = int(dur * fps) + 24
    
    print(f"   Kadrlar: {total} ta")
    frames = []
    for i in range(total):
        frames.append(make_frame(quote, author, i, total))
        if i % 10 == 0:
            print(f"   {i}/{total}")
    
    # 4. Render
    print("   🎞️ Render...")
    clip = ImageSequenceClip(frames, fps=fps)
    
    if audio:
        clip = clip.set_audio(audio)
    
    clip = clip.fx(fadein, 0.3)
    clip = clip.fadeout(0.5)
    
    output_path = "output/video.mp4"
    print(f"   📁 Saqlanmoqda: {output_path}")
    
    clip.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        fps=fps,
        preset='ultrafast',
        bitrate='3000k'
    )
    
    clip.close()
    if audio and os.path.exists(audio_path):
        os.remove(audio_path)
    
    print(f"✅ Video tayyor!")
    print(f"   Fayl: {output_path}")
    print(f"   Hajmi: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
    print(f"   Caption: output/caption.txt")
    
    return output_path


# =============== ASOSIY ===============
if __name__ == "__main__":
    # facts.json ni o'qish
    try:
        with open("facts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ facts.json xatosi: {e}")
        print("   Test matni bilan ishlayman")
        data = [
            {"quote": "Muvaffaqiyatga erishish uchun birinchi qadam - bu harakat qilishni boshlash!", "author": "MotivBot"},
            {"quote": "Kuniga 1% yaxshilanib boring. Bir yildan so'ng 37 barobar kuchli bo'lasiz!", "author": "James Clear"},
            {"quote": "Orzularingiz sari intiling! Hech qachon taslim bo'lmang.", "author": "Unknown"}
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
    
    print(f"\n📖 Tanlangan iqtibos: {text[:60]}...")
    print(f"✍️  Muallif: {author}")
    
    # Video + caption yaratish
    create_video(text, author)
    
    print("\n✅ Barcha fayllar tayyor:")
    print("   - output/video.mp4")
    print("   - output/caption.txt")
