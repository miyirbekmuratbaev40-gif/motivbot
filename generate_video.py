"""
generate_video.py (v4 - "Curiosity Gap" tuzilmasi: savol -> kutish -> javob)
------------------------------------------------------------------------------
Qisqa videolar (Reels/Shorts) virusliligi bo'yicha isbotlangan psixologik
tamoyilga asoslangan: avval qiziqtiruvchi SAVOL beriladi, tomoshabin javobni
bilish uchun oxirigacha tomosha qiladi (watch-time yuqori bo'ladi), so'ng
kuchli, aniq JAVOB beriladi.

Oqim:
1) Tasodifiy savol+javob juftligini tanlaydi (facts.json)
2) Ikkala qismni alohida o'zbekcha ovozga aylantiradi (Edge TTS)
   va orasiga qisqa pauza qo'yib birlashtiradi
3) Pexels'dan mavzuga mos bepul stock-video (fon) yuklab oladi
4) Ekranda ham avval SAVOL, so'ng JAVOB ko'rinadi (ovoz bilan sinxron)
5) ffmpeg orqali hammasini birlashtirib, 1080x1920 Reels video yaratadi

Kerakli muhit o'zgaruvchisi:
    PEXELS_API_KEY   (bepul, pexels.com/api dan olinadi)
"""

import asyncio
import json
import os
import random
import subprocess
import sys
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
PAUSE_SECONDS = 0.9   # savol va javob orasidagi "kutish" pauzasi

# Zaxira mavzular - agar faktning o'z "theme" maydoni topilmasa ishlatiladi
FALLBACK_THEMES = [
    "space galaxy stars",
    "ocean underwater deep",
    "wildlife animals nature",
    "aurora borealis northern lights",
]


# ---------------------------------------------------------------------------
# Fakt tanlash
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Ovoz (ikki bosqichli: savol + pauza + javob)
# ---------------------------------------------------------------------------

def get_audio_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def generate_speech_two_part(hook_text, reveal_text):
    import edge_tts

    voice = random.choice(VOICES)
    hook_raw = os.path.join(OUTPUT_DIR, "hook_raw.mp3")
    reveal_raw = os.path.join(OUTPUT_DIR, "reveal_raw.mp3")
    hook_path = os.path.join(OUTPUT_DIR, "hook.wav")
    reveal_path = os.path.join(OUTPUT_DIR, "reveal.wav")
    silence_path = os.path.join(OUTPUT_DIR, "silence.wav")
    combined_path = os.path.join(OUTPUT_DIR, "audio.mp3")

    async def _run():
        # Rate biroz tabiiyroq eshitilishi uchun -3% dan -1% ga o'zgartirildi -
        # ortiqcha sekinlashtirish ovozni "cho'zilgan/robot" kabi eshittiradi
        await edge_tts.Communicate(hook_text, voice, rate="-1%").save(hook_raw)
        await edge_tts.Communicate(reveal_text, voice, rate="-1%").save(reveal_raw)

    asyncio.run(_run())

    # Har bir segmentni bir xil formatga (44.1kHz, mono, PCM WAV) qayta kodlaymiz -
    # turli MP3 header/bitrate parametrlari concat vaqtida jarangsizlik/click
    # tovushlarga sabab bo'lishi mumkin edi.
    for src, dst in [(hook_raw, hook_path), (reveal_raw, reveal_path)]:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-ar", "44100", "-ac", "1", "-acodec", "pcm_s16le", dst],
            check=True, capture_output=True,
        )

    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", str(PAUSE_SECONDS), "-acodec", "pcm_s16le", silence_path],
        check=True, capture_output=True,
    )

    list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_path, "w") as f:
        f.write(f"file '{os.path.abspath(hook_path)}'\n")
        f.write(f"file '{os.path.abspath(silence_path)}'\n")
        f.write(f"file '{os.path.abspath(reveal_path)}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
         "-acodec", "libmp3lame", "-q:a", "2", combined_path],
        check=True, capture_output=True,
    )

    hook_dur = get_audio_duration(hook_path)
    reveal_dur = get_audio_duration(reveal_path)

    print(f"Ovoz yaratildi ({voice}): savol={hook_dur:.1f}s, pauza={PAUSE_SECONDS}s, javob={reveal_dur:.1f}s")
    return combined_path, hook_dur, reveal_dur


# ---------------------------------------------------------------------------
# Fon video (Pexels)
# ---------------------------------------------------------------------------

def fetch_background_video(out_path, theme=None, min_duration=6):
    """
    Fon videoni faktning o'z mavzusiga ("theme" maydoni, facts.json'da) mos
    ravishda Pexels'dan qidiradi - shunda fon har doim aytilayotgan gap bilan
    mantiqan bog'liq bo'ladi. Bundan tashqari, iloji boricha video kamida
    "min_duration" soniya davom etadigan klipni tanlaydi - juda qisqa klip
    tez-tez "loop" bo'lib, sun'iy va zerikarli ko'rinishning oldini olish uchun.
    """
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        print("OGOHLANTIRISH: PEXELS_API_KEY topilmadi, gradient fon ishlatiladi.")
        return None

    if not theme:
        theme = random.choice(FALLBACK_THEMES)
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": api_key}
    params = {"query": theme, "orientation": "portrait", "per_page": 25, "size": "medium"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            fallback_theme = random.choice(FALLBACK_THEMES)
            print(f"Pexels'da '{theme}' uchun natija topilmadi, '{fallback_theme}' bilan sinaymiz.")
            params["query"] = fallback_theme
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            if not videos:
                print("Zaxira mavzu ham natija bermadi, gradient fon ishlatiladi.")
                return None

        # Imkon qadar uzunroq (min_duration dan katta) klip tanlaymiz - qisqa
        # klip loop qilinganda ko'zga tashlanadigan, zerikarli takrorlanish beradi.
        long_enough = [v for v in videos if (v.get("duration") or 0) >= min_duration]
        pool = long_enough if long_enough else videos
        # Eng uzunlaridan tasodifiy tanlaymiz (faqat bittasini emas)
        pool_sorted = sorted(pool, key=lambda v: v.get("duration") or 0, reverse=True)
        video = random.choice(pool_sorted[:5]) if len(pool_sorted) >= 5 else random.choice(pool_sorted)

        files = sorted(video["video_files"], key=lambda f: abs((f.get("width") or 0) - WIDTH))
        best = next((f for f in files if (f.get("height") or 0) > (f.get("width") or 0)), files[0])

        video_resp = requests.get(best["link"], timeout=60)
        video_resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(video_resp.content)

        actual_dur = video.get("duration", "?")
        print(f"Fon video yuklandi (mavzu: '{theme}', davomiyligi: {actual_dur}s): {out_path}")
        return out_path
    except Exception as e:
        print(f"OGOHLANTIRISH: Pexels'dan video yuklab bo'lmadi ({e}), gradient fon ishlatiladi.")
        return None


# ---------------------------------------------------------------------------
# Matn overlay - ikkita alohida kadr: SAVOL va JAVOB
# ---------------------------------------------------------------------------

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


def _fit_lines(draw, text, base_size, max_width, max_lines=6, min_size=36):
    font_size = base_size
    font = ImageFont.truetype(FONT_BOLD, font_size)
    lines = wrap_text(draw, text, font, max_width)
    while len(lines) > max_lines and font_size > min_size:
        font_size -= 4
        font = ImageFont.truetype(FONT_BOLD, font_size)
        lines = wrap_text(draw, text, font, max_width)
    return lines, font, font_size


def _draw_badge(draw, text, center_y, bg_color, text_color=(20, 20, 20, 255)):
    badge_font = ImageFont.truetype(FONT_BOLD, 50)
    w = draw.textlength(text, font=badge_font)
    draw.rounded_rectangle(
        [(WIDTH // 2 - w / 2 - 28, center_y - 10), (WIDTH // 2 + w / 2 + 28, center_y + 62)],
        radius=18, fill=bg_color,
    )
    draw.text((WIDTH // 2 - w / 2, center_y), text, font=badge_font, fill=text_color)
    return center_y + 62


def render_hook_overlay(hook_text):
    """Video boshida ko'rinadigan kadr: faqat qiziqtiruvchi savol."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_width = WIDTH - 160

    lines, font, font_size = _fit_lines(draw, hook_text, 72, max_width, max_lines=6)
    line_height = int(font_size * 1.35)
    badge_h = 90
    total_h = badge_h + 30 + line_height * len(lines)
    box_top = (HEIGHT - total_h) // 2 - 60

    draw.rectangle([(0, box_top - 50), (WIDTH, box_top + total_h + 60)], fill=(0, 0, 0, 160))

    y_after_badge = _draw_badge(draw, "QANI TOPING-CHI?", box_top, (255, 200, 40, 235))

    start_y = y_after_badge + 30
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = (WIDTH - w) // 2
        y = start_y + i * line_height
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 170))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "overlay_hook.png")
    img.save(path)
    return path


def render_reveal_overlay(reveal_text):
    """Javob paytida ko'rinadigan kadr: aniq javob + izohga chorlash."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_width = WIDTH - 160

    lines, font, font_size = _fit_lines(draw, reveal_text, 66, max_width, max_lines=7)
    line_height = int(font_size * 1.35)
    badge_h = 90
    total_h = badge_h + 30 + line_height * len(lines)
    box_top = (HEIGHT - total_h) // 2 - 60

    draw.rectangle([(0, box_top - 50), (WIDTH, box_top + total_h + 60)], fill=(0, 0, 0, 170))

    y_after_badge = _draw_badge(draw, "JAVOB ✅", box_top, (90, 220, 130, 235))

    start_y = y_after_badge + 30
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = (WIDTH - w) // 2
        y = start_y + i * line_height
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 170))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    # Pastda doimiy ko'rinadigan like/obuna chaqirig'i (caption o'qimaydiganlar uchun ham)
    cta_font = ImageFont.truetype(FONT_BOLD, 42)
    cta_text = "❤️ Layk  •  🔔 Obuna  •  💬 Izoh"
    cw = draw.textlength(cta_text, font=cta_font)
    cta_y = HEIGHT - 200
    draw.rounded_rectangle(
        [(WIDTH // 2 - cw / 2 - 30, cta_y - 16), (WIDTH // 2 + cw / 2 + 30, cta_y + 56)],
        radius=16, fill=(0, 0, 0, 150),
    )
    draw.text((WIDTH // 2 - cw / 2, cta_y), cta_text, font=cta_font, fill=(255, 255, 255, 255))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "overlay_reveal.png")
    img.save(path)
    return path


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


# ---------------------------------------------------------------------------
# Hammasini ffmpeg bilan birlashtirish (vaqtga qarab overlay almashtiriladi)
# ---------------------------------------------------------------------------

def compose_video(background_path, hook_overlay, reveal_overlay, audio_path,
                   hook_dur, reveal_start, duration, is_video_bg):
    out_path = os.path.join(OUTPUT_DIR, "video.mp4")
    fade_out_start = max(duration - 0.6, 0)

    if is_video_bg:
        bg_input = ["-stream_loop", "-1", "-i", background_path]
        # Video fonga ham sekin zoom qo'shamiz - manba klip harakatsiz/statik
        # bo'lsa ham, natija ko'zga "jonli" ko'rinishi uchun.
        big_w, big_h = int(WIDTH * 1.3), int(HEIGHT * 1.3)
        bg_filter = (
            f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase,"
            f"crop={big_w}:{big_h},"
            f"zoompan=z='min(zoom+0.0004,1.1)':d={int(duration * 30)}:s={WIDTH}x{HEIGHT}:fps=30,"
            f"eq=brightness=-0.04,"
            f"fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out_start}:d=0.6"
        )
    else:
        bg_input = ["-loop", "1", "-i", background_path]
        bg_filter = (
            f"zoompan=z='min(zoom+0.0007,1.15)':d={int(duration * 30)}:s={WIDTH}x{HEIGHT}:fps=30,"
            f"fade=t=in:st=0:d=0.6,fade=t=out:st={fade_out_start}:d=0.6"
        )

    filter_complex = (
        f"[0:v]{bg_filter}[bg];"
        f"[bg][1:v]overlay=0:0:enable='between(t,0,{hook_dur})'[bg2];"
        f"[bg2][2:v]overlay=0:0:enable='gte(t,{reveal_start})'[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        *bg_input,
        "-i", hook_overlay,
        "-i", reveal_overlay,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "3:a",
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


# ---------------------------------------------------------------------------
# Asosiy oqim
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    facts = load_facts()
    state = load_state()
    fact, state = pick_fact(facts, state)
    save_state(state)

    audio_path, hook_dur, reveal_dur = generate_speech_two_part(fact["hook"], fact["reveal"])
    reveal_start = hook_dur + PAUSE_SECONDS
    duration = reveal_start + reveal_dur + 1.2  # javobdan keyin "nafas" vaqti

    bg_video_path = os.path.join(OUTPUT_DIR, "background.mp4")
    fetched = fetch_background_video(bg_video_path, theme=fact.get("theme"), min_duration=duration)
    is_video_bg = fetched is not None
    background_path = fetched if fetched else render_gradient_fallback()

    hook_overlay = render_hook_overlay(fact["hook"])
    reveal_overlay = render_reveal_overlay(fact["reveal"])

    video_path = compose_video(
        background_path, hook_overlay, reveal_overlay, audio_path,
        hook_dur, reveal_start, duration, is_video_bg,
    )

    caption = (
        f"🤔 {fact['hook']}\n\n"
        f"👇 Javobni pastdan o'qing (yoki videoni oxirigacha tomosha qiling!)\n\n"
        f"✅ {fact['reveal']}\n\n"
        f"Bu faktni bilarmidingiz? Izohga yozing! 👇\n"
        f"❤️ Layk qiling  •  🔔 Obuna bo'ling  •  📤 Do'stingizga yuboring\n\n"
        f"#qiziqarlifaktlar #bilasizmi #fakt #ilmiyfaktlar #kosmosfaktlari #uzbekfaktlar #dunyo #tabiat #fan #qiziqarli"
    )
    with open(os.path.join(OUTPUT_DIR, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"Video tayyor: {video_path} (jami davomiylik: {duration:.1f}s)")
    print(f"Caption:\n{caption}")


if __name__ == "__main__":
    main()
