# Yayın

Yayın elle yapılır; CI yalnız kontrol çalıştırır, otomatik yayın yoktur. Proje kimlikleri ve yayın geçmişi repoda tutulmaz; bakımcının kendi notlarındadır.

## Yapı

- **Uygulama:** `https://dreamlib.cenker.dev`, Cloudflare Workers Static Assets.
- **API:** Railway üzerinde tek servis; aynı süreçte iki kuyruk worker'ı.
- **Aynı origin:** frontend `/api/*` ve `/healthz` isteklerini API'ye geçirir. Bearer jetonu ve ses gövdesi korunur; cookie aktarılmaz, API yanıtları cache'lenmez. Tarayıcıda CORS ayarı ya da servis anahtarı yoktur.
- **Giriş:** Supabase Site URL canlı alan adıdır; `?auth=callback` izinli dönüş adresidir. Ayrıntı: [giriş](giris.md).

## Yayınlama

Önce `npm run check`.

Backend (Railway CLI, bağlı servise dosya paketi gönderir):

```powershell
railway up backend --path-as-root --detach --project $env:RAILWAY_PROJECT_ID --service $env:RAILWAY_SERVICE_ID --environment production
```

Frontend: `VITE_SUPABASE_URL` ve publishable anahtar build ortamında tanımlanır; `frontend/` içinde `npm run build`, ardından `wrangler deploy`.

Ortam dosyaları yayın paketine girmez; backend Docker imajı yalnız requirements ve uygulama kodunu alır. Sunucu anahtarları Railway servis değişkenlerindedir; değerleri loglara dökme.

## Yayın sonrası kontrol

```powershell
Invoke-RestMethod https://dreamlib.cenker.dev/healthz
```

- `ok`, hesap, LLM, görsel, ses ve worker alanları true olmalı.
- `/api/dreams` oturumsuz 401 dönmeli.
- Canlı JS özeti temiz build ile aynı olmalı.
- Site ve asset yüklemesi, Google yönlendirmesi ve mobil HTTPS denenir.
- Şema değiştiyse migration canlıda uygulanmış ve RLS korunmuş olmalı.

Canlı uçtan uca deneme için `scripts/live-journal-smoke.py`: iki geçici sentetik hesap açar, kayıt, düzeltme ve erişim kurallarını dener, sonra yalnız o hesapları siler. Gerçek kullanıcı kaydına dokunmaz.

## Ürün olayları

İçeriksiz ürün olayları (`session_open`, `record_started`, `transcript_ready`, `analysis_ready`, `booklet_ready`, `dream_saved`, `feedback_helpful/unhelpful`) yalnız servis loguna yazılır: takma hesap kodu, UUID olay kimliği ve platform. Rüya metni, ad ya da e-posta yoktur. Elle rapor:

```powershell
railway logs --project $env:RAILWAY_PROJECT_ID --service $env:RAILWAY_SERVICE_ID --environment production --lines 1000 --filter product_event --json | python scripts/pilot-report.py
```

Kalıcı analitik tablosu yoktur; sayım log penceresiyle sınırlıdır.

## Geri alma

Bir önceki temiz commit yeniden yayımlanır (Railway ve Cloudflare için aynı adımlar). Geri alınan şema değişikliği varsa ayrıca elle geri yazılır; migration'lar geriye uyumlu yazılır.
