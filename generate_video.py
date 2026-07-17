import json
import random
import os
import sys
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import edge_tts

try:
    from moviepy.editor import *
    from moviepy.video.fx.all import fadein, fadeout
except ImportError:
    print("❌ moviepy o'rnatilmagan. O'rnatish: pip install moviepy")
    sys.exit(1)

# =============== SOZLAMALAR ===============
os.makedirs("output", exist_ok=True)
os.makedirs("fonts", exist_ok=True)

W, H = 1080, 1920  # Instagram Reels

# 12 xil premium gradient ranglar
COLORS = [
    ["#0f0c29", "#302b63"],  # Galaktika
    ["#ff6b6b", "#ffa500"],  # Quyosh botishi
    ["#00b4db", "#0083b0"],  # Moviy okean
    ["#8e2de2", "#4a00e0"],  # Binafsha
    ["#11998e", "#38ef7d"],  # Zumrad
    ["#fc5c7d", "#6a82fb"],  # Pushti-ko'k
    ["#1a1a2e", "#16213e"],  # Tungi osmon
    ["#f7971e", "#ffd200"],  # Oltin
    ["#667eea", "#764ba2"],  # Lavanda
    ["#f12711", "#f5af19"],  # Olov
    ["#0cebeb", "#20e3b2"],  # Turkuaz
    ["#e65c00", "#f9d423"],  # Amber
]


def create_gradient(w, h, c1, c2):
    """Gradient fon yaratish"""
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
    
    # Yulduz effekti
    if random.random() > 0.4:
        for _ in range(random.randint(20, 50)):
            x = random.randint(0, w)
            y = random.randint(0, h)
            s = random.randint(1, 4)
            br = random.randint(180, 255)
            draw.ellipse([x, y, x + s, y + s], fill=(br, br, br))
    
    return img


def wrap_text(text, font, max_w, draw):
    """Matnni ekran kengligiga moslab o'rash"""
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
    """Bir kadr yaratish"""
    # Gradient tanlash
    c1, c2 = random.choice(COLORS)
    
    # Fon
    img = create_gradient(W, H, c1, c2)
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    draw = ImageDraw.Draw(img)
    
    # Font yuklash
    font = ImageFont.load_default()
    font_paths = [os.path.join("fonts", f) for f in os.listdir("fonts") 
                  if f.endswith((".ttf", ".otf"))] if os.path.exists("fonts") else []
    
    if font_paths:
        try:
            font = ImageFont.truetype(random.choice(font_paths), 56)
        except:
            font = ImageFont.load_default()
    
    # Matnni o'rash
    max_w = W - 180
    lines = wrap_text(quote, font, max_w, draw)
    
    # Animatsiya: yuqoridan pastga siljish
    progress = frame_num / max(total_frames, 1)
    offset = int((1 - progress) * 50)
    
    line_h = 72
    total_h = len(lines) * line_h
    start_y = (H - total_h) // 2 - 60 + offset
    
    # Matn chizish (oq + qora kontur)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        y = start_y + i * line_h
        
        # Kontur
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 180))
        # Asosiy matn
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
    
    # Muallif (oltin rangda)
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
    
    # Pastki tag
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
    """Edge-TTS orqali ovoz yaratish"""
    voices = [
        "uz-UZ-MadinaNeural",
        "ru-RU-DariyaNeural",
        "en-US-JennyNeural",
        "en-GB-SoniaNeural"
    ]
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
    """To'liq video yaratish"""
    print("\n" + "="*50)
    print("🎬 VIDEO YARATISH BOSHLANDI")
    print("="*50)
    print(f"📝 Matn: {quote[:80]}...")
    print(f"✍️  Muallif: {author}")
    print(f"📁 Chiqish: {output_path}")
    print("="*50)
    
    # 1️⃣ CAPTION FAYL YARATISH
    caption = f"{quote}\n\n— {author}\n\n#motivatsiya #iqtibos #kunilikiqtibos #motivbot_uz #o_zbekcha #motivatsion"
    with open("output/caption.txt", "w", encoding="utf-8") as f:
        f.write(caption)
    print("✅ caption.txt yaratildi")
    
    # 2️⃣ AUDIO YARATISH
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
            audio = None
    
    # 3️⃣ KADRLAR YARATISH
    fps = 24
    total_frames = int(dur * fps) + 24  # +1 soniya qo'shimcha
    
    print(f"🖼️  Kadrlar yaratilmoqda: {total_frames} ta")
    frames = []
    
    for i in range(total_frames):
        frame = make_frame(quote, author, i, total_frames)
        frames.append(frame)
        if i % 15 == 0 or i == total_frames - 1:
            print(f"   Progress: {i+1}/{total_frames} ({(i+1)/total_frames*100:.0f}%)")
    
    # 4️⃣ VIDEOGA JOYLASH
    print("🎞️ Video render qilinmoqda...")
    clip = ImageSequenceClip(frames, fps=fps)
    
    if audio:
        clip = clip.set_audio(audio)
    
    # Effektlar
    clip = clip.fx(fadein, 0.3)
    clip = clip.fadeout(0.5)
    
    # Saqlash
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
    
    # Natija
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print("="*50)
    print(f"✅ VIDEO TAYYOR!")
    print(f"   📍 {output_path}")
    print(f"   📦 {size_mb:.1f} MB")
    print(f"   ⏱️  {dur:.1f} sek")
    print(f"   📝 output/caption.txt")
    print("="*50)
    
    return output_path


if __name__ == "__main__":
    # Ma'lumotlarni yuklash
    try:
        with open("facts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"⚠️ facts.json yuklanmadi: {e}")
        print("📚 Standart iqtiboslar bilan ishlayman")
        data = [
            {"quote": "Muvaffaqiyatga erishishning kaliti - bu harakat qilishni boshlash!", "author": "MotivBot"},
            {"quote": "Kuniga 1% yaxshilanib boring. Bir yildan so'ng 37 barobar kuchli bo'lasiz!", "author": "James Clear"},
            {"quote": "Orzularingiz sari intiling! Hech qachon kech emas.", "author": "Unknown"},
            {"quote": "Eng katta xato - hech nima qilmaslikdir.", "author": "Elon Musk"},
            {"quote": "Muvaffaqiyat - bu muvaffaqiyatsizlikdan muvaffaqiyatsizlikka o'tib, ishtiyoqni yo'qotmaslikdir.", "author": "Winston Churchill"},
        ]
    
    # Ma'lumot turini aniqlash
    if isinstance(data, list):
        quotes = data
    elif isinstance(data, dict):
        quotes = data.get("quotes", data.get("facts", data))
        if isinstance(quotes, dict):
            quotes = list(quotes.values())
    else:
        quotes = [{"quote": str(data), "author": "Unknown"}]
    
    # Tasodifiy iqtibos
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
    
    print(f"\n📖 Tanlangan iqtibos: {text}")
    print(f"✍️  Muallif: {author}")
    
    # Video yaratish
    create_video(text, author)
