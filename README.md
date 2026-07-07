# MotivBot — Kunlik avtomatik Instagram Reels boti

Bu tizim **har kuni o'zi**:
1. Motivatsion iqtibosni tanlaydi
2. Chiroyli fon + matn bilan vertikal video (1080x1920, Reels formati) yaratadi
3. Instagram Business akkauntingizga avtomatik joylaydi

**GitHub Actions** orqali ishlaydi — ya'ni kompyuteringiz yoqilgan bo'lishi shart emas, hammasi bulutda, bepul ishlaydi.

---

## ⚠️ Avval bilib qo'ying

- Instagram post qilish uchun **Business yoki Creator akkaunt** (shaxsiy oddiy akkaunt emas) va **Facebook Page**ga ulangan bo'lishi shart — bu Meta talabi, uni chetlab o'tib bo'lmaydi.
- Video generatsiya **pullik AI orqali emas**, balki matn+fon+zoom effekti orqali yaratiladi (siz tanlagan variant).
- Video omborida saqlash uchun **Cloudinary** (bepul reja yetarli) ishlatiladi, chunki Instagram video faylni faqat ochiq URL orqali qabul qiladi.
- Iqtiboslar ro'yxati `quotes.json` faylida — xohlagancha qo'shishingiz, o'chirishingiz mumkin.

---

## 1-qadam: GitHub'da repozitoriya yaratish

1. [github.com](https://github.com) da hisob oching (agar yo'q bo'lsa)
2. Yangi **private** repozitoriya yarating (masalan `motivbot`)
3. Ushbu papkadagi barcha fayllarni o'sha repozitoriyaga yuklang:

```bash
cd motivbot
git init
git add .
git commit -m "Boshlang'ich versiya"
git branch -M main
git remote add origin https://github.com/FOYDALANUVCHI_NOMI/motivbot.git
git push -u origin main
```

---

## 2-qadam: Cloudinary sozlash (video hostingi, bepul)

1. [cloudinary.com](https://cloudinary.com) da bepul hisob oching
2. Dashboard'da **Cloud name** ni ko'chirib oling
3. Settings → Upload → **Add upload preset** → Signing mode: **Unsigned** qilib saqlang, preset nomini eslab qoling

---

## 3-qadam: Instagram + Meta Developer sozlash

Bu qadam biroz uzunroq, lekin bir marta qilinadi:

1. Instagram akkauntingizni **Professional (Business yoki Creator)** akkauntga o'tkazing (Instagram ilovasi → Sozlamalar → Akkaunt turi)
2. Bu akkauntni bitta **Facebook Page**ga ulang (agar yo'q bo'lsa, yangi bepul Facebook Page yarating)
3. [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App** → turi: *Business*
4. Ilovangizga **Instagram Graph API** mahsulotini qo'shing
5. **Graph API Explorer** ([developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer)) orqali:
   - Ilovangizni tanlang
   - Ruxsatlar (permissions): `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`
   - Token oling, so'ng uni **uzoq muddatli (60 kunlik) tokenga** almashtiring:
     ```
     https://graph.facebook.com/v21.0/oauth/access_token?
       grant_type=fb_exchange_token&
       client_id=ILOVA_ID&
       client_secret=ILOVA_SECRET&
       fb_exchange_token=QISQA_TOKEN
     ```
6. Instagram Business Account ID'ni oling:
   ```
   https://graph.facebook.com/v21.0/me/accounts?access_token=TOKEN
   ```
   keyin har bir Page ID uchun:
   ```
   https://graph.facebook.com/v21.0/PAGE_ID?fields=instagram_business_account&access_token=TOKEN
   ```

> 💡 Token 60 kundan keyin eskiradi — uni qayta yangilab, GitHub Secret'ni yangilab turishingiz kerak bo'ladi. Bu — Meta tomonidan qo'yilgan cheklov, hech qanday tizim buni butunlay chetlab o'ta olmaydi.

---

## 4-qadam: GitHub Secrets qo'shish

Repozitoriyangizda: **Settings → Secrets and variables → Actions → New repository secret**

Quyidagi 4 ta maxfiy o'zgaruvchini qo'shing:

| Nomi | Qiymati |
|---|---|
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name |
| `CLOUDINARY_UPLOAD_PRESET` | Cloudinary unsigned preset nomi |
| `IG_ACCESS_TOKEN` | Uzoq muddatli Instagram/Facebook token |
| `IG_USER_ID` | Instagram Business Account ID |

---

## 5-qadam: Sinab ko'rish

Repozitoriyada **Actions** bo'limiga o'ting → **Kunlik Instagram post** workflow'ini tanlang → **Run workflow** tugmasini bosing (qo'lda ishga tushirish).

Loglarni kuzatib boring — xatolik bo'lsa, aynan qaysi qadamda ekanini ko'rsatadi.

---

## Avtomatik jadval

`.github/workflows/daily-post.yml` faylida cron **har kuni soat 03:00 UTC (Toshkent vaqti bilan 08:00)** ga sozlangan. O'zgartirmoqchi bo'lsangiz, cron qatorini tahrirlang:

```yaml
- cron: "0 3 * * *"   # daqiqa soat kun oy hafta_kuni
```

---

## Fayllar tuzilishi

```
motivbot/
├── quotes.json              # Iqtiboslar bazasi (xohlagancha qo'shing)
├── generate_video.py        # Video yaratish skripti
├── upload_and_post.py        # Cloudinary + Instagram'ga joylash
├── state.json                # Qaysi iqtiboslar ishlatilganini eslab qoladi
├── requirements.txt
├── fonts/                    # Videodagi matn uchun shriftlar
└── .github/workflows/
    └── daily-post.yml        # Kunlik avtomatik ishga tushirish
```

## Nimalarni o'zingiz sozlashingiz mumkin

- **`quotes.json`** — o'z iqtiboslaringizni qo'shing
- **`PALETTES`** (`generate_video.py` ichida) — fon ranglarini o'zgartiring
- **Caption/hashtag** — `main()` funksiyasidagi shablonni tahrirlang
- **Video davomiyligi** — `build_video(frame_path, duration=8)` dagi raqamni o'zgartiring

## Cheklovlar (halol ogohlantirish)

- Instagram token muddati tugasa, post to'xtaydi — uni qayta yangilash kerak
- Cloudinary bepul rejasida oylik trafik chegarasi bor (odatda 25GB/oy — kunlik bitta qisqa video uchun yetarli)
- Meta har qanday avtomatlashtirilgan akkauntni bir xil qoliplar bilan haddan tashqari faol ishlatilsa, spam sifatida belgilashi mumkin — shuning uchun kuniga 1 tadan ortiq post joylashtirmang
