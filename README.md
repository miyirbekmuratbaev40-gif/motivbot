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
- Video Instagram'ga yuborilishi uchun ochiq (public) URL kerak. Buning uchun uchinchi tomon xizmati (Cloudinary va h.k.) shart emas — video repozitoriyaning o'zidagi alohida `media` branch'ida saqlanadi va `raw.githubusercontent.com` orqali ochiq havola olinadi. **Shu sababli repozitoriya oxir-oqibat Public (ochiq) qilinishi kerak** — bu xavfsiz, chunki GitHub Secrets (tokenlar) public repoda ham hech kimga ko'rinmaydi, faqat kod va videolar ko'rinadi.
- Iqtiboslar o'rniga endi **qiziqarli faktlar** ishlatiladi (`facts.json`) — xohlagancha qo'shishingiz, o'chirishingiz mumkin.
- Video endi **ovozli** (o'zbekcha tabiiy TTS diktor ovozi, Microsoft Edge TTS orqali, bepul) va **real fon footage** bilan (Pexels'dan, mavzuga mos: koinot, okean, tabiat va h.k.) — statik gradient endi faqat zaxira (fallback) sifatida ishlatiladi.

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

## 2-qadam: Repozitoriyani Public (ochiq) qilish

Video ochiq URL orqali Instagram'ga yuborilishi uchun repo public bo'lishi kerak:

1. Repozitoriyangizda **Settings** ga o'ting
2. Pastga tushib, **"Danger Zone"** bo'limini toping
3. **"Change visibility"** → **"Change to public"** ni tanlang
4. Tasdiqlash uchun repo nomini yozib kiriting

> 🔒 Xavotir olmang: **Secrets (tokenlar) hech qachon ko'rinmaydi**, hatto public repolarda ham — ular alohida shifrlangan joyda saqlanadi. Faqat kod, iqtiboslar va yaratilgan videolar ko'rinadi.

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

## 3.5-qadam: Pexels API kaliti olish (fon videolar uchun, bepul)

1. [pexels.com/api](https://www.pexels.com/api/) ga o'ting
2. **"Get Started"** orqali bepul ro'yxatdan o'ting (email bilan)
3. Tasdiqlagach, sizga darhol **API kalit** beriladi (dashboard'da ko'rinadi)
4. Uni nusxalab saqlang — bu `PEXELS_API_KEY` bo'ladi

> Agar bu kalit sozlanmasa yoki ishlamasa, tizim avtomatik ravishda oddiy gradient fonga qaytadi (video baribir ovoz bilan ishlaydi, faqat fon real footage o'rniga rangli bo'ladi).

---

## 4-qadam: GitHub Secrets qo'shish

Repozitoriyangizda: **Settings → Secrets and variables → Actions → New repository secret**

Quyidagi 3 ta maxfiy o'zgaruvchini qo'shing:

| Nomi | Qiymati |
|---|---|
| `IG_ACCESS_TOKEN` | Uzoq muddatli Instagram/Facebook token |
| `IG_USER_ID` | Instagram Business Account ID |
| `PEXELS_API_KEY` | Pexels'dan olingan bepul API kalit |

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
├── facts.json                # Qiziqarli faktlar bazasi (xohlagancha qo'shing)
├── generate_video.py        # Video yaratish skripti
├── upload_and_post.py        # Cloudinary + Instagram'ga joylash
├── state.json                # Qaysi iqtiboslar ishlatilganini eslab qoladi
├── requirements.txt
├── fonts/                    # Videodagi matn uchun shriftlar
└── .github/workflows/
    └── daily-post.yml        # Kunlik avtomatik ishga tushirish
```

## Nimalarni o'zingiz sozlashingiz mumkin

- **`facts.json`** — o'z faktlaringizni qo'shing
- **`PALETTES`** (`generate_video.py` ichida) — fon ranglarini o'zgartiring
- **Caption/hashtag** — `main()` funksiyasidagi shablonni tahrirlang
- **Video davomiyligi** — `build_video(frame_path, duration=8)` dagi raqamni o'zgartiring

## Cheklovlar (halol ogohlantirish)

- Instagram token muddati tugasa, post to'xtaydi — uni qayta yangilash kerak
- Repozitoriya **Public** bo'lgani uchun kod, iqtiboslar va videolar hamma uchun ko'rinadi (tokenlar esa yashirin qoladi)
- Meta har qanday avtomatlashtirilgan akkauntni bir xil qoliplar bilan haddan tashqari faol ishlatilsa, spam sifatida belgilashi mumkin — shuning uchun kuniga 1 tadan ortiq post joylashtirmang
