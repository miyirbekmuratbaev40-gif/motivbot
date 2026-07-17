import json
import random
import os
import sys
import asyncio
import subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import edge_tts

# filmpy ni import qilish
try:
    from moviepy.editor import ImageSequenceClip, AudioFileClip
    from moviepy.video.fx.all import fadein, fadeout
except ImportError as e:
    print(f"❌ moviepy: {e}")
    print("   pip install moviepy==1.0.3 imageio==2.34.0 imageio-ffmpeg==0.5.1")
    sys.exit(1)

# ============ SOZLAMALAR ============
os.makedirs("output", exist_ok=True)
os.makedirs("fonts", exist_ok=True)

W, H = 1080, 1920

COLORS = [
    ["#0f0c29","#302b63"], ["#ff6b6b","#ffa500"], ["#00b4db","#0083b0"],
    ["#8e2de2","#4a00e0"], ["#11998e","#38ef7d"], ["#fc5c7d","#6a82fb"],
    ["#1a1a2e","#16213e"], ["#f7971e","#ffd200"], ["#667eea","#764ba2"],
    ["#f12711","#f5af19"], ["#0cebeb","#20e3b2"], ["#e65c00","#f9d423"],
]


def create_gradient(w, h, c1, c2):
    img = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(img)
    r1,g1,b1 = tuple(int(c1[i:i+2],16) for i in (1,3,5))
    r2,g2,b2 = tuple(int(c2[i:i+2],16) for i in (1,3,5))
    for i in range(h):
        r = int(r1*(1-i/h) + r2*(i/h))
        g = int(g1*(1-i/h) + g2*(i/h))
        b = int(b1*(1-i/h) + b2*(i/h))
        draw.line([(0,i),(w,i)], fill=(r,g,b))
    if random.random() > 0.4:
        for _ in range(random.randint(20,50)):
            x,y,s=random.randint(0,w),random.randint(0,h),random.randint(1,4)
            br=random.randint(180,255)
            draw.ellipse([x,y,x+s,y+s], fill=(br,br,br))
    return img


def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = cur + " " + word if cur else word
        bbox = draw.textbbox((0,0), test, font=font)
        if bbox[2]-bbox[0] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines


def make_frame(quote, author, fnum, total):
    c1,c2 = random.choice(COLORS)
    img = create_gradient(W,H,c1,c2).filter(ImageFilter.GaussianBlur(radius=2))
    draw = ImageDraw.Draw(img)
    
    font = ImageFont.load_default()
    fps = [os.path.join("fonts",f) for f in os.listdir("fonts") if f.endswith((".ttf",".otf"))]
    if fps:
        try: font = ImageFont.truetype(random.choice(fps), 56)
        except: pass
    
    lines = wrap_text(quote, font, W-180, draw)
    offset = int((1 - fnum/max(total,1)) * 50)
    line_h, total_h = 72, len(lines)*72
    start_y = (H - total_h)//2 - 60 + offset
    
    for i,line in enumerate(lines):
        bbox = draw.textbbox((0,0), line, font=font)
        lw,x = bbox[2]-bbox[0], (W-(bbox[2]-bbox[0]))//2
        y = start_y + i*line_h
        for dx in range(-3,4):
            for dy in range(-3,4):
                if dx!=0 or dy!=0:
                    draw.text((x+dx,y+dy), line, font=font, fill="black")
        draw.text((x,y), line, font=font, fill="white")
    
    if author and author!="Unknown":
        at = f"— {author}"
        bbox = draw.textbbox((0,0), at, font=font)
        aw,ay = bbox[2]-bbox[0], start_y + len(lines)*line_h + 30
        for dx in range(-2,3):
            for dy in range(-2,3):
                if dx!=0 or dy!=0:
                    draw.text(((W-aw)//2+dx,ay+dy), at, font=font, fill="black")
        draw.text(((W-aw)//2,ay), at, font=font, fill="#FFD700")
    
    tag = "@motivbot_uz"
    bbox = draw.textbbox((0,0), tag, font=font)
    tw = bbox[2]-bbox[0]
    for dx in range(-1,2):
        for dy in range(-1,2):
            if dx!=0 or dy!=0:
                draw.text(((W-tw)//2+dx,H-90+dy), tag, font=font, fill="black")
    draw.text(((W-tw)//2,H-90), tag, font=font, fill="#CCCCCC")
    
    return np.array(img)


async def gen_audio(text, path):
    for v in ["uz-UZ-MadinaNeural","ru-RU-DariyaNeural","en-US-JennyNeural"]:
        try:
            await edge_tts.Communicate(text,v).save(path)
            if os.path.getsize(path)>500: return True
        except: pass
    return False


def create_video(quote, author, out="output/video.mp4"):
    print(f"\n🎬 Video: {quote[:60]}... | Muallif: {author}")
    
    # Caption
    c = f"{quote}\n\n— {author}\n\n#motivatsiya #iqtibos #kunilikiqtibos #motivbot_uz"
    with open("output/caption.txt","w",encoding="utf-8") as f: f.write(c)
    print("✅ caption.txt")
    
    # Audio
    ap = "temp_audio.mp3"
    print("🎵 Audio...")
    ok = asyncio.run(gen_audio(quote, ap))
    dur, audio = 5.0, None
    if ok and os.path.exists(ap):
        try:
            audio = AudioFileClip(ap)
            dur = audio.duration
            print(f"✅ Audio: {dur:.1f}s")
        except: pass
    
    # Kadrlar
    fps, total = 24, int(dur*24)+24
    print(f"🖼️ Kadrlar: {total}")
    frames = [make_frame(quote,author,i,total) for i in range(total)]
    
    # Render
    print("🎞️ Render...")
    clip = ImageSequenceClip(frames, fps=fps)
    if audio: clip = clip.set_audio(audio)
    clip = clip.fx(fadein,0.3).fadeout(0.5)
    
    os.makedirs(os.path.dirname(out), exist_ok=True)
    clip.write_videofile(out, codec='libx264', audio_codec='aac', fps=fps,
                         preset='ultrafast', bitrate='3000k', logger=None)
    clip.close()
    if audio and os.path.exists(ap): os.remove(ap)
    
    mb = os.path.getsize(out)/1024/1024
    print(f"✅ Video: {out} ({mb:.1f}MB, {dur:.1f}s)")
    return out


if __name__ == "__main__":
    try:
        with open("facts.json","r",encoding="utf-8") as f: data = json.load(f)
    except:
        data = [{"quote":"Muvaffaqiyat kaliti - harakat!","author":"MotivBot"},
                {"quote":"Kuniga 1% yaxshilan. 1 yilda 37x kuchli!","author":"James Clear"},
                {"quote":"Orzularing sari intil!","author":"Unknown"}]
    
    if isinstance(data,list): quotes = data
    elif isinstance(data,dict): quotes = data.get("quotes",data.get("facts",data))
    else: quotes = [{"quote":str(data),"author":"Unknown"}]
    
    q = random.choice(quotes) if quotes else {"quote":"Muvaffaqiyat!","author":"MotivBot"}
    text = q.get("quote",q.get("text",q.get("fact","Test")))
    author = q.get("author","Unknown")
    
    print(f"\n📖 {text[:80]}")
    print(f"✍️ {author}")
    create_video(text, author)
