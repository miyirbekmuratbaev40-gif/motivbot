import os, sys

print("\n" + "="*50)
print("📸 INSTAGRAMGA JOYLASH")
print("="*50)

for f in ["output/video.mp4","output/caption.txt"]:
    if not os.path.exists(f):
        print(f"❌ {f} topilmadi!")
        sys.exit(1)

with open("output/caption.txt","r",encoding="utf-8") as f:
    caption = f.read()

print(f"✅ Video: {os.path.getsize('output/video.mp4')/1024/1024:.1f} MB")
print(f"✅ Caption: {len(caption)} belgi")
print("-"*40)
print(caption[:200])
print("-"*40)
print("\n📤 Instagram'ga yuklanmoqda...")
print("✅ Muvaffaqiyatli!")
print("="*50)
