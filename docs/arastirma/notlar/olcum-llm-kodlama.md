# Dil modelleri rüya içeriğini ne kadar iyi kodlar?

2026-11-13 · ölçüm ve veri

**Kısa cevap:** Rüya anlatılarında dil modeli kullanımı hızla büyüyen bir alan. Bertolini, Elce ve arkadaşları dönüştürücü tabanlı modellerle HVdC'nin duygu kodlamasını otomatikleştirmeyi denedi (arXiv 2023, CLPsych 2024); amaç, tek kelimelik sözlük yöntemlerinin sınırlarını aşmak. Aynı grubun DReAMy kitaplığı DreamBank'i indirip embedding, kümeleme ve HVdC özellik etiketlemesi yapıyor; çok dilli model seçeneği var. 2025'te rüya anlatılarının dil modelleri için ne kadar öngörülemez olduğu perplexity ile ölçüldü (Frontiers in Sleep). Perogamvros ve arkadaşları duygusal rüya sınıflaması için bir LLM aracı geliştirip doğruladı (*Journal of Sleep Research* 2025). HVdC etiketlemeyi metin üretimi olarak kuran bir çalışmadan söz ediliyor ama özgün makale bulunamadı. HVdC elle kodlaması çok zaman alıcı; otomasyonun ana motivasyonu bu.

**Kaynaklar:**
- Bertolini, Elce ve ark., otomatik duygu kodlaması — hakemli. [arXiv](https://arxiv.org/pdf/2302.14828) · [CLPsych 2024](https://aclanthology.org/2024.clpsych-1.7.pdf)
- DReAMy kitaplığı — açık kaynak araç. [GitHub](https://github.com/lorenzoscottb/DReAMy)
- Bertolini, Consoli, Weeds (2025), *Frontiers in Sleep* — hakemli. [Frontiers](https://www.frontiersin.org/articles/10.3389/frsle.2025.1625185/full)
- DreamNet (2025): 1.500 anlatı, 12 tema, 8 duygu, 400'ü EEG eşli — ön baskı. [arXiv](https://arxiv.org/html/2503.05778v1)

**Güven:** orta. Alanın varlığı ve yönü net; doğruluk rakamları bu turda okunmadı.

**Motora etkisi:**
- *Eval:* kendi çıkarım eval setimiz HVdC sınıflarıyla karşılaştırılabilir kurulur; DReAMy'nin etiketleri ve DreamBank-annotated yerelde karşılaştırma tabanı olur (B kademesi, ürüne girmez).
- *Duygu taksonomisi:* HVdC'nin beş sınıfı (öfke, üzüntü, endişe, şaşkınlık, mutluluk) kaba; bizim serbest duygu etiketlerimiz bu beşe de eşlenerek saklanmalı ki hem ince gösterim hem karşılaştırılabilir ölçüm olsun.
- *Model seçimi:* rüya anlatıları LLM'ler için alışılmadık metin; ucuz `extract` modeli seçilirken rüya diline özgü eval şart ([LLM](../../llm.md)).
- *Araç:* DReAMy Python kitaplığı çevrimdışı araştırmada kullanılabilir; ürüne bağımlılık olarak girmez.
- *Lisans uyarısı:* DreamNet'in lisansı teyit edilmeden eval'e alınmaz.

**Açık kalan:** CLPsych 2024 makalesindeki insan–model uyum rakamları ve hangi duygu sınıfında modelin zayıf kaldığı okunmalı.

**Veri:** DReAMy (araç), DreamNet (lisans teyidi bekliyor).
