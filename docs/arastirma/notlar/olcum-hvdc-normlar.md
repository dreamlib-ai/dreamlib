# Hall–Van de Castle normları neyi gösteriyor?

2026-11-13 · ölçüm ve veri · A3

**Kısa cevap:** Hall–Van de Castle (HVdC) normları, Cleveland'daki iki üniversitenin ağırlıkla beyaz, orta sınıf öğrencilerinden toplanan yaklaşık 500 erkek ve 500 kadın rüyasına dayanır (tablo 491 kadın rüyası diyor). Seçili değerler (erkek / kadın): karakterler içinde erkek oranı %67 / %48; saldırganlık/dostluk yüzdesi %59 / %51; fiziksel saldırganlık yüzdesi %50 / %34; saldırganlık içeren rüya %47 / %44; dostluk içeren rüya %38 / %42. Domhoff'a göre cinsiyet ve rüya içeriği üzerine en sistematik bulgular bu sistemden gelir; sonraki tekrarlarda saldırganlık ve olumsuz içerikte bir azalma olabilir.

**Kaynaklar:**
- dreamresearch.net normlar tablosu ve açıklaması — araştırma sitesi (Schneider, Domhoff). [Normlar](https://dreams.ucsc.edu/Norms/main.html) · [Açıklama](https://dreams.ucsc.edu/Norms/main-explanation.html)
- Domhoff (2005), "The Dreams of Men and Women" — makale. [UCSC](https://dreams.ucsc.edu/Library/domhoff_2005c.html)
- Domhoff, Amerikan üniversite öğrencilerinde normatif bulgular — kitap bölümü. [UCSC](https://dreams.ucsc.edu/Library/fmid4.html)

**Güven:** yüksek (tablo değerleri birden çok kaynakta aynı); ama örneklem dar ve eski.

**HVdC kategorileri ve bizim düğüm türlerimiz (A3 ilk eşleme):**

| HVdC kategorisi | Bizdeki karşılık | Durum |
| --- | --- | --- |
| Karakterler (cinsiyet, yaş, tanıdıklık, hayvan, yaratık) | `features.people` | Var ama rol ve tanıdıklık yok → `character` türü |
| Sosyal etkileşimler (saldırgan, dostça, cinsel) | Yok | Eksik → `interaction` türü, kim → kime |
| Etkinlikler (fiziksel, sözlü, hareket, görme…) | `features.events` | Kısmen; tür sınıflaması yok |
| Başarı ve başarısızlık | Yok | Eksik → `outcome` alanı |
| Talih ve talihsizlik | Yok | Eksik → `outcome` alanı |
| Duygular (öfke, endişe, mutluluk, üzüntü, şaşkınlık) | `emotions` (serbest etiket + yüzde) | Var; sınıflar HVdC'ye eşlenmeli |
| Mekânlar (iç, dış, tanıdık, tanıdık değil) | `features.places` | Var ama iç/dış ve tanıdıklık yok |
| Nesneler (beden parçaları, giysi, araç…) | `objects` | Var; HVdC nesne sınıflarına eşlenebilir |
| Değişimler, zaman, olumsuzlar | Yok | Düşük öncelik |
| Yemek, cinsellik gibi temalar | `tags` | Serbest etiket |

**Motora etkisi:**
- *Düğüm türleri:* `character` (rol, tanıdıklık, cinsiyet, yaş grubu), `interaction` (tür, başlatan, hedef), `setting` (iç/dış, tanıdıklık) ve `outcome` (başarı, başarısızlık, talih) [motor](../../motor.md) şemasına önerilir. `entity_kinds` satırı olarak eklenir, şema değişmez.
- *Metrikler:* HVdC'nin oran göstergeleri (saldırganlık/dostluk yüzdesi, erkek/kadın karakter oranı, olumsuz duygu yüzdesi) kişisel istatistikler için hazır ve karşılaştırılabilir göstergeler. Kişiye "normdan sapma" diye sunulmaz; yalnız kendi zaman çizgisinde gösterilir.
- *Çıkarım prompt'u:* `features` sürüm 2'de etkileşim ve sonuç alanları eklenir; eski kayıtlar sürüm 1 kalır.
- *Eval:* DreamBank-annotated (B kademesi, yerel) ile karakter ve duygu çıkarımımız HVdC etiketlerine karşı ölçülebilir.

**Açık kalan:** Türkçe rüya anlatılarında HVdC normları hiç çıkarılmış mı? Bulunamazsa kendi rızalı verimizden ileride türetilen normlar bir araştırma katkısı olur.

**Veri:** DreamBank-annotated (B, yerel).
