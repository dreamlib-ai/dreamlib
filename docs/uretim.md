# Üretim: işler, fal, tekrar, ikon, dergi, video

Uzun süren her şey (indeksleme, ikon, dergi, video) Postgres `jobs` kuyruğundan geçer. Bugünkü kuyruk sağlam; eksik olan, yeni iş türlerini ve zincirleri taşıyacak genellik. Bugünkü durum: [mimari](mimari.md).

## İş sistemi

| Değişiklik | Bugün | Hedef |
| --- | --- | --- |
| İş türü | Yapıldı (B1): türler `pipelines/registry.py` içindeki `KINDS` kaydında; sütunda yalnız biçim check'i | Yeni tür bir kayıt satırıdır |
| Eşzamanlılık | Yapıldı (B3): tek aktif iş kuralı yalnız `exclusive` türlerde (`manga`, `image`) | `index` ve `glyph` kayda `exclusive=False` ile girer |
| Bekleme | Yapıldı (B2): geçici hatada `run_after` ile 5, 20, 80 sn (±%25) bekleme; kalıcı hatada tekrar yok | — |
| Zincir | Sütunlar var (B3): `dream_id`, `parent_id` | Biten iş sonrakini kuyruğa yazar (`index` işiyle, M4) |
| Tekrar koruması | Yapıldı (B3): kullanıcı, tür ve `dedupe_key` tekil; ikinci istek mevcut işi döner. Manga `requestId` ile sürüyor | — |
| Öncelik | Yapıldı (B3): `priority` kayıttan; çizim 10, arka plan 0 | — |

Bir rüyanın yolu:

```
anlatım ─> akışlı yorum (senkron, SSE)
              └─> index ─> glyph (eksik ikon varsa)
              └─> magazine ─> (istenirse) video
```

`index` ve `magazine` birbirini beklemez. İstemci tek uçtan rüyanın tüm işlerinin durumunu okur.

## Hata ve tekrar

Hatalar iki sınıftır; sınıfı sağlayıcı istemcisi belirler (`providers/errors.py`, `ProviderError.status`), worker yalnız uygular. Bilinmeyen hata geçici sayılır: en çok üç denemeyle sınırlı. fal ve OpenRouter istemcileri bu sınıfla hata verir.

| Sınıf | Örnek | Davranış |
| --- | --- | --- |
| Geçici | 429, 5xx, zaman aşımı, ağ hatası | Bekleyip tekrar: 5 sn, 20 sn, 80 sn (jitter'lı), en çok 3 deneme |
| Kalıcı | İçerik reddi, bozuk girdi, okunamayan taslak | Tekrar yok; iş `failed`, kullanıcıya anlaşılır mesaj |
| Kısmi | 6 panelden 1'i çizilemedi | Biten paneller korunur; yalnız eksik panel tekrar edilir |

Korunan mevcut davranışlar: lease ve heartbeat, süreç ölünce devralma, saklı fal istek adresleriyle yeniden ödememe, başarısız işte yüklenen dosyaların silinmesi, başarısız işin günlük haktan düşmemesi. Kalıcı başarısız işler elle yeniden kuyruğa alınabilir (betik).

## fal entegrasyonu

- **Model kaydı (yapıldı):** `backend/app/providers/image_models.toml`; her model bir blok: takma ad, fal id'si, rol (`image`, `edit`, `speech`), fiyat, tipik süre, açık/kapalı. `FAL_IMAGE_MODEL` gibi ayarlar takma adı ya da tam id'yi alır. Eklemek bir blok, çıkarmak silmek ya da `enabled = false`; kayıtta olmayan tam id uyarıyla çalışır. `DREAMLIB_IMAGE_MODELS` başka bir dosyayı gösterebilir.
- **Prompt revizyonları (yapıldı):** stil satırları ve fal'a giden bütün şablonlar `prompts/image.py` içinde numaralı revizyonlar (`image@1`). Değişiklik yeni revizyondur, eskisi düzenlenmez (test sabitler). Yeni işler `DREAMLIB_IMAGE_PROMPT` ile seçilen revizyonu kullanır, iş başladığı revizyonu ve modeli kaydeder; tekrar ve panel yenilemede aynı kalır.
- **Süre tahmini (yapıldı):** fal kuyruğu tahmin vermez; durum ucu yalnız `queue_position` (sıradayken) ve `metrics.inference_time` (bitince) döner. `app/eta.py` model başına cezalı (ridge) doğrusal regresyonu her biten istekten sonra özyinelemeli günceller (RLS). Özellikler: görsel sayısı, referans görsel sayısı, ilk bakıştaki sıra. Ön değer kayıttaki tipik süre; ceza tek bir takılmış isteğin eğriyi savurmasını önler. Son hatalar büyükse (ortalama mutlak yüzde hata %25'in üstünde) eski gözlemler hızlı unutulur, küçükse eğri durulur. Gözlemler `generation_timings` tablosunda; açılışta son 500'ü yeniden oynatılır. İş ucu çalışırken `etaSeconds` döner.
- **Kuyruk ve webhook:** istek fal kuyruğuna verilir, adresleri iş durumuna yazılır (bugünkü gibi). Herkese açık API adresi olduğu için fal'a webhook adresi de verilir; imzası doğrulanan çağrı işi uyandırır. Yoklama, webhook gelmezse devreye giren yedektir.
- **İçerik bayrağı:** fal'ın uygunsuz içerik işareti panele yazılır; işaretli görsel paylaşıma çıkamaz.
- **Kalıcılık:** fal adresleri geçicidir; her çıktı Storage'a alınır (bugünkü gibi), genişlik, yükseklik ve blurhash ile birlikte.
- **Maliyet:** her çağrı `usage` tablosuna satır yazar (sağlayıcı, model, birim, tahmini dolar, iş, kullanıcı). Genel harcama freni bu tablodan okunur; frenin kendisi ertelenmiş karardır.

## İkon kütüphanesi

Yorum metni akarken semboller küçük resimlerle görünür. Bunlar rüya başına üretilmez.

- Her onaylı `symbol` düğümü için bir kez, tek üslupta küçük bir ikon üretilir ve açık depoda durur; adres düğüm kimliğinden türetilir.
- Sözlüğün en sık birkaç yüz sembolü betadan önce toplu üretilir.
- Yeni düğüm onaylanınca `glyph` işi kuyruğa girer; ikon gelene kadar düğüm türünün genel ikonu gösterilir.
- Üslup tek bir istem şablonu ve referans görselle sabitlenir; şablon repoda durur.
- İkonlar toplulukça elle çizilip değiştirilebilir ([açık kaynak](acik-kaynak.md)); elle çizilen, üretilenin önüne geçer.

Seçenekler: rüya başına canlı ikon (kişisel ama yavaş ve pahalı), emoji (hızlı ama marka dışı). Kütüphane, hızı ve tutarlılığı birlikte verir ve kolektifle büyür.

## Dergi

Bugünkü manga kitapçığı derginin içeriğidir; dergi ona kapak, sayfa düzeni ve paylaşım ekler.

- `magazines` tablosu: rüya, sahip, `spec` (jsonb), durum, görünürlük (`private`, `link`, `public`), kapak yolu, `share_slug`.
- `spec` yapısaldır: kapak (başlık, görsel, baskın renk), sayfalar (düzen adı, panel, altyazı, alıntı, ikonlar), künye. Okuyucu bunu istemcide çizer; sayfa çevirme animasyonu sunum katmanıdır ve sunucu bilmez.
- Sayfa düzenleri adlandırılmış küçük bir kümedir; yeni düzen eklemek veri değil istemci işidir.
- `magazine` işi: storyboard → paneller (mevcut hat) → kapak → `spec` kaydı → kütüphaneye otomatik kayıt.
- Paylaşım: `link` yalnız adresi bilenle, `public` herkese açık kütüphanede. Paylaşılan sayfa kapaktan önizleme görseli taşır. Ham anlatım paylaşılmaz; altyazılar paylaşılır.
- Yayın öncesi kontrol: fal içerik bayrağı ve bir moderasyon çağrısı; şikâyet ve geri çekme ucu.
- PDF ya da görsel olarak indirme ayrı bir iş türü olarak sonra gelir.

## Video

Video istisnadır: pahalı, yavaş ve çoğu rüyada gereksiz.

- Ayrı iş türü `video`; derginin kapağından ya da seçilen panelden kısa bir klip (görselden videoya).
- Özellik bayrağı ve ayrı günlük hak arkasında; betada yalnız elle açılan hesaplarda.
- Zaman aşımı ve bekleme çizimden uzun tutulur; webhook burada yoklamadan belirgin biçimde iyidir.
- Çıktı Storage'a alınır; dergi `spec`'ine isteğe bağlı alan olarak bağlanır.

## Saklama ve temizlik

- Bitmiş işler 7 gün sonra silinir (bugünkü süpürme); rüyaya bağlanmamış görseller birlikte gider.
- Silinen rüya; panellerini, dergisini, kenarlarını ve vektörünü birlikte götürür.
- İkonlar ve A kademesi sözlük kullanıcıya ait değildir; hesap silinince kalır.

## Yerelde anahtarsız çalışma

Katkıcılar ücretli anahtar olmadan çalışabilmelidir. `DREAMLIB_DEV_AUTH=1` bugün sahte hesap açıyor; buna sahte sağlayıcılar eklenir: sabit JSON döndüren bir LLM ve yer tutucu görsel döndüren bir fal. İş kuyruğu ve hatların tamamı bu sahte sağlayıcılarla uçtan uca koşar; testler de bunları kullanır.
