# Görevler

Her satır tek PR'a sığacak büyüklüktedir. Kimlik faz ve sırayı verir; "Önce" sütunu bağımlılıktır. Biten satır silinir. Faz gerekçeleri: [yol haritası](yol-haritasi.md).

İşaret: 🌱 dışarıdan katkıya uygun ilk iş.

## Faz 0: araştırma

İlk tur tamam (2026-11-13): 16 kart, [tema listesi](arastirma/temalar.md), HVdC eşlemesi, uygulama karşılaştırması (mağaza sayfalarından), korpus atlasına metin listesi, motif veri seti önerisi, [hassas içerik taslağı](hassas-icerik.md), fikir süzmesi. İkinci tur (aynı gün): Türk halkbilimi kartı (A10), `trilogy` ölçümü ve lisans çelişkisi (A11), TDQ'nun 56 maddesiyle tema listesi (A12), CLPsych rakamları ve duygu eval hedefi (A13); HVdC insanlar arası uyum, duygularda %63 (A15). Kalanlar:

| No | Görev |
| --- | --- |
| A7 | Hassas içerik taslağını bir ruh sağlığı uzmanına okut; Türkiye destek kaynaklarını doğrula (kenarda; R3 ile betaya çıkarken) |

İkinci tur (2026-11-14): uygulama karşılaştırması güncellendi, Türkiye'deki rüya uygulamaları ve Faladdin eklendi; telefonda görülecek maddeler beta telefon testine (S5) bağlandı (A4). Çelepi tezi indirilemediği için bırakıldı (A14). Kendi kültürünün rüya geleneği kartı topluluğa açık işlere taşındı (A9).

Faz 0 kod içermez. Kartlar `docs/arastirma/notlar/` altına; program: [araştırma](arastirma.md).

## Faz 1: zemin

Yapıldı (2026-11-13): canlı sürüm, avatar, belgeler ve zemin `main`'de (Z1, Z2); birleşmiş dallar silindi (Z3); migration'lar tek klasörde (Z4); yerel not ve env dosyaları git dışı (Z5); tüm geçmişte sır taraması temiz (Z6); yalnız kontrol çalıştıran CI, Actions açık (Z7); proje kimlikleri ve kişisel bilgiler repodan çıktı (Z8); `DREAMLIB_FAKE_AI=1` ile anahtarsız yerel akış (Z9); temiz geçmişli public repo, AGPL-3.0 ve şablonlar (Z10); tercih anketi sitesi duraklatıldı, sonuçlar veritabanında (Z11); ilk altı `good first issue` GitHub'da açık (Z12). Kalanlar:

Anahtarlar sağlayıcı panellerinden döndürüldü, eski Supabase anahtarları kapatıldı (Z5b, 2026-11-14).

## Faz 2: beta çekirdeği

### İş sistemi ve maliyet

Yapıldı: iş türleri kod kaydında, veritabanı check'i kalktı (B1); geçici hatada üstel bekleme, kalıcı hatada tekrar yok (B2); zincir ve tekrar koruması sütunları, öncelik, tür başına eşzamanlılık (B3); `usage` tablosu, OpenRouter ve fal çağrıları satır yazıyor (B4); rüya başına tek durum ucu (B5).

### LLM

Yapıldı: görev tablosu, görev başına model, yedek dizi ve zaman aşımı (L1); Pydantic'ten şemalı çıktı ve JSON modu yedeği (L2); prompt'lar görev dosyalarında, sürümlü (L5); embedding çağrısı (L4); akışlı çağrı ve SSE yardımcısı (L3, uca bağlanması yorum ucuyla); eval iskeleti ve ilk çıkarım seti (L6).

### Motor ve yorum

Yapıldı: pgvector, `entity_kinds` (11 tür tohumlu), `entities`, `entity_aliases`, `dream_entities` (M1; embedding boyutu ve HNSW indeksi L4 ile); `relation_types` (9 ilişki), `edges` (simetrik kenar tek ve sıralı), `dream_embeddings`, `dream_neighbors` ve derinliği üçle sınırlı `dream_chain` (M2; arama yalnız kişinin kendi rüyalarında, rızalılar R1 ile); her yorum ve indeksleme `analyses` satırı, yorum kayıtla rüyaya bağlanır (M3); LLM'siz `index` işi: kayıt ve metin değişince kuyruğa girer, lab motorlarıyla duygu düğümlerini `dream_entities`'e kanıtıyla, bakış açısı ve beyanları `analyses`'e yazar; arka plan işi kullanıcıyı kilitlemez ve günlük haktan düşmez (M4); aynı iş yorumun `objects` ve `features` alanlarını da düğüme açar (sembol, karakter, yer, eylem aday düğüm; tür ve deneyim onaylı tema), kullanıcının düzelttiği tür ve deneyim `user` kaynağıyla yazılır, mevcut rüyalar bir migration'la bir kez yeniden dizinlenir (M8).

| No | Görev | Önce |
| --- | --- | --- |
| M6 | Sözlük: A kademesi ilk dışa aktarım, `lexicon_entries`, düğüm tohumu | M1 |
| M7 | Kümülatif yorum hattı: sözlük ve kişisel bağlamla getir, sentezle (benzer rüyalar M5 gelince) | M3, M6, L3 |

### Rıza ve hesap

| No | Görev | Önce |
| --- | --- | --- |
| R1 | `consents` tablosu, rüya başına kademe ucu, arama fonksiyonlarında erişim kuralı | M2 |
| R2 | Veriyi indir ve hesabı sil (rüya, görsel, kenar, vektör, rıza) | R1 |
| R3 | [Hassas içerik](hassas-icerik.md) politikasını uygula: `sensitive` sınıflaması, destek kartı, eval seti | L6, A7 |

### İkon, dergi, kütüphane

Yapıldı: fal model kaydı (TOML), sürümlü görsel prompt revizyonları, öğrenen süre tahmini ve `etaSeconds`; her kaydedilen görselin genişlik, yükseklik, BlurHash, baskın renk ve 480 px WebP küçük resmi `images` tablosunda, paneller bunlarla gönderilir (G3, Pillow).

| No | Görev | Önce |
| --- | --- | --- |
| G1 | İkon üslup şablonu ve referansı; `glyph` işi | B1, M1 |
| G2 | En sık semboller için toplu ikon üretimi | G1, M6 |
| G4 | `magazines` tablosu ve `spec`; `magazine` işi (kapak dahil) | B3, G3 |
| G5 | Dergi okuyucu: sayfa düzenleri, sayfa çevirme, azaltılmış hareket | G4 |
| G6 | Linkle paylaşım, girişsiz dergi sayfası, önizleme görseli | G4 |
| G7 | Masonry kütüphane duvarı, imleçli sayfalama | G8 | Akışlı yorum ekranı: parça dizisi, satır içi ikon | M7, G1 |

### Sözleşme

Yapıldı: `/api/v1` ve yerinde eski yollar (S1); makine hata kodları (S2); şemadan üretilen TS istemci (S3); ana ekrana eklenebilir web: manifest ve elle yazılmış service worker, API hiç önbelleğe alınmaz (S4).

| No | Görev | Önce |
| --- | --- | --- |
| S5 | Fiziksel iOS ve Android kabul testi listesi ve koşusu; aynı turda rakiplerin telefonda görülecek maddeleri ([karşılaştırma](arastirma/notlar/uygulamalar-karsilastirma.md)) | G8 |

### Fikirlerden (süzme: [fikirler](fikirler.md))

| No | Görev | Önce |
| --- | --- | --- |
| F1 | Sembol kartı: gelenekler arası anlam, kaynak, kişide görülme sayısı; ikonu çizenin adı | M6, G1 |
| F2 | Yıl dönümü: bir yıl önceki dergi sabah kütüphanenin üstünde | G4 |
| F3 | Açılışta doğrudan kayıt; kayıttan önce bildirim, rozet ya da ekran yok | — |
| F4 | Kâbus sonrası "sonunu yeniden yaz"; ilk anlatım korunur | R3 |
| F5 | Onboarding'de isteğe bağlı "hangilerini gördün" tipik tema seçimi | G1 |
| F6 | `features` sürüm 2: karakter rolü, etkileşim, sonuç, mekân tanıdıklığı, eylemlilik | L2 |

### Beyin grafiği

Her kullanıcının rüyaları bir uzay kanvasında düğüm; ilişkiler türüne göre renkli bağlar. Zayıf ilişki tutulmaz, bağı olmayan rüya uzayda süzülür (Cenker, 2026-11-14). İlk sürüm LLM'siz, M4 ve M8'in düğümlerinden; vektör benzerliği (M10) gelince ayrı bir bağ türü olarak eklenir.

Yapıldı: dört ilişki türü (`shares_content`, `shares_concept`, `shares_emotion`, `near_in_time`), IDF ağırlıklı puanlayıcılar `backend/app/engine/relations.py`'de; eşiğin altı yazılmaz, tür başına en güçlü birkaç bağ kalır; `index` işi yeni rüyanın bağlarını yazar ve eskilerini siler, `brain_links` kişinin derlemini tek sorguda verir, mevcut rüyalar bir kez yeniden dizinlenir (BG1); `GET /api/v1/brain` bütün rüyaları (tarih, duygular, küçük resim, bağ sayısı) ve bağları kanıtıyla tek yanıtta verir (BG2); "Beyin" sekmesi: gece göğünde kuvvet yerleşimli grafik (bağımlılıksız canvas), dört renkli bağ (yakın zaman kesikli), duygu halkalı düğümler, bağsız rüyalar dış halkada süzülür; sürükle, kaydır, yakınlaştır, tür filtresi, dokununca kanıtlı bağ kartı ve komşu vurgusu, azaltılmış harekette durağan, ekran okuyucu için rüya listesi (BG3); kartta "Bir rüyaya bağla" ile elle bağ (`series`, beyaz) ve her bağda × ile kaldırma/gizleme (`hidden`), yeniden puanlama bunlara dokunmaz (BG4).

| No | Görev | Önce |
| --- | --- | --- |
## Sonraki major (betadan sonra)

Beta, anlat → yorum → dergi → kütüphane akışına odaklanır; benzerlik ve lab'ın gerçek veri işi buraya alındı (Cenker, 2026-11-14).

| No | Görev | Önce |
| --- | --- | --- |
| M5 | `similar` puanlayıcısı ve kanıt; kişinin kendi rüyaları arasında (lab v0: `app/lab/similarity.py`) | M2, M4 |
| M9 | 🌱 Altın benzerlik çiftleri ve puanlayıcı testi | M5 |
| M10 | Vektörleme: `dream_embeddings` doldurma; embedding modeli (L4) ya da yerel model kararı ([lab](lab.md), A/B/C) | M4 |
| LB1 | Lab gerçek veri: kurallar yazılırken görülmemiş gerçek raporlar, HVdC'ye göre iki kodlayıcı; kaynaklar tez (A14), DreamBank | — |

## Faz 3: kolektif

| No | Görev | Önce |
| --- | --- | --- |
| K1 | Kullanıcılar arası `similar` kenarları (rızalı) | R1, M5 |
| K2 | Profil vektörü ve `rem` kenarı; eşleşme ucu | K1 |
| K3 | Eşleşme modalı | K2 |
| K4 | Kolektif toplamlar (beş kişi kuralı) ve yorumda kullanımı | K1, M7 |
| K5 | Herkese açık kütüphane, tepkiler | G6, G7 |
| K6 | Moderasyon çağrısı, şikâyet, engelleme, geri çekme | K5 |
| K7 | Kütüphane havuzu animasyonu | G7 |
| K8 | fal webhook ucu ve imza doğrulama | B2 |
| K9 | `video` işi, bayrak ve ayrı hak | K8, G4 |
| K10 | 🌱 Rüya bağışı formu ve açık veri seti dışa aktarımı | R3 |
| K11 | Aday düğüm birleştirme önerileri ve onay akışı | M4 |
| K12 | Rüya ikizi: rızalı benzer rüya bildirimi, yalnız ortak semboller | K1 |
| K13 | `motif` düğümleri ve `evokes_motif` puanlayıcısı (Thompson dizini, seviye 1–3) | M4, V6 (`trilogy` lisans teyidi) |
| K14 | Çevre: küçük grupta paylaşım ve eşleşme; "benim rüyam olsaydı" tepkisi | R1, G6 |

## Veri işleri (koddan bağımsız, paralel)

| No | Görev |
| --- | --- |
| V1 | Tüm `entries.jsonl` dosyalarını tek tabloda birleştir ve tekilleştir |
| V2 | Sembol başlıklarını kavramlara bağla (`concept_id`, QID) |
| V3 | A kademesi anlamları dışa aktar; kaynak ve yer bilgisiyle |
| V4 | Internet Archive OCR metinlerini maddeye çevir |
| V5 | Çevrimdışı: sembol IDF ve birliktelik, benzerlik eşiği, altın çiftler |
| V6 | Hak sahiplerine izin yazıları; yanıtları kaydet (ilk sırada `trilogy`: README CC BY-SA, `LICENSE.md` CC BY-NC-SA) |
| V7 | 🌱 Yeni bir kültürün serbest lisanslı tabir kaynağını ekle |

## Topluluğa açık sürekli işler

- 🌱 Bir sembolün ikonunu çiz ya da iyileştir.
- 🌱 Sembol etiketlerini bir dile çevir.
- 🌱 Eval setine zor bir rüya örneği ekle.
- 🌱 Yeni bir dergi sayfa düzeni tasarla.
- 🌱 Arayüz metinlerini çevir.
- 🌱 Kendi kültürünün rüya geleneği üzerine bir araştırma kartı yaz (Türkçesi: [halkbilimi kartı](arastirma/notlar/kultur-turk-halkbilimi.md)).
