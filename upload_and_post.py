import os, sys

video_path = "output/video.mp4"
caption_path = "output/caption.txt"

print("\n📸 INSTAGRAMGA JOYLASH")
print("="*40)

if not os.path.exists(video_path):
    print("❌ Video topilmadi!")
    sys.exit(1)

if not os.path.exists(caption_path):
    print("❌ Caption topilmadi!")
    sys.exit(1)

with open(caption_path, "r", encoding="utf-8") as f:
    caption = f.read()

username = os.environ.get("INSTAGRAM_USERNAME")
password = os.environ.get("INSTAGRAM_PASSWORD")

if not username or not password:
    print("⚠️ Instagram login topilmadi!")
    print("   GitHub Secrets ga qo'shing:")
    print("   - INSTAGRAM_USERNAME")
    print("   - INSTAGRAM_PASSWORD")
    print("✅ Video va caption tayyor, lekin Instagramga yuklanmadi")
    sys.exit(0)

try:
    from instagrapi import Client
    cl = Client()
    cl.login(username, password)
    print("✅ Instagram'ga kirdi")
    
    result = cl.clip_upload(video_path, caption=caption)
    print(f"✅ Yuklandi! ID: {result.id}")
    print(f"🔗 https://www.instagram.com/reel/{result.code}/")
    
except Exception as e:
    print(f"❌ Xatolik: {e}")
    print("✅ Video va caption tayyor, lekin Instagramga yuklanmadi")
    # Xatolik bo'lsa ham workflow fail bo'lmasligi uchun
    sys.exit(0)
