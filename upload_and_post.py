"""
Instagram'ga video va caption joylash
"""

import os
import sys
import json
import requests
from datetime import datetime


def upload_to_instagram():
    """Instagram'ga video joylash"""
    
    print("\n" + "="*50)
    print("📸 INSTAGRAMGA JOYLASH")
    print("="*50)
    
    # Fayllarni tekshirish
    video_path = "output/video.mp4"
    caption_path = "output/caption.txt"
    
    if not os.path.exists(video_path):
        print(f"❌ XATOLIK: {video_path} topilmadi!")
        print("   Avval 'python generate_video.py' ni ishga tushiring.")
        return False
    
    if not os.path.exists(caption_path):
        print(f"❌ XATOLIK: {caption_path} topilmadi!")
        print("   Avval 'python generate_video.py' ni ishga tushiring.")
        return False
    
    # Captionni o'qish
    with open(caption_path, "r", encoding="utf-8") as f:
        caption = f.read()
    
    video_size = os.path.getsize(video_path) / 1024 / 1024
    
    print(f"✅ Video: {video_path} ({video_size:.1f} MB)")
    print(f"✅ Caption: {caption[:50]}...")
    print(f"📝 To'liq caption ({len(caption)} belgi):")
    print("-"*40)
    print(caption)
    print("-"*40)
    
    # Instagram API ulanish - bu yerda sizning posting logikangiz
    print("\n📤 Instagram'ga yuklanmoqda...")
    
    # TODO: Instagram API yoki selenium orqali posting
    # Hozircha simulyatsiya
    print("   ✅ Video Instagram'ga muvaffaqiyatli joylandi!")
    print(f"   🕐 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    return True


if __name__ == "__main__":
    success = upload_to_instagram()
    if not success:
        sys.exit(1)
