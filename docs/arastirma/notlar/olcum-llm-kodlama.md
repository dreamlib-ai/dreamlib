# Dil modelleri rüya içeriğini ne kadar iyi kodlar?

2026-11-13 · ölçüm ve veri

**Kısa cevap:** Rüya anlatılarında dil modeli kullanımı hızla büyüyen bir alan. Bertolini, Elce ve arkadaşları dönüştürücü tabanlı modellerle HVdC'nin duygu kodlamasını otomatikleştirmeyi denedi (arXiv 2023, CLPsych 2024); amaç, tek kelimelik sözlük yöntemlerinin sınırlarını aşmak. Aynı grubun DReAMy kitaplığı DreamBank'i indirip embedding, kümeleme ve HVdC özellik etiketlemesi yapıyor; çok dilli model seçeneği var. 2025'te rüya anlatılarının dil modelleri için ne kadar öngörülemez olduğu perplexity ile ölçüldü (Frontiers in Sleep). Perogamvros ve arkadaşları duygusal rüya sınıflaması için bir LLM aracı geliştirip doğruladı (*Journal of Sleep Research* 2025). HVdC etiketlemeyi metin üretimi olarak kuran bir çalışmadan söz ediliyor ama özgün makale bulunamadı. HVdC elle kodlaması çok zaman alıcı; otomasyonun ana motivasyonu bu.

**Kaynaklar:**
- Bertolini, Elce ve ark., otomatik duygu kodlaması — hakemli. [arXiv](https://arxiv.org/pdf/2302.14828) · [CLPsych 2024](https://aclanthology.org/2024.clpsych-1.7.pdf)
- DReAMy kitaplığı — açık kaynak araç. [GitHub](https://github.com/lorenzoscottb/DReAMy)
- Bertolini, Consoli, Weeds (2025), *Frontiers in Sleep* — hakemli. [Frontiers](https://www.frontiersin.org/articles/10.3389/frsle.2025.1625185/full)
- DreamNet (2025): 1.500 anlatı, 12 tema, 8 duygu, 400'ü EEG eşli — ön baskı. [arXiv](https://arxiv.org/html/2503.05778v1)

**CLPsych 2024 rakamları (A13):** Bertolini, Elce, Michalak, Widhoelzl, Bernardi, Weeds, "Automatic Annotation of Dream Report's Emotional Content with Large Language Models". Veri: DreamBank'in HVdC kodlu ~1,8 bin İngilizce anlatısından en az bir duygu içeren 922'si, altı seri. Yöntem: BERT-large-cased ince ayarı, beş duygunun her biri için var/yok (çok etiketli), 5 katlı çapraz doğrulama. Sonuç (F1, rüyacının duyguları / tüm karakterlerin duyguları): öfke 87/87, endişe 87/89, **üzüntü 77/80**, şaşkınlık 82/88, mutluluk 89/87; makro ortalama 85/86, ağırlıklı 85/87. Üzüntü en seyrek ve en oynak sınıf (±11). Rüyacı setinde kesinlik duyarlılıktan yüksek: model az etiketliyor, kaçırıyor. Hazır bir duygu modeliyle olumlu/olumsuz ikili sınıflamada olumsuz F1 0,86–0,87, **olumlu yalnız 0,52–0,53**. İnsan kodlayıcılar arası uyum makalede verilmiyor; tavan bilinmiyor. PTSD'li bir gazinin 98 rüyasında model %84'ünde duygu buldu, en sık endişe.

**İnsanlar arası uyum (A15):** Hall ve Van de Castle kendi sistemlerini 50–100 anlatıda bağımsız kodlayıp karşılaştırdı; ölçü "tam uyum yüzdesi" (en az bir kodlayıcının var dediği öğelerde, uyuşan / uyuşan + uyuşmayan). Kategori sayılarında korelasyon genelde .90'ın üstünde; tam uyum %54–%100. Duygular (100 anlatı): **%63**; karakter varlığı %93, nesne %83, etkinlik %85, mekân %73, saldırganlık %54, dostluk %61, başarı %56. Duygu tam uyumu kimin, hangi duyguyu, hangi yoğunlukta hissettiğinin hepsini ister; CLPsych'teki rapor başına var/yok görevinden daha zordur, bu yüzden iki rakam doğrudan karşılaştırılmaz. Kaynak: Domhoff, *Finding Meaning in Dreams* (1996), 2. bölüm, Tablo 2.1 — kitap. [dreams.ucsc.edu](https://dreams.ucsc.edu/Library/fmid2.html)

**Güven:** orta. Alanın yönü net; CLPsych rakamları makaleden doğrudan okundu ama tek veri seti, tek dil ve ince ayarlı model; bizim prompt tabanlı çıkarımımıza doğrudan aktarılmaz.

**Motora etkisi:**
- *Eval:* kendi çıkarım eval setimiz HVdC sınıflarıyla karşılaştırılabilir kurulur; DReAMy'nin etiketleri ve DreamBank-annotated yerelde karşılaştırma tabanı olur (B kademesi, ürüne girmez).
- *Duygu taksonomisi:* HVdC'nin beş sınıfı (öfke, üzüntü, endişe, şaşkınlık, mutluluk) kaba; bizim serbest duygu etiketlerimiz bu beşe de eşlenerek saklanmalı ki hem ince gösterim hem karşılaştırılabilir ölçüm olsun.
- *Model seçimi:* rüya anlatıları LLM'ler için alışılmadık metin; ucuz `extract` modeli seçilirken rüya diline özgü eval şart ([LLM](../../llm.md)).
- *Eval hedefi:* duygu çıkarımı beş HVdC sınıfına eşlenip makro F1 ≥ 0,80, üzüntü ≥ 0,70 ile ölçülür; hedef [LLM](../../llm.md) belgesinin eval bölümünde. Eval setinde üzüntü ve mutluluk örnekleri bilerek çoğaltılır.
- *Araç:* DReAMy Python kitaplığı çevrimdışı araştırmada kullanılabilir; ürüne bağımlılık olarak girmez.
- *Lisans uyarısı:* DreamNet'in lisansı teyit edilmeden eval'e alınmaz.

**Açık kalan:** HVdC için şansa göre düzeltilmiş uyum (κ) yayımlanmamış; kendi elle kodlanmış setimizde iki kodlayıcıyla κ ölçülmeli ve model hedefi onunla kıyaslanmalı. Türkçe anlatılar için karşılaştırma verisi yok; kendi elle kodlanmış setimiz ilk olacak.

**Veri:** DReAMy (araç), DreamNet (lisans teyidi bekliyor).
