import json
import random
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
from moviepy.editor import *
from moviepy.video.fx.all import fadein, fadeout
import edge_tts
import asyncio
import requests
from io import BytesIO

# =============== KONFIGURATSIYA ===============
FONTS_DIR = "fonts"
OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Instagram Reels o'lchami: 1080x1920 (9:16)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Ranglar palitrasi (trenddagi ranglar)
COLOR_PALETTES = [
    # Gradient uchun 2 ta rang
    [("#0f0c29", "#302b63", "#24243e")],  # Kosmik
    [("#ff6b6b", "#ffa500", "#ffd700")],   # Quyosh botishi
    [("#00b4db", "#0083b0", "#00d2ff")],   # Okean
    [("#8e2de2", "#4a00e0", "#7b2ff7")],   # Binafsha
    [("#f12711", "#f5af19", "#f5af19")],   # Olov
    [("#11998e", "#38ef7d", "#11998e")],   # Yashil
    [("#fc5c7d", "#6a82fb", "#fc5c7d")],   # Pushti-ko'k
    [("#1a1a2e", "#16213e", "#0f3460")],   # Tungi
    [("#f7971e", "#ffd200", "#f7971e")],   # Oltin
    [("#667eea", "#764ba2", "#667eea")],   # Lavanda
]

# Fon videolar uchun URL'lar (muqobil: rangli gradient)
BACKGROUND_VIDEOS = []  # Agar fon video qo'shmoqchi bo'lsangiz, URL'larni qo'ying


def create_gradient_background(width, height, colors, direction="vertical"):
    """Chiroyli gradient fon yaratish"""
    from PIL import ImageColor
    
    base = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(base)
    
    r1, g1, b1 = ImageColor.getrgb(colors[0])
    r2, g2, b2 = ImageColor.getrgb(colors[1])
    
    if direction == "vertical":
        for i in range(height):
            ratio = i / height
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
    else:  # diagonal
        for i in range(width):
            for j in range(height):
                ratio = (i + j) / (width + height)
                r = int(r1 * (1 - ratio) + r2 * ratio)
                g = int(g1 * (1 - ratio) + g2 * ratio)
                b = int(b1 * (1 - ratio) + b2 * ratio)
                draw.point((i, j), fill=(r, g, b))
    
    # Yulduz effekti qo'shish (kosmik stil)
    if "kosmik" in str(colors).lower() or random.random() > 0.7:
        for _ in range(random.randint(20, 50)):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            draw.ellipse([x, y, x + size, y + size], 
                        fill=(brightness, brightness, brightness))
    
    return base


def add_text_with_outline(draw, text, position, font, fill_color, outline_color="black", outline_width=3):
    """Matnga kontur qo'shish"""
    x, y = position
    
    # Kontur
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    
    # Asosiy matn
    draw.text((x, y), text, font=font, fill=fill_color)


def wrap_text(text, font, max_width, draw):
    """Matnni kenglikka moslab o'rash"""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines


def create_quote_frame(quote, author, frame_number=0, total_frames=48):
    """Bitta kadr yaratish (harakat animatsiyasi bilan)"""
    
    # Gradient ranglar palitrasini tanlash
    palette = random.choice(COLOR_PALETTES)[0]
    
    # Fon yaratish
    bg = create_gradient_background(VIDEO_WIDTH, VIDEO_HEIGHT, palette, 
                                     "vertical" if frame_number % 2 == 0 else "diagonal")
    
    # Bir oz xira qilish (blur) - chuqurlik effekti
    bg = bg.filter(ImageFilter.GaussianBlur(radius=2))
    
    # Nozik naqsh qo'shish
    overlay = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Geometrik shakllar (doiralar)
    for _ in range(random.randint(3, 6)):
        cx = random.randint(100, VIDEO_WIDTH - 100)
        cy = random.randint(100, VIDEO_HEIGHT - 100)
        r = random.randint(50, 200)
        alpha = random.randint(10, 30)
        overlay_draw.ellipse([cx - r, cy - r, cx + r, cy + r], 
                           fill=(255, 255, 255, alpha))
    
    bg = Image.alpha_composite(bg.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(bg)
    
    # Fontlarni yuklash
    try:
        # Asosiy quote uchun katta font
        quote_font_size = 65
        quote_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Bold.ttf"), quote_font_size)
        # Muallif uchun kichik font
        author_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Italic.ttf"), 40)
        # 'MotivBot' tagi uchun
        tag_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Regular.ttf"), 25)
    except:
        # Agar font topilmasa, default
        quote_font = ImageFont.load_default()
        author_font = ImageFont.load_default()
        tag_font = ImageFont.load_default()
    
    # Matnni o'rash
    max_text_width = VIDEO_WIDTH - 200  # 100px chap va o'ngdan margin
    lines = wrap_text(quote, quote_font, max_text_width, draw)
    
    # Animatsiya parametrlari (matn harakati)
    animation_offset = 0
    if total_frames > 0:
        # Matn yuqoridan pastga siljiydi
        progress = frame_number / total_frames
        animation_offset = int((1 - progress) * 50)  # 50px siljish
    
    # Matn boshlanish nuqtasi
    total_text_height = len(lines) * 80  # Har bir satr balandligi
    start_y = (VIDEO_HEIGHT - total_text_height) // 2 - 50 + animation_offset
    
    # " (qo'shtirnoq) belgisi - dekorativ
    try:
        deco_font = ImageFont.truetype(os.path.join(FONTS_DIR, "Roboto-Bold.ttf"), 120)
    except:
        deco_font = ImageFont.load_default()
    
    quote_color = "#FFFFFF"  # Oq matn
    outline_color = "#000000"  # Qora kontur
    
    # Har bir satrni chizish
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=quote_font)
        line_width = bbox[2] - bbox[0]
        x = (VIDEO_WIDTH - line_width) // 2
        
        y = start_y + i * 80
        add_text_with_outline(draw, line, (x, y), quote_font, quote_color, outline_color, 2)
    
    # Muallif matni
    author_text = f"— {author}" if author else ""
    if author_text:
        bbox = draw.textbbox((0, 0), author_text, font=author_font)
        aw = bbox[2] - bbox[0]
        author_y = start_y + len(lines) * 80 + 30
        add_text_with_outline(draw, author_text, 
                            ((VIDEO_WIDTH - aw) // 2, author_y), 
                            author_font, "#FFD700", outline_color, 2)  # Oltin rang
    
    # Pastki tag: @motivbot yoki boshqa
    tag_text = "@motivbot"
    bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tw = bbox[2] - bbox[0]
    add_text_with_outline(draw, tag_text, 
                        ((VIDEO_WIDTH - tw) // 2, VIDEO_HEIGHT - 80), 
                        tag_font, "#AAAAAA", outline_color, 1)
    
    return bg


def create_animated_frame(quote, author, frame_num, total_frames):
    """Animatsiyali kadr yaratish"""
    img = create_quote_frame(quote, author, frame_num, total_frames)
    return np.array(img)


async def generate_audio(text, output_path):
    """Edge-TTS orqali ovoz yaratish"""
    try:
        # Ovoz sozlamalari: tez va ifodali
        voice = "uz-UZ-MadinaNeural"  # O'zbek tili ovozi
        # Agar o'zbek tili ishlamasa, rus yoki ingliz:
        # voice = "ru-RU-DariyaNeural" 
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"Ovoz yaratishda xatolik: {e}")
        return False


def create_video(quote, author, output_path="motivational_reel.mp4"):
    """To'liq video yaratish"""
    
    print(f"🎬 Video yaratilmoqda: {quote[:50]}...")
    
    # Audio yaratish
    audio_path = "temp_audio.mp3"
    asyncio.run(generate_audio(quote, audio_path))
    
    # Audio davomiyligini aniqlash
    try:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
    except:
        audio_duration = 5  # Agar audio bo'lmasa, default 5 sek
    
    # Video davomiyligi (audio + 1 sekund pauza)
    video_duration = audio_duration + 1.5
    fps = 24
    total_frames = int(video_duration * fps)
    
    print(f"   Audio: {audio_duration:.1f}s, Video: {video_duration:.1f}s, Frames: {total_frames}")
    
    # Kadrlarni yaratish
    frames = []
    for i in range(total_frames):
        frame = create_animated_frame(quote, author, i, total_frames)
        frames.append(frame)
        if i % 10 == 0:
            print(f"   Progress: {i}/{total_frames} frames")
    
    # Videoni yaratish
    video_clip = ImageSequenceClip(frames, fps=fps)
    
    # Ovoz qo'shish
    if os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            # Video va audio uzunligini moslash
            if audio_clip.duration > video_clip.duration:
                audio_clip = audio_clip.subclip(0, video_clip.duration)
            video_clip = video_clip.set_audio(audio_clip)
        except Exception as e:
            print(f"   Audio qo'shishda xatolik: {e}")
    
    # Transition effektlari
    video_clip = video_clip.fx(fadein, 0.3, None)  # Kirish fade
    video_clip = video_clip.fadeout(0.5)  # Chiqish fade
    
    # Videoni saqlash
    print(f"   💾 Video saqlanmoqda: {output_path}")
    video_clip.write_videofile(
        output_path, 
        codec='libx264', 
        audio_codec='aac',
        fps=fps,
        preset='medium',
        bitrate='5000k',
        threads=4
    )
    
    # Tozalash
    video_clip.close()
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    print(f"✅ Video tayyor: {output_path}")
    return output_path


# =============== ASOSIY ISHGA TUSHIRISH ===============
if __name__ == "__main__":
    # facts.json dan iqtibosni o'qish
    with open("facts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    quotes = data.get("quotes", data.get("facts", data))
    
    if isinstance(quotes, list):
        quote_data = random.choice(quotes)
        if isinstance(quote_data, dict):
            text = quote_data.get("quote", quote_data.get("text", quote_data.get("fact", "")))
            author = quote_data.get("author", "Unknown")
        else:
            text = str(quote_data)
            author = "Unknown"
    else:
        text = str(quotes)
        author = "Unknown"
    
    # Unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"reel_{timestamp}.mp4")
    
    # Video yaratish
    create_video(text, author, output_path)
