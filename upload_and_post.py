"""
upload_and_post.py
-------------------
1) output/video.mp4 faylini Cloudinary'ga yuklaydi (ochiq URL olish uchun,
   Instagram Graph API videoni faqat ochiq URL orqali qabul qiladi).
2) Instagram Graph API orqali Reels sifatida joylaydi.

Kerakli maxfiy o'zgaruvchilar (GitHub Secrets yoki .env):
    CLOUDINARY_CLOUD_NAME
    CLOUDINARY_UPLOAD_PRESET   (unsigned preset, Cloudinary dashboardida yaratiladi)
    IG_ACCESS_TOKEN            (Instagram/Facebook uzoq muddatli access token)
    IG_USER_ID                 (Instagram Business Account ID)
"""

import os
import sys
import time

import requests

GRAPH_API_VERSION = "v21.0"


def env(name):
    val = os.environ.get(name)
    if not val:
        print(f"XATOLIK: {name} muhit o'zgaruvchisi topilmadi.")
        sys.exit(1)
    return val


def upload_to_cloudinary(video_path):
    cloud_name = env("CLOUDINARY_CLOUD_NAME")
    preset = env("CLOUDINARY_UPLOAD_PRESET")
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/video/upload"

    with open(video_path, "rb") as f:
        files = {"file": f}
        data = {"upload_preset": preset}
        resp = requests.post(url, files=files, data=data, timeout=120)

    resp.raise_for_status()
    secure_url = resp.json()["secure_url"]
    print(f"Cloudinary'ga yuklandi: {secure_url}")
    return secure_url


def create_media_container(video_url, caption):
    ig_user_id = env("IG_USER_ID")
    token = env("IG_ACCESS_TOKEN")
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": token,
    }
    resp = requests.post(url, data=params, timeout=60)
    resp.raise_for_status()
    creation_id = resp.json()["id"]
    print(f"Media konteyner yaratildi: {creation_id}")
    return creation_id


def wait_until_ready(creation_id, timeout=300, interval=10):
    token = env("IG_ACCESS_TOKEN")
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{creation_id}"
    elapsed = 0
    while elapsed < timeout:
        resp = requests.get(url, params={"fields": "status_code", "access_token": token})
        resp.raise_for_status()
        status = resp.json().get("status_code")
        print(f"Holat: {status}")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError("Instagram video qayta ishlashda xato yuz berdi.")
        time.sleep(interval)
        elapsed += interval
    raise TimeoutError("Video qayta ishlash kutilganidan uzoq davom etdi.")


def publish_media(creation_id):
    ig_user_id = env("IG_USER_ID")
    token = env("IG_ACCESS_TOKEN")
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{ig_user_id}/media_publish"
    params = {"creation_id": creation_id, "access_token": token}
    resp = requests.post(url, data=params, timeout=60)
    resp.raise_for_status()
    post_id = resp.json()["id"]
    print(f"E'lon qilindi! Post ID: {post_id}")
    return post_id


def main():
    video_path = "output/video.mp4"
    caption_path = "output/caption.txt"

    if not os.path.exists(video_path):
        print("XATOLIK: output/video.mp4 topilmadi. Avval generate_video.py ni ishga tushiring.")
        sys.exit(1)

    with open(caption_path, "r", encoding="utf-8") as f:
        caption = f.read()

    video_url = upload_to_cloudinary(video_path)
    creation_id = create_media_container(video_url, caption)
    wait_until_ready(creation_id)
    publish_media(creation_id)


if __name__ == "__main__":
    main()
