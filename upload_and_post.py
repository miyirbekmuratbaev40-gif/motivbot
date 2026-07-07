name: Kunlik Instagram post

on:
  schedule:
    # Har kuni ertalab soat 08:00 (Toshkent, UTC+5) = 03:00 UTC da ishga tushadi
    - cron: "0 3 * * *"
  workflow_dispatch: {}   # Qo'lda ham ishga tushirish imkoniyati (Actions bo'limidan)

permissions:
  contents: write   # bot'ga "media" branch'ga va state.json'ga push qilish huquqini beradi

jobs:
  post-to-instagram:
    runs-on: ubuntu-latest
    steps:
      - name: Repozitoriyani olish
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Python o'rnatish
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Kutubxonalarni o'rnatish
        run: |
          sudo apt-get update && sudo apt-get install -y ffmpeg
          pip install -r requirements.txt

      - name: Video yaratish
        run: python generate_video.py

      - name: Videoni "media" branch'ga joylash (ochiq URL olish uchun)
        id: media
        run: |
          git config user.name "motivbot"
          git config user.email "motivbot@users.noreply.github.com"

          cp output/video.mp4 /tmp/video.mp4

          git checkout --orphan media_tmp
          git rm -rf . > /dev/null 2>&1 || true
          cp /tmp/video.mp4 video.mp4
          git add video.mp4
          git commit -m "Kunlik video yangilandi"
          git branch -D media > /dev/null 2>&1 || true
          git branch -m media
          git push -f origin media

          echo "video_url=https://raw.githubusercontent.com/${{ github.repository }}/media/video.mp4" >> "$GITHUB_OUTPUT"

      - name: Asosiy branch'ga qaytish
        run: git checkout main

      - name: Instagram'ga joylash
        env:
          VIDEO_URL: ${{ steps.media.outputs.video_url }}
          IG_ACCESS_TOKEN: ${{ secrets.IG_ACCESS_TOKEN }}
          IG_USER_ID: ${{ secrets.IG_USER_ID }}
        run: python upload_and_post.py

      - name: Holatni saqlash (qaysi iqtiboslar ishlatilgani)
        run: |
          git add state.json
          git commit -m "state.json yangilandi [skip ci]" || echo "O'zgarish yo'q"
          git push origin main
