"""
upload_and_post.py
-------------------
Instagram Graph API orqali videoni Reels sifatida joylaydi.

Video fayl avvalroq (GitHub Actions workflow ichida, alohida bash qadamida)
"media" branch'iga joylab qo'yilgan va ochiq raw.githubusercontent.com
URL orqali kirish mumkin - shu URL VIDEO_URL muhit o'zgaruvchisi orqali
uzatiladi (Cloudinary yoki boshqa uchinchi tomon xizmati kerak emas).

Kerakli maxfiy o'zgaruvchilar (GitHub Secrets):
    IG_ACCESS_TOKEN   (Instagram/Facebook uzoq muddatli access token)
    IG_USER_ID        (Instagram Business Account ID)

Kerakli muhit o'zgaruvchisi (workflow ichida avtomatik beriladi):
    VIDEO_URL         (video.mp4 ga ochiq havola)
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
    caption_path = "output/caption.txt"

    if not os.path.exists(caption_path):
        print("XATOLIK: output/caption.txt topilmadi. Avval generate_video.py ni ishga tushiring.")
        sys.exit(1)

    with open(caption_path, "r", encoding="utf-8") as f:
        caption = f.read()

    video_url = env("VIDEO_URL")
    creation_id = create_media_container(video_url, caption)
    wait_until_ready(creation_id)
    publish_media(creation_id)


if __name__ == "__main__":
    main()
