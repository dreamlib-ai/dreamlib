# Masal ve mit motifleri rüyalarla eşlenebilir mi? (Thompson Motif Dizini)

2026-11-13 · mitoloji ve kültür · A6

**Kısa cevap:** Evet, veri hazır. Hagedorn'un `trilogy` reposu, Thompson Motif Dizini'ni ve Aarne-Thompson-Uther (ATU) masal tipi dizinini düzenli tablolar olarak sunar; lisansı CC BY-SA 4.0'dır ve içeriğin kamu malı ya da hak sahibi izniyle olduğu belirtilir. Zenodo DOI: 10.5281/zenodo.6575263. Bu, A kademesine girebilecek ilk büyük dış sözlük.

**Tablolar:**

| Tablo | Satır | Önemli sütunlar |
| --- | --- | --- |
| `tmi` | Motif başına bir satır (üst düzeyler dahil) | `id`, `chapter_name` (Mitler, Hayvanlar, Tabu, Büyü, Ölüm, Harikalar…), `motif_name`, `notes`, `level` (0–6), `level_0`…`level_6` |
| `atu_df` | Masal tipi başına | `atu_id`, `tale_name`, `provenance`, `tale_type` (özet), `combos` |
| `atu_seq` | Masal tipindeki motif sırası | `atu_id`, `motif`, `motif_order` |
| `aft` | Açıklamalı masal metinleri | `atu_id`, `tale_title`, `provenance`, `text`, `source` |

Satır sayıları ve dosya biçimi sayfada yazmıyor; repo indirilince ölçülecek.

**Kaynaklar:**
- [trilogy, GitHub](https://www.github.com/j-hagedorn/trilogy) ve [veri sözlüğü](https://github.com/j-hagedorn/trilogy/blob/master/docs/data_dictionary.md) — veri seti.
- Hagedorn ve Darányi (2022), açıklamalı masal külliyatı — hakemli.
- Thompson, *Motif-Index of Folk-Literature* (Indiana University Press, 1955) — kaynak eser.

**Güven:** yüksek (veri sözlüğü ve lisans doğrudan okundu).

**Motora etkisi (rüya → motif önerisi):**
- *Düğüm türü:* `motif`. Kaynak `tmi`; kanonik anahtar motif kimliği (ör. `C611`), etiket `motif_name`, hiyerarşi `level_*` sütunlarından `is_a` kenarlarına.
- *İlişki türü:* `evokes_motif` (rüya → motif). Puanlayıcı: rüya anlatısının vektörü ile motif adının ve notlarının vektörü arasında aday bulma, ardından LLM ile doğrulama ("bu rüyada şu motif açıkça var mı, alıntıyla"). Alıntı yoksa kenar yazılmaz.
- *Seviye seçimi:* çok ince motifler (seviye 4–6) rüyaya nadiren oturur; ilk sürümde seviye 1–3 kullanılır.
- *Dil:* motif adları İngilizce; Türkçe etiketler ilk aşamada en sık eşleşen birkaç yüz motif için çevrilir (topluluk işi, 🌱).
- *Arayüz:* sembol kartının yanında "bu rüya şu eski hikâyelere benziyor" satırı; ATU tipinden bir masal adı ve kısa özetle ([fikir 1](../../fikirler.md)).
- *Lisans:* CC BY-SA olduğu için türetilmiş motif tablosu (çeviriler dahil) aynı lisansla ve kaynak gösterilerek yayımlanır; uygulama kodu AGPL kalır, veri ayrı lisanslıdır.
- *Şema değişikliği:* gerekmez; yeni bir `entity_kinds` satırı ve bir `relation_types` satırı yeter. [Motor](../../motor.md) belgesinin "yeni ilişki türü eklemek" sözünün ilk gerçek sınavı.

**Açık kalan:** Kaç motif gerçekten rüya diline yakın? Repo indirilip sık rüya temalarıyla (bkz. [tema listesi](../temalar.md)) kaba bir örtüşme sayımı yapılmalı.

**Veri:** trilogy (CC BY-SA 4.0), A kademesi.
