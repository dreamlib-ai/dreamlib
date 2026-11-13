# Masal ve mit motifleri rüyalarla eşlenebilir mi? (Thompson Motif Dizini)

2026-11-13 · mitoloji ve kültür · A6

**Kısa cevap:** Veri hazır ama lisansı çelişkili. Hagedorn'un `trilogy` reposu Thompson Motif Dizini'ni ve Aarne-Thompson-Uther (ATU) masal tipi dizinini düzenli tablolar olarak sunar. README CC BY-SA 4.0 diyor; repoya 2024-01-08'de eklenen `LICENSE.md` ise **CC BY-NC-SA 4.0** metni; Zenodo kaydı (10.5281/zenodo.6575263) yalnız "other-open" diyor. Daha kısıtlayıcı olan geçerli sayılır: lisans yazarla netleşene kadar veri **B kademesi**, yalnız çevrimdışı araştırma (A11 ölçümü, 2026-11-13).

**Ölçüm (A11, `data/tmi.csv`, commit `d57c2ce`):** 46.230 motif satırı; 23 bölüm (en büyükleri Büyü 7.165, Mitler 5.810, Harikalar 5.366). Seviye dağılımı: 0: 217, 1: 1.253, 2: 10.679, 3: 20.476, 4: 9.297, 5: 2.529, 6: 361, boş 1.418. Seviye 1–3 toplam 32.408. Adında "dream" geçen motif 135 (ör. A1399.2 rüyaların kökeni, D812.8 rüyada verilen büyülü nesne, C168 rüya uyarısını çiğneme yasağı).

**Tema örtüşmesi (anahtar kelime, seviye 1–3 motif adı):** Hayvanlar 3.578, doğaüstü 2.655, dinî 2.151, ilişkiler 2.032, şiddet ve ölüm 1.426, su 1.128, iş 732, cinsellik 635, beden 575, gökyüzü ve uzay 536, ev ve odalar 451, afet 436; düşme 194, kovalanma 132, uçma 104, ölmüş birinin dönmesi 55, çıplaklık 47, okul 37, felç 18, geç kalma 18, sevilen birinin ölümü 8; teknoloji ve rüya kontrolü 0. Sayım kaba bir üst sınırdır (ör. "magic flight" bir kaçış motifidir, uçma değil); mitolojik ve doğaüstü temalarda motif zengin, gündelik kaygı temalarında (okul, geç kalma, felç) neredeyse yok.

**Tablolar:**

| Tablo | Satır | Önemli sütunlar |
| --- | --- | --- |
| `tmi` | Motif başına bir satır (üst düzeyler dahil) | `id`, `chapter_name` (Mitler, Hayvanlar, Tabu, Büyü, Ölüm, Harikalar…), `motif_name`, `notes`, `level` (0–6), `level_0`…`level_6` |
| `atu_df` | Masal tipi başına | `atu_id`, `tale_name`, `provenance`, `tale_type` (özet), `combos` |
| `atu_seq` | Masal tipindeki motif sırası | `atu_id`, `motif`, `motif_order` |
| `aft` | Açıklamalı masal metinleri | `atu_id`, `tale_title`, `provenance`, `text`, `source` |

Biçim CSV; `tmi` 7,5 MB, `atu_seq` 11 MB, `aft` 7 MB.

**Kaynaklar:**
- [trilogy, GitHub](https://www.github.com/j-hagedorn/trilogy) ve [veri sözlüğü](https://github.com/j-hagedorn/trilogy/blob/master/docs/data_dictionary.md) — veri seti.
- Hagedorn ve Darányi (2022), açıklamalı masal külliyatı — hakemli.
- Thompson, *Motif-Index of Folk-Literature* (Indiana University Press, 1955) — kaynak eser.

**Güven:** yüksek (veri indirildi ve sayıldı); lisans düşük (üç kaynak üç şey söylüyor).

**Motora etkisi (rüya → motif önerisi):**
- *Düğüm türü:* `motif`. Kaynak `tmi`; kanonik anahtar motif kimliği (ör. `C611`), etiket `motif_name`, hiyerarşi `level_*` sütunlarından `is_a` kenarlarına.
- *İlişki türü:* `evokes_motif` (rüya → motif). Puanlayıcı: rüya anlatısının vektörü ile motif adının ve notlarının vektörü arasında aday bulma, ardından LLM ile doğrulama ("bu rüyada şu motif açıkça var mı, alıntıyla"). Alıntı yoksa kenar yazılmaz.
- *Seviye seçimi:* çok ince motifler (seviye 4–6) rüyaya nadiren oturur; ilk sürümde seviye 1–3 kullanılır.
- *Dil:* motif adları İngilizce; Türkçe etiketler ilk aşamada en sık eşleşen birkaç yüz motif için çevrilir (topluluk işi, 🌱).
- *Arayüz:* sembol kartının yanında "bu rüya şu eski hikâyelere benziyor" satırı; ATU tipinden bir masal adı ve kısa özetle ([fikir 1](../../fikirler.md)).
- *Lisans:* NC okunduğu sürece motif tablosu ürüne ve public repoya girmez; K13 yazardan CC BY-SA teyidi ya da izin bekler. Teyit gelirse türetilmiş tablo aynı lisansla, kaynak gösterilerek yayımlanır.
- *Ölçümün sonucu:* motif eşleşmesi gündelik rüyalarda değil, mitolojik ve doğaüstü öğeli rüyalarda değer üretir. Puanlayıcı yalnız alıntıyla doğrulanan eşleşmede konuşur; çoğu rüyada sessiz kalması beklenir.
- *Şema değişikliği:* gerekmez; yeni bir `entity_kinds` satırı ve bir `relation_types` satırı yeter. [Motor](../../motor.md) belgesinin "yeni ilişki türü eklemek" sözünün ilk gerçek sınavı.

**Açık kalan:** Yazara (Hagedorn) lisans sorusu: README ile `LICENSE.md` hangisi geçerli? Yanıt V6 izin yazıları kaydına girer. Ölçüm anahtar kelimeyle yapıldı; vektörle aday bulma rızalı rüya örnekleriyle yerelde denenmeli.

**Veri:** trilogy (README CC BY-SA 4.0, `LICENSE.md` CC BY-NC-SA 4.0), teyide kadar B kademesi.
