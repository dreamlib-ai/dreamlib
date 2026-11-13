# Mimari

Tek süreçli modüler monolit: FastAPI uçları, aynı süreçte arka plan worker'ı, durum Supabase'de (Postgres, Auth, Storage). Ayrı kuyruk servisi yok.

```
tarayıcı ──HTTP──> FastAPI (app/routes)
                     │ metin (clean, analyze): senkron, OpenRouter
                     │ görsel, kitapçık: jobs tablosuna 'queued' satır → 202 {id}
                     ▼
                  Postgres jobs  <── worker (app/worker.py, asyncio)
                                       claim_job → pipeline → fal queue → Storage → done
tarayıcı ──GET /api/jobs/{id} ile izler
```

## Katmanlar (`backend/app/`)

| Klasör | Ne durur |
| --- | --- |
| `routes/` | Yalnız HTTP: doğrulama, giriş, yanıt biçimi. İş başlatan uçlar kuyruğa satır yazar, çizim yapmaz |
| `pipelines/` | İşin kendisi: `manga.py` (taslak → paneller), `image.py`; `context.py` iş durumunu kaydetme; `registry.py` iş türleri kaydı (`KINDS`), kuyruk ve worker buradan doğrular |
| `providers/` | Dış servis istemcileri: `openrouter.py`, `fal.py` (kuyruk API'si, fiyat tablosu) |
| `store/` | `supabase.py` (rüyalar, Storage, token), `jobstore.py` (kuyruk), `devstore.py` (yerel sahte hesap) |
| `worker.py` | Kuyruktan iş alır, lease ile tutar, hata olursa yeniden dener |

## İş kuyruğu

- Tablo `jobs` (`supabase/migrations/20261014000005_jobs.sql`). Kullanıcı başına aynı anda tek aktif iş, unique index ile garanti.
- Worker `claim_job` ile sıradaki işi alır (`FOR UPDATE SKIP LOCKED`), 60 sn lease koyar ve 15 sn'de bir yeniler. Yazmalar lease sahibine kilitli: işi başkası devraldıysa eski worker yazamaz.
- Pipeline her adımı `state` alanına yazar: taslak, kuyruğa verilen fal istek adresleri, saklanan paneller. Süreç ölürse lease dolar, iş yeniden alınır ve kaldığı yerden sürer. Biten paneller ve bekleyen fal istekleri yeniden ödenmez.
- Geçici hata 3 denemeye kadar tekrarlanır. Kalıcı hata (`JobFailed`, ör. okunamayan taslak) ya da son deneme işi `failed` yapar ve yüklenen dosyaları siler.
- Günlük hak: misafir 3, hesap 10 iş (24 saat, başarısız işler sayılmaz). Her işte `cost_usd` tahmini tutulur. Yorum ve panel yenileme hakları `call_log` tablosunda sayılır; panel ve kaydetme kilidi `user_locks` tablosunda (`0006_quota_locks.sql`). İkisi de süreç belleğinde değil, API birden çok kopya çalışabilir.
- Worker 6 saatte bir temizlik yapar (`worker.sweep`): 7 günden eski bitmiş işleri siler, rüyaya kaydedilmemiş (`state.saved` yok) olanların görsellerini de kaldırır.
- Worker varsayılan olarak API sürecinde 2 işi aynı anda yürütür (`DREAMLIB_WORKERS`). `DREAMLIB_WORKERS=0` ve `python -m app.worker` ile ayrı süreçte çalışır; kod aynı.

## Kimlik

Access token, Supabase'in yayımladığı açık anahtarla (`/auth/v1/.well-known/jwks.json`, ES256) backend'de doğrulanır; istek başına ağ çağrısı yok. Anahtarlar 10 dakika tutulur, bilinmeyen anahtar kimliği gelince en fazla dakikada bir yeniden çekilir. Anahtarlar alınamazsa ya da jeton eski HS256 anahtarıyla imzalıysa GoTrue'ya sorulur. Bedeli: çıkış yapılmış jeton süresi dolana kadar (1 saat) geçerli kalır.

## Neden RabbitMQ yok

Hacim dakikada birkaç iş; Postgres kuyruğu bunu ek servis olmadan, durumu tek yerde tutarak taşır. Broker şu durumlarda düşünülür:
- işçiler birden çok makineye yayılmalıysa,
- saniyede yüzlerce iş geliyorsa,
- bir olayı birden çok tüketici dinlemeliyse.

O gün yalnız `store/jobstore.py`'nin arkası değişir. fal webhook'u da herkese açık adres gelince bekleme yerine kullanılabilir.

## Hedef mimari (kolektif motor)

Yukarısı bugünkü durumdur. Aşağısı [vizyon](vizyon.md) için kurulacak hâl; biçim aynı kalır (tek kod tabanı, tek veritabanı), katman eklenir. Kararlar: [0001](kararlar/0001-moduler-monolit.md), [0002](kararlar/0002-backend-dili.md).

```
web / mobil ──/api/v1──> FastAPI (routes)
                           │ akışlı yorum (SSE): çıkar → getir → sentezle
                           │ iş başlatır: index, glyph, magazine, video
                           ▼
                        Postgres ── jobs kuyruğu <── worker (aynı kod, ayrı rol)
                           │ dreams, analyses, magazines            │
                           │ entities, edges, embeddings (pgvector) ├─ OpenRouter (görev tablosu)
                           │ consents, usage                        └─ fal (kuyruk + webhook)
                        Storage: özel görseller, açık ikon ve kapak küçük resimleri
```

| Yeni katman | Klasör | Görev | Ayrıntı |
| --- | --- | --- | --- |
| Motor | `app/engine/` | Düğüm normalize, puanlayıcılar, eşleşme, getirme | [motor](motor.md) |
| Üretim | `app/pipelines/` | `index`, `glyph`, `magazine`, `video` işleri | [üretim](uretim.md) |
| LLM | `app/providers/openrouter.py`, `app/prompts/` | Görev tablosu, şemalı çıktı, akış, embedding | [LLM](llm.md) |
| Sözleşme | `app/routes/` | `/api/v1`, hata kodu, sayfalama | [istemci](istemci.md) |

### Hazır olan ve eksik

| Alan | Hazır | Eksik |
| --- | --- | --- |
| Kuyruk | Lease, heartbeat, 3 deneme, kaldığı yerden devam | Tür kaydı, bekleme süresi, zincir, tür başına eşzamanlılık |
| fal | Kuyruk API'si, saklı istek adresleri, fiyat tahmini | Model kaydı, webhook, NSFW bayrağı, video |
| LLM | Tek model, JSON modu, kullanım logu | Görev tablosu, şema garantisi, akış, yedek model, embedding |
| Yorum | Tek çağrı, `features` v1, kullanıcı düzeltmeleri | Sürümlü `analyses`, getirme adımı, sözlük |
| İlişki | Tekrar eden etiket sayımı | Düğüm sözlüğü, kenarlar, benzerlik, eşleşme |
| Gizlilik | Sahip süzmesi, özel Storage, RLS | Rıza defteri, kademeler, dışa aktarma ve silme |
| Paylaşım | Görünürlük alanı | Dergi kaydı, link, herkese açık kütüphane, moderasyon |
| Maliyet | İş başına tahmin, günlük hak | `usage` defteri, genel harcama freni |
| İstemci | Bearer jeton, tek API kapısı | `/api/v1`, makine hata kodu, imleçli sayfalama, küçük resim |

### Ölçek adımları

| Belirti | Adım |
| --- | --- |
| Çizim işleri API yanıt süresini etkiliyor | Worker ayrı süreç (`DREAMLIB_WORKERS=0`, `python -m app.worker`) |
| Yoklama istekleri artıyor | fal webhook; yoklama yedek kalır |
| Vektör ve zincir sorguları PostgREST üstünde yavaş | `store/` arkasında doğrudan Postgres bağlantısı |
| Kütüphane görselleri yavaş | Önceden üretilmiş küçük resimler, CDN |
| Okuma yükü yazmayı eziyor | Okuma kopyası |

Her adım tek bir modülün arkasını değiştirir; uç sözleşmesi aynı kalır.
