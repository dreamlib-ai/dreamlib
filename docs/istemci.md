# İstemci: API sözleşmesi, mobil geçiş, arayüz yüzeyleri

Beta web'de koşar ama ürün mobil önceliklidir. Aynı backend iki istemciye hizmet edecek; bu yüzden sözleşme bugünden istemciden bağımsız kurulur. Karar: [0006](kararlar/0006-mobil-yol.md). Bugünkü uçlar: [api](api.md).

## Sözleşme kuralları

| Konu | Bugün | Hedef |
| --- | --- | --- |
| Yol | `/api/...` | `/api/v1/...`; eski yollar beta boyunca yönlendirilir |
| Kimlik | Bearer jeton (Supabase) | Aynı; çerez kullanılmaz, mobilde değişiklik gerekmez |
| Hata | `{"error": "Türkçe mesaj"}` | `{"code": "quota_exceeded", "error": "…"}`; istemci koda göre davranır, mesajı kendi dilinde gösterebilir |
| Liste | En çok 200 kayıt | İmleçli sayfalama (`cursor`, `limit`) |
| Tekrar | Manga'da `requestId` | Yazan her uçta `Idempotency-Key` başlığı |
| Görsel | Süreli imzalı adres | Ek olarak genişlik, yükseklik, blurhash, baskın renk, küçük resim adresi |
| Uzun iş | `GET /api/jobs/{id}` yoklama | Rüya başına tek durum ucu; SSE, yoklama yedek |
| Tip | Elle yazılmış `api.ts` | OpenAPI şemasından üretilen TS istemci |

Mobil ağ kopar ve uygulama arka plana geçer: her akışlı ya da uzun işin yoklamayla okunabilen kalıcı bir karşılığı vardır. İstemci hiçbir sonucu yalnız açık bağlantıdan beklemez.

## Yeni uçlar (taslak)

| Uç | İş |
| --- | --- |
| `POST /api/v1/dreams/{id}/interpret` | Akışlı kümülatif yorum (SSE) |
| `GET /api/v1/dreams/{id}/status` | Yorum, indeks, dergi, video durumları tek yanıtta |
| `GET /api/v1/dreams/{id}/similar` | Benzer rüyalar: oran, bileşenler, ortak semboller |
| `PUT /api/v1/dreams/{id}/consent` | `private`, `collective`, `public` |
| `GET /api/v1/magazines/{id}`, `GET /api/v1/m/{slug}` | Dergi `spec`'i; ikincisi girişsiz |
| `GET /api/v1/library` | Kendi kütüphanem; `view=wall` ya da `view=pool` |
| `GET /api/v1/explore` | Herkese açık dergiler |
| `GET /api/v1/matches/{userId}` | Eşleşme: oran, ortak noktalar, örneklem |
| `GET /api/v1/entities/{id}` | Sembol: etiket, ikon, sözlük anlamları |
| `POST /api/v1/reports` | Şikâyet ve geri çekme |

## Arayüz yüzeyleri

Her yüzeyin verisi ve sunumu ayrıdır: sunucu yapısal veri verir, animasyon istemcidedir. Böylece aynı veri web'de CSS, mobilde yerel animasyonla çizilir.

### Anlat
Tek mikrofon düğmesi, yazı ikincil; mevcut ekran korunur. Yeni özellikler buraya düğme eklemez. Taslak kurtarma ve kesinti davranışı bugünkü gibidir.

### Akışlı yorum
- Olay türleri: `title`, `entity` (düğüm kimliği, etiket, ikon adresi), `text` (cümle parçası), `emotion`, `section` (rüya, semboller, sende, başkalarında), `done`.
- Metin parça parça gelir; sembol geçtiği yerde küçük ikonuyla belirir. Yorum düz metin değil parça dizisi olarak saklanır; yeniden açıldığında aynı dizilim animasyonsuz çizilir.
- Göz yormaması için tek sütun, büyük yazı, bölüm başına kısa metin; azaltılmış hareket tercihinde metin tek seferde gelir.

### Dergi okuyucu
- Girdi `spec` ([üretim](uretim.md)); sayfa düzenleri adlandırılmış bileşenlerdir.
- Sayfa çevirme dokunma, klavye ve düğmeyle; görseller blurhash'ten netleşir.
- Yapıldı (G5): `frontend/src/Magazine.tsx`, rüya detayından açılır; sayfa düzenleri `magazine.css`'te. Kayıttan hemen sonra kendiliğinden açılması henüz yok.

### Kütüphane duvarı
- Pinterest benzeri masonry: kapaklar gerçek en-boy oranıyla dizilir. Sunucu genişlik ve yüksekliği verdiği için yerleşim görsel yüklenmeden hesaplanır, sayfa zıplamaz.
- Küçük resimler önceden üretilir; imleçli sayfalama ile aşağı indikçe yüklenir.
- Kendi kütüphanem ve herkese açık kütüphane aynı bileşeni kullanır; fark veri kaynağıdır.

### Kütüphane havuzu
- Açılışta kapakların bir havuzda yüzdüğü kısa animasyon, ardından duvara yerleşme.
- `view=pool` hafif yanıt verir: sınırlı sayıda kapak, küçük resim ve baskın renk.
- Tamamen sunum; azaltılmış harekette atlanır.

### Eşleşme modalı
- Girdi: oran, ortak semboller (ikonlarıyla), ortak temalar, duygu örtüşmesi, örneklem sayısı ve varsa paylaşılmış en benzer rüya çifti.
- Yeterli rüya yoksa oran yerine neyin eksik olduğu söylenir.
- Aynı modal rüya ↔ rüya benzerliğinde de kullanılır.

## Mobile geçiş hazırlığı

| Şimdi yapılır | Neden |
| --- | --- |
| Tüm veri `api.ts` üzerinden; ekranlarda `fetch` yok (mevcut kural) | İstemci değişince tek katman değişir |
| Kayıt, taslak ve oturum mantığı bileşenlerden ayrı (`recorder.ts`, `draft.ts`, `session.ts`) | Mobilde yeniden kullanılır |
| Metinler tek dosyada | Çeviri ve paylaşım |
| Web mobil genişlikte tasarlanır (320–390 px) | Asıl hedef telefon |
| Üretilen TS istemci ve tipler | Mobil uygulama aynı paketi kullanır |

| Sonra yapılır | Tetikleyici |
| --- | --- |
| `apps/mobile` (Expo) ve ortak `packages/` | Beta akışı doğrulanınca |
| Yerel Apple/Google girişi, bildirim | Mobil uygulamayla |
| Sesin doğrudan Storage'a imzalı yükleme | Uzun kayıt ya da zayıf ağ şikâyeti |
| Çevrimdışı kayıt kuyruğu | Mobil uygulamayla |

Beta süresince web, ana ekrana eklenebilir (PWA) hâle getirilir; mağaza uygulaması gelene kadar telefonda günlük kullanım böyle sağlanır.

## Erişilebilirlik ve performans

- Her animasyonun azaltılmış hareket karşılığı vardır.
- Okuyucu ve duvar klavyeyle gezilir; görsellerin metin karşılığı altyazıdan gelir.
- İlk yorum cümlesi birkaç saniyede; duvarın ilk ekranı tek istekle dolar.
