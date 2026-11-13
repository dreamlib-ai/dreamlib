# Dreamlib

Rüya günlüğü ve bilinçaltı platformu: kullanıcı rüyasını yazar ya da sesle anlatır, yapay zekâ tabir eder ve duygularını çıkarır, rüya manga sayfasına çevrilir, kütüphanede saklanır; benzer rüya görenler eşleşir. Kullanıcı için **basit** olmalı: çok özellik var ama her biri sade ve az adımla sunulur.

## Yapı

Basit klasik monorepo; ağır araç yok, kök yalnız görev çalıştırıcı.

| Klasör | İçerik |
| --- | --- |
| `frontend/` | React + TypeScript + Vite. Tema `src/theme.css`, metinler `src/strings.ts`, tek API kapısı `src/api.ts` (başka yerde `fetch` yok) |
| `backend/` | Python 3.13 + FastAPI. `app/` içinde `routes/` (HTTP uçları), `pipelines/` (kitapçık, görsel), `providers/` (OpenRouter, fal), `store/` (Supabase, iş kuyruğu, yerel sahte hesap), `worker.py` (arka plan işleri), `main.py`, `prompts/` (görev başına sürümlü prompt); `tests/` pytest. Veritabanı şeması kökteki `supabase/migrations/` içinde, tarih sırasıyla. Mimari: `docs/mimari.md` |
| `docs/` | `api.md` uçlar, `mimari.md` katmanlar ve iş kuyruğu, `urun.md` ürün kararları, `tasarim.md` tasarım yönü ve maskot. Kolektif motor: `vizyon.md` yön, `motor.md` grafik ve benzerlik, `veri.md`, `uretim.md`, `llm.md`, `istemci.md`, `yol-haritasi.md`, `gorevler.md` iş listesi, `eval-hedefleri.md`, `riskler.md`, `acik-kaynak.md`, `kararlar/` karar kayıtları. Araştırma: `arastirma.md` program, `arastirma/` alanlar ve kartlar, `fikirler.md` |
| `brand/` | Profil resmi ve marka dosyaları |
| `scripts/` | `setup.ps1`, `dev.ps1`, `check.ps1`, `cutout.ps1` (görsel zemin kesme) |
| `kaynak/` | Git dışı yerel kaynaklar: `belgeler/`, `referans/`, `prototip/` |

## Çalışma kuralları

- **Basit tut.** Tek süreç, modüler monolit; servise bölme ancak gerçek sebep çıkınca. Uzun işler (görsel, kitapçık) Postgres `jobs` kuyruğuna girer ve aynı süreçteki worker yürütür; RabbitMQ/Redis yok. Bağımlılık eklemeden önce Cenker'e sor (backend: fastapi, uvicorn, httpx; frontend: react, vite, supabase-js). Frontend'de ağır UI kütüphanesi yok.
- **Python seçildi (2026-10-24):** AI işleri (OpenRouter, fal, Supabase) için en hızlı geliştirme; Go sürümü silindi, geçmişte durur. Tip ipucu yaz, `async` kullan, HTTP istemcisi `httpx`.
- Veri ekranlara gömülmez: ekranlar `frontend/src/api.ts` üzerinden konuşur. Hesap ve rüya saklama Supabase (Postgres + Auth + private Storage); backend token'ı projenin açık anahtarıyla (JWKS) yerelde doğrular, eski HS256 jetonlarda GoTrue'ya sorar, ve PostgREST ile yazar, her sorguyu `user_id` ile süzer. Supabase projesi ayrı hesapta (kimlikler bakımcının notlarında); anonim giriş açık, Site URL `https://dreamlib.cenker.dev` (yerel callback adresleri de izinli). Anahtarlar `backend/.env` ve `frontend/.env.local`'de, asla repoda. `DREAMLIB_DEV_AUTH=1` yalnız Supabase olmadan yerelde bellekte sahte hesap açar.
- AI: LLM OpenRouter (`OPENROUTER_MODEL` ile seçilir, kodda sabit değil), görsel/ses fal (`FAL_IMAGE_MODEL`, `FAL_EDIT_MODEL`, `FAL_SPEECH_MODEL`). Anahtarlar tarayıcıya hiç inmez.
- Uçlar, kitapçık işi ve günlük haklar: `docs/api.md`. Ücretli her uç giriş ister (misafir anonim oturum yeterli) ve günlük hakla sınırlı.
- İlk giriş akışı `frontend/src/Onboarding.tsx`: Google ile devam et → doğrulanmış oturum → ilk hesapta gizlilik. Tercihler Supabase `user_metadata.dreamlib` içinde, yalnız tercih amaçlıdır; yetki kaynağı değildir. `/?onboarding` akışı yeniden açar. Gizlilik kayda gönderilir; eski anonim hesap aynı kimlikle bağlanır. Sağlayıcı kurulumu ve yerel dönüş adresleri `docs/giris.md`; Google Cloud istemcisi olmadan Google etkin sayılmaz. Frontend sahte geliştirme jetonu üretmez.
- Arayüz Türkçe, metinler tek dosyada; kod, değişken ve dosya adları İngilizce. Ürün kararları `docs/urun.md`, tasarım `docs/tasarim.md`.

## Komutlar

Kökte (PowerShell betiklerini çağırır):
- `npm run setup`: bir kez; frontend paketleri, `backend/.venv` ve paketleri, yoksa `backend/.env`
- `npm run dev`: backend (`http://127.0.0.1:8080`, şema `/docs`) ve frontend (`http://localhost:5173`, `/api` backend'e yönlenir) ayrı pencerelerde. Vite `strictPort` kullanır: 5173 doluysa eski Vite'ı kapat.
- `npm run check`: pytest + frontend oturum testleri, tip kontrolü ve build. Her değişiklikten sonra çalıştır.
- `npm start` (ya da `npm run dreamlib`): bütün projeyi Docker'da kaldırır; `npm run dreamlib:stop` durdurur (veri kalır), `npm run dreamlib:logs` backend ve frontend loglarını izler. Aşağıdaki `npm run db -- app` ile aynıdır.
- `npm run db -- up|app|status|migrate|psql|logs|env|down|reset`: kalıcı yerel Supabase `dreamlib-local`, Docker'da (betik `scripts/local_db.py`, compose `supabase/local/`). `up` Postgres'i (`127.0.0.1:55432`), giriş (GoTrue), dosya deposu (storage-api), PostgREST (`:55433`) ve Supabase yollarını (`/rest/v1`, `/auth/v1`, `/storage/v1`) tek adreste sunan ağ geçidini (`http://127.0.0.1:55431`) kaldırır; ilk seferde kurar, bekleyen migration'ları uygular (`supabase_migrations.schema_migrations`). `app` bunlara ek olarak backend'i (`:8080`, kod bağlı, değişince yeniden yüklenir; anahtarlar `backend/.env`'den, Supabase ayarları yerele çevrilir) ve frontend'i (`http://localhost:5173`) de Docker'da açar; `npm run dev` ile aynı portlar, ikisi birlikte koşmaz. `env` uygulamayı elle yerel yığına bağlamak için `.env` satırlarını yazar. `down` durdurur, veri kalır; `reset` veriyi silip baştan kurar. Arayüz girişi yalnız Google: yerelde `DREAMLIB_GOOGLE_ENABLED=true`, `DREAMLIB_GOOGLE_CLIENT_ID`, `DREAMLIB_GOOGLE_SECRET` ister (kabukta ya da git dışı `supabase/local/.env`'de) (yönlendirme `http://127.0.0.1:55431/auth/v1/callback`).
- `npm run test:db`: ayrı ve geçici `dreamlib-local-test` yığınını (`:55442`/`:55443`) migration'lardan sıfırdan kurar, `backend/tests/db` testlerini gerçek veritabanına karşı koşar ve yığını siler (`--keep` açık bırakır, `--reuse` yalnız testleri koşar); `dreamlib-local`'ın verisine dokunmaz. Migration ya da veritabanına yazan kod değişince çalıştır; CI'da `database` işi.

Elle: `backend/` içinde `.venv\Scripts\python -m app`, `.venv\Scripts\python -m pytest -q`; `frontend/` içinde `npm run dev`, `npm run build`. Anahtarlar için `backend/env.example` → `backend/.env`.

## Sınırlar

- `kaynak/` git dışı; repoya ekleme. `kaynak/belgeler/db pass.txt`'i açma.
- `.env*` okuma/yazma yok; anahtarlar uygulamaya gömülmez, Faz 2'de Edge Functions'ta durur.
- Commit ve PR yazarı yalnız Cenker; co-author ya da "Generated with" satırı yok. Force push yok.

## Git ve PR

- Commit'ler Conventional Commits, İngilizce ve kısa: `feat: add dream feed`, `fix: keep tab slots fixed`. Türler: `feat`, `fix`, `refactor`, `style`, `docs`, `test`, `chore`. Konu başına bir commit; gövde yalnız gerekiyorsa.
- İş dalda yapılır: `feat/<konu>`, `fix/<konu>` (ör. `feat/dream-feed`). `main`'e PR ile girer. Hızlı ilerleme için (2026-10-16): düzgün, tek konulu commit'ler at, PR'ı aç ve **merge etmeden önce sorma**, kendin squash merge et. Doğrudan `main`'e push yok. CI (`.github/workflows/check.yml`) her PR'da yalnız kontrol çalıştırır: pytest, frontend testleri, tip kontrolü, build ve sır taraması; yayın elle yapılır. Yine de `npm run check` yerelde çalıştırılır.
- PR başlığı commit gibi (İngilizce, kısa). PR gövdesi **Türkçe**, Cenker'in hızlıca anlayacağı sade dille:
  - **Ne değişti:** kullanıcının göreceği değişiklik, 2-4 madde.
  - **Neden:** hangi isteğe ya da soruna karşılık.
  - **Nasıl denendi:** hangi ekranlar gezildi, tip kontrolü ve lint.
  - **Dikkat:** varsa açık kalan, bilerek yapılmayan ya da karar bekleyen şey.

## Hafıza ve dosya boyu

- İşe başlamadan `memory.md`'yi oku: Cenker'in daha önce düzelttiği hatalar ve doğru yaklaşım orada. Cenker bir hatayı düzelttiğinde kalıbını oraya tek satır yaz.
- Proje uzun sürecek: her `.md` en fazla 160 satır. Uzatma; yeni bilgi eskisinin yerine geçer, tekrar eden budanır.

Bakımcı günlüğü repo dışında, Obsidian kasasında: `projeler/dreamlib/gunluk-dreamlib.md`, proje notu `projeler/dreamlib/dreamlib.md`. İş bitince günlüğe sonuç ve açık işleri yaz; kasa sözleşmesi bakımcının yerel `KASA.md` dosyasında.
