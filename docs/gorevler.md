# Görevler

Her satır tek PR'a sığacak büyüklüktedir. Kimlik faz ve sırayı verir; "Önce" sütunu bağımlılıktır. Biten satır silinir. Faz gerekçeleri: [yol haritası](yol-haritasi.md).

İşaret: 🌱 dışarıdan katkıya uygun ilk iş.

## Faz 0: araştırma

İlk tur tamam (2026-11-13): 16 kart, [tema listesi](arastirma/temalar.md), HVdC eşlemesi, uygulama karşılaştırması (mağaza sayfalarından), korpus atlasına metin listesi, motif veri seti önerisi, [hassas içerik taslağı](hassas-icerik.md), fikir süzmesi. İkinci tur (aynı gün): Türk halkbilimi kartı (A10), `trilogy` ölçümü ve lisans çelişkisi (A11), TDQ'nun 56 maddesiyle tema listesi (A12), CLPsych rakamları ve duygu eval hedefi (A13); HVdC insanlar arası uyum, duygularda %63 (A15). Kalanlar:

| No | Görev |
| --- | --- |
| A4 | Mirror, Oniri, The Dream Drop, Remora ve Türkiye'deki rüya uygulamalarını elle dene; karşılaştırma kartını tamamla |
| A7 | Hassas içerik taslağını bir ruh sağlığı uzmanına okut; Türkiye destek kaynaklarını doğrula |
| A9 | 🌱 Kendi kültürünün rüya geleneği üzerine bir araştırma kartı yaz |
| A14 | Çelepi'nin *Türk Halk Kültüründe Rüya* tezini indir (Açık Bilim, CC BY 4.0 görünüyor); lisansı teyit et, pratik listesini halkbilimi kartına ve korpus atlasına ekle |

Faz 0 kod içermez. Kartlar `docs/arastirma/notlar/` altına; program: [araştırma](arastirma.md).

## Faz 1: zemin

Yapıldı (2026-11-13): canlı sürüm, avatar, belgeler ve zemin `main`'de (Z1, Z2); birleşmiş dallar silindi (Z3); migration'lar tek klasörde (Z4); yerel not ve env dosyaları git dışı (Z5); tüm geçmişte sır taraması temiz (Z6); yalnız kontrol çalıştıran CI, Actions açık (Z7); proje kimlikleri ve kişisel bilgiler repodan çıktı (Z8); `DREAMLIB_FAKE_AI=1` ile anahtarsız yerel akış (Z9); temiz geçmişli public repo, AGPL-3.0 ve şablonlar (Z10); tercih anketi sitesi duraklatıldı, sonuçlar veritabanında (Z11); ilk altı `good first issue` GitHub'da açık (Z12). Kalanlar:

| No | Görev | Önce |
| --- | --- | --- |
| Z5b | Bakımcının yerel `dreamlib-vibe/` env dosyasındaki anahtarları sağlayıcı panellerinden döndür | — |

## Faz 2: beta çekirdeği

### İş sistemi ve maliyet

Yapıldı: iş türleri kod kaydında, veritabanı check'i kalktı (B1); geçici hatada üstel bekleme, kalıcı hatada tekrar yok (B2); zincir ve tekrar koruması sütunları, öncelik, tür başına eşzamanlılık (B3); `usage` tablosu, OpenRouter ve fal çağrıları satır yazıyor (B4).

| No | Görev | Önce |
| --- | --- | --- |
| B5 | Rüya başına tek durum ucu | B3 |

### LLM

Yapıldı: görev tablosu, görev başına model, yedek dizi ve zaman aşımı (L1); Pydantic'ten şemalı çıktı ve JSON modu yedeği (L2).

| No | Görev | Önce |
| --- | --- | --- |
| L3 | Akışlı çağrı ve SSE'ye çeviri | L1 |
| L4 | Embedding çağrısı | L1 |
| L5 | Prompt'ları görev dosyalarına böl, sürüm kimliği ver | L1 |
| L6 | 🌱 `evals/` iskeleti, kayıtlı yanıtla koşan ilk çıkarım seti | L2 |

### Motor ve yorum

| No | Görev | Önce |
| --- | --- | --- |
| M1 | pgvector, `entity_kinds`, `entities`, `entity_aliases`, `dream_entities` | Z1 |
| M2 | `relation_types`, `edges`, `dream_embeddings` ve arama SQL fonksiyonları | M1 |
| M3 | `analyses` tablosu; yorum yeni satır yazsın, eski alanlar okunmaya devam etsin | Z1 |
| M4 | `index` işi: çıkar, normalize et, vektörle | M1, L2, L4, B3 |
| M5 | `similar` puanlayıcısı ve kanıt; kişinin kendi rüyaları arasında | M2, M4 |
| M6 | Sözlük: A kademesi ilk dışa aktarım, `lexicon_entries`, düğüm tohumu | M1 |
| M7 | Kümülatif yorum hattı: sözlük ve kişisel bağlamla getir, sentezle | M3, M5, M6, L3 |
| M8 | Mevcut `features` ve `objects` alanlarını `dream_entities`'e açan geçiş | M4 |
| M9 | 🌱 Altın benzerlik çiftleri ve puanlayıcı testi | M5 |

### Rıza ve hesap

| No | Görev | Önce |
| --- | --- | --- |
| R1 | `consents` tablosu, rüya başına kademe ucu, arama fonksiyonlarında erişim kuralı | M2 |
| R2 | Veriyi indir ve hesabı sil (rüya, görsel, kenar, vektör, rıza) | R1 |
| R3 | [Hassas içerik](hassas-icerik.md) politikasını uygula: `sensitive` sınıflaması, destek kartı, eval seti | L6, A7 |

### İkon, dergi, kütüphane

| No | Görev | Önce |
| --- | --- | --- |
| G1 | İkon üslup şablonu ve referansı; `glyph` işi | B1, M1 |
| G2 | En sık semboller için toplu ikon üretimi | G1, M6 |
| G3 | Görsel kaydında genişlik, yükseklik, blurhash, baskın renk, küçük resim | — |
| G4 | `magazines` tablosu ve `spec`; `magazine` işi (kapak dahil) | B3, G3 |
| G5 | Dergi okuyucu: sayfa düzenleri, sayfa çevirme, azaltılmış hareket | G4 |
| G6 | Linkle paylaşım, girişsiz dergi sayfası, önizleme görseli | G4 |
| G7 | Masonry kütüphane duvarı, imleçli sayfalama | G3 |
| G8 | Akışlı yorum ekranı: parça dizisi, satır içi ikon | M7, G1 |

### Sözleşme

| No | Görev | Önce |
| --- | --- | --- |
| S1 | `/api/v1` ve eski yolların yönlendirmesi | — |
| S2 | Makine hata kodları | S1 |
| S3 | OpenAPI'den üretilen TS istemci; `api.ts` onu kullansın | S1 |
| S4 | Ana ekrana eklenebilir web (PWA) | — |
| S5 | Fiziksel iOS ve Android kabul testi listesi ve koşusu | G8 |

### Fikirlerden (süzme: [fikirler](fikirler.md))

| No | Görev | Önce |
| --- | --- | --- |
| F1 | Sembol kartı: gelenekler arası anlam, kaynak, kişide görülme sayısı; ikonu çizenin adı | M6, G1 |
| F2 | Yıl dönümü: bir yıl önceki dergi sabah kütüphanenin üstünde | G4 |
| F3 | Açılışta doğrudan kayıt; kayıttan önce bildirim, rozet ya da ekran yok | — |
| F4 | Kâbus sonrası "sonunu yeniden yaz"; ilk anlatım korunur | R3 |
| F5 | Onboarding'de isteğe bağlı "hangilerini gördün" tipik tema seçimi | G1 |
| F6 | `features` sürüm 2: karakter rolü, etkileşim, sonuç, mekân tanıdıklığı, eylemlilik | L2 |

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
