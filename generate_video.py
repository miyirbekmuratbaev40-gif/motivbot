import json
import random
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from PIL import ImageColor
import numpy as np
from moviepy.editor import *
from moviepy.video.fx.all import fadein, fadeout
import edge_tts
import asyncio

# =============== KONFIGURATSIYA ===============
os.makedirs("output", exist_ok=True)
os.makedirs("fonts", exist_ok=True)

# Instagram Reels o'lchami: 1080x1920 (9:16)
W, H = 1080, 1920

# Ranglar palitrasi (10 xil chiroyli gradient)
COLORS = [
    ["#0f0c29", "#302b63"],  # Kosmik
    ["#ff6b6b", "#ffa500"],  # Quyosh botishi
    ["#00b4db", "#0083b0"],  # Okean
    ["#8e2de2", "#4a00e0"],  # Binafsha
    ["#11998e", "#38ef7d"],  # Yashil
    ["#fc5c7d", "#6a82fb"],  # Pushti-ko'k
    ["#1a1a2e", "#16213e"],  # Tungi
    ["#f7971e", "#ffd200"],  # Oltin
    ["#667eea", "#764ba2"],  # Lavanda
    ["#f12711", "#f5af19"],  # Olov
]


def create_gradient(w, h, color1, color2):
    """Gradient fon yaratish"""
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
    
    # Yulduz effekti (50% extimol)
    if random.random() > 0.5:
        for _ in range(random.randint(15, 40)):
            x = random.randint(0, w)
            y = random.randint(0, h)
            s = random.randint(1, 3)
            br = random.randint(180, 255)
            draw.ellipse([x, y, x + s, y + s], fill=(br, br, br))
    
    return img


def wrap_text(text, font, max_w, draw):
    """Matnni kenglikka moslab o'rash"""
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
    """1 ta kadr yaratish (animatsiya bilan)"""
    # Gradient rang tanlash
    c1, c2 = random.choice(COLORS)
    
    # Fon yaratish
    img = create_gradient(W, H, c1, c2)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    draw = ImageDraw.Draw(img)
    
    # Fontlarni yuklash
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
    
    # Matnni o'rash
    max_w = W - 160
    lines = wrap_text(quote, quote_font, max_w, draw)
    
    # Animatsiya: matn yuqoridan pastga siljiydi
    progress = frame_num / max(total_frames, 1)
    offset = int((1 - progress) * 40)
    
    # Matn markazini hisoblash
    line_h = 70
    total_h = len(lines) * line_h
    start_y = (H - total_h) // 2 - 40 + offset
    
    # Matnni chizish (oq rang + qora kontur)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=quote_font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_h
        
        # Qora kontur
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=quote_font, fill="black")
        # Asosiy oq matn
        draw.text((x, y), line, font=quote_font, fill="white")
    
    # Muallif matni (oltin rangda)
    if author:
        author_text = f"— {author}"
        bbox = draw.textbbox((0, 0), author_text, font=author_font)
        aw = bbox[2] - bbox[0]
        ay = start_y + len(lines) * line_h + 20
        # Qora kontur
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx != 0 or dy != 0:
                    draw.text(((W - aw) // 2 + dx, ay + dy), author_text, font=author_font, fill="black")
        # Oltin rang
        draw.text(((W - aw) // 2, ay), author_text, font=author_font, fill="#FFD700")
    
    # Pastki tag
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
    """Edge-TTS orqali ovoz yaratish"""
    try:
        # O'zbek tili ovozi
        voice = "uz-UZ-MadinaNeural"
        tts = edge_tts.Communicate(text, voice)
        await tts.save(path)
        return True
    except:
        try:
            # Agar o'zbek tili ishlamasa, rus tili
            voice = "ru-RU-DariyaNeural"
            tts = edge_tts.Communicate(text, voice)
            await tts.save(path)
            return True
        except:
            try:
                # Ingliz tili
                voice = "en-US-JennyNeural"
                tts = edge_tts.Communicate(text, voice)
                await tts.save(path)
                return True
            except:
                return False


def create_video(quote, author, output_path):
    """To'liq video yaratish"""
    print(f"🎬 Video yaratilmoqda...")
    print(f"   Matn: {quote[:60]}...")
    print(f"   Muallif: {author}")
    
    # Audio yaratish
    audio_path = "temp_audio.mp3"
    audio_ok = asyncio.run
