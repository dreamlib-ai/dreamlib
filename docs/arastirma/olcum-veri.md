# Araştırma: ölçüm, kodlama ve veri

Rüya içeriği nasıl sayıya dökülür, hangi şema ve ölçekler var, hangi veri setleri açık, dil modelleri bu işte ne kadar iyi. Motorun çıkarım, benzerlik ve metrik kısımlarının doğrudan girdisi. Program: [araştırma](../arastirma.md).

İşaret: ✓ bu turda web'de doğrulandı; ○ genel bilgiden yazıldı, kartla doğrulanacak.

## Kodlama şemaları

| Şema | Ne ölçer | Not |
| --- | --- | --- |
| Hall–Van de Castle (HVdC) | Karakterler, etkileşimler, etkinlikler, duygular, mekânlar, nesneler ✓ | En yaygın şema ✓; elle kodlama çok zaman alır ✓ |
| HVdC duygu sınıfları | Öfke, üzüntü, endişe, şaşkınlık, mutluluk ✓ | Yalnız beş sınıf; olumlu duygu tek kutuda |
| Tipik Rüyalar Anketi (TDQ) | Onlarca tipik temanın ömür boyu yaygınlığı ✓ | Anketler bağımsız içerik verisiyle doğrulanmamış ✓ |
| Rüya Motifleri Ölçeği (Yu) | Motif grupları | Kısa formu Türkçeye uyarlanmış (2018) ✓ |
| Merkezî imge (Hartmann) | Rüyanın en güçlü imgesi ve yoğunluğu ○ | Kapak görseli seçimine fikir verir |
| Tuhaflık ölçekleri | Süreksizlik, uyumsuzluk, belirsizlik ○ | Metrik adayı |
| Lucidlik ölçekleri | Farkındalık, kontrol | Rüyalarda Bilinçlilik Ölçeği Türkçeye uyarlanmış (2025, 551 öğrenci) ✓ |
| MADRE (Mannheim) | Hatırlama sıklığı, kâbus, tutumlar ○ | Onboarding soruları için kaynak |

## Tipik temalar (ilk tohum)

Öğrenci örneklemlerinde kovalanma ve düşme en yaygın temalar: Kanada'da %82 ve %74, Almanya'da %89 ve %74, Hong Kong'da %92 ve %87 ✓. Okul ve cinsel deneyim temaları da %60'ı aşıyor ✓. Almanya'nın temsilî anketlerinde (1956–2000) sıra farklı: felç olma %26, düşme %18, kovalanma %12 ✓.

Okunuşu: oranlar örnekleme ve soru biçimine çok bağlı; öğrenci verisi ile temsilî veri karşılaştırılamaz ✓. Bizim için değeri oranlar değil tema listesinin kendisi: `theme` düğümlerinin ilk tohumu.

## Dil modelleriyle kodlama

- Dönüştürücü tabanlı modellerle HVdC duygu kodlamasının otomatikleştirilmesi; tek kelimelik sözlük yöntemlerinin sınırını aşmak için (Bertolini, Elce ve ark., CLPsych 2024) ✓.
- DReAMy: DreamBank'i indiren, embedding ve kümeleme yapan, HVdC özelliklerini etiketleyen açık Python kitaplığı; çok dilli model seçeneği var ✓.
- Rüya anlatılarının dil modelleri için ne kadar "öngörülemez" olduğu ölçülmüş (Frontiers in Sleep 2025) ✓.
- Duygusal sınıflandırma için doğrulanmış bir LLM aracı (Perogamvros ve ark. 2025) ✓.
- HVdC etiketlemeyi metin üretimi olarak kuran bir çalışmadan söz ediliyor; özgün makale bulunamadı, teyit edilecek ✓.

Bize dersi: çıkarım prompt'umuzun ölçüleceği hazır bir literatür ve araç var; kendi eval setimiz bunlarla karşılaştırılabilir kurulmalı ([LLM](../llm.md)).

## Yapı ve ağ çözümlemesi

- DreamBank'in 18 binden fazla anlatısında her rüya bir konu ağı olarak temsil edilmiş: olumlu rüyalar daha tutarlı ve doğrusal, olumsuzlar daha döngülü ve baskın konulu (2024) ✓. Modülerlik ve yol uzunluğu yapıyı ölçmüş ✓.
- Üç dilde rüya tabiri veri seti, ortak sembol sözlükleriyle birbirine bağlanmış ("Connecting Dream Networks Across Cultures") ✓. Bizim korpusun yapmak istediğinin erken bir örneği.
- Reddit'te denetimsiz konu keşfi, HVdC ile karşılaştırılarak doğrulanmış ✓.

## Veri setleri

| Veri | Büyüklük | Hak | Bizde |
| --- | --- | --- | --- |
| DreamBank ve türevleri | ~30 bin anlatı | CC BY-NC-SA | Var (B) |
| SDDb | ~44 bin anlatı | İzin gerekli | Zenodo kopyası (B) |
| DreamNet (2025) | 1.500 anlatı, 12 tema, 8 duygu; 400'ü EEG'li ✓ | Lisans teyit edilecek | Yok |
| Reddit r/Dreams | 44 bin+ | Platform koşulları | Kullanılmıyor |
| Thompson Motif Dizini veri seti | Motif başına satır | CC BY-SA 4.0 ✓ | Yok (A adayı) |
| Açıklamalı masal külliyatı (Zenodo) | Masallar ve tipler ✓ | Teyit edilecek | Yok |
| Duygu sözlükleri (NRC, GoEmotions) ○ | Kelime ve cümle düzeyinde duygu | Değişir; teyit edilecek | Yok |
| Wikidata, WordNet, ConceptNet ○ | Kavram hiyerarşisi | Açık | Kısmen |
| The Dream Drop | Anonim rüya paylaşımı, kâr amacı gütmeyen ✓ | Araştırma verisi koşulları sorulacak | Yok |

Türkçe gerçek rüya anlatısı veri seti bulunamadı; Türkiye'deki çalışmalar küçük örneklemli ve belirli bir psikolojik değişkene odaklı, literatür sınırlı ✓.

## Sorular

1. HVdC kategorileri ile bizim `entity_kinds` nasıl eşleşir; hangi kategori bizde yok (etkileşim, başarı ve başarısızlık, talih)?
2. Duygu için hangi taksonomi: HVdC'nin beşi, temel duygular, daha ince bir liste? Türkçe karşılıkları nasıl?
3. LLM kodlamasının insan kodlayıcılarla uyumu hangi kategoride düşük?
4. Rüya benzerliği için denenmiş ölçüler neler; embedding uzaklığı insan yargısıyla ne kadar örtüşüyor?
5. Anlatı yapısı (döngü, doğrusallık, baskın konu) ucuz bir metrik olarak çıkarılabilir mi?
6. Rüya uzunluğu ve ayrıntı düzeyi puanları nasıl saptırır; nasıl normalleştirilir?
7. Çok dilli embedding'ler Türkçe rüya dilinde (devrik cümle, sözlü anlatım, transkript hatası) ne kadar sağlam?
8. Tipik tema listeleri arasında (TDQ, Yu, Schredl) ortak çekirdek hangisi?
9. Hangi onboarding soruları (hatırlama sıklığı, kâbus sıklığı, rüyaya tutum) araştırmada standart?
10. DreamNet ve benzeri yeni setlerin lisansı ürün ya da eval için uygun mu?

## Bulunacak metinler

Hall ve Van de Castle'ın içerik çözümlemesi kitabı ve Domhoff'un kodlama kılavuzu (dreamresearch.net) ○; Nielsen ve ark. 2003, tipik rüyalar ○; Schredl 2021, Almanya'da tipik rüyalar ✓; Yu, Rüya Motifleri Ölçeği ve Türkçe uyarlaması ✓; Bertolini ve Elce, otomatik duygu kodlaması ✓; Fogli ve ark. 2020, rüya anlatılarının otomatik çözümlemesi ○; Das ve ark., Reddit çalışması ✓; rüya ağları makalesi ✓; DReAMy belgeleri ✓; Bulkeley'nin kelime arama yöntemi ○.

## Motora taşınabilecekler

- **Düğüm türleri:** karakter (rol ve tanıdıklıkla), etkileşim, etkinlik, mekân, nesne, duygu; HVdC ile karşılaştırılabilir olacak biçimde.
- **Tema tohumu:** tipik rüya listelerinin ortak çekirdeği.
- **Metrikler:** anlatı döngüselliği, baskın konu, tuhaflık, duygu dengesi, karakter sayısı, uzunluk.
- **Eval:** HVdC etiketli örneklerle çıkarım karşılaştırması (B kademesi, yalnız yerelde).
- **Onboarding:** hatırlama ve kâbus sıklığı gibi standart sorular, isteğe bağlı.
- **Sözlük köprüsü:** diller arası sembol bağlama için önceki çalışmanın yöntemi.

## Kaynaklar (bu tur)

- [Bertolini, Elce ve ark., otomatik duygu kodlaması](https://arxiv.org/pdf/2302.14828) · [CLPsych 2024](https://aclanthology.org/2024.clpsych-1.7.pdf)
- [Frontiers in Sleep 2025, perplexity çalışması](https://www.frontiersin.org/articles/10.3389/frsle.2025.1625185/full)
- [DReAMy, GitHub](https://github.com/lorenzoscottb/DReAMy)
- [Rüyaların içeriği ve yapısı duyguyla bağlı](https://arxiv.org/abs/2409.14279)
- [Connecting Dream Networks Across Cultures](https://arxiv.org/pdf/1402.2297)
- [DreamNet 2025](https://arxiv.org/html/2503.05778v1)
- [Schredl 2021, IJoDR](https://journals.ub.uni-heidelberg.de/index.php/IJoDR/article/view/75878)
- [Tipik rüyalar, kültürler arası karşılaştırma (iz sürmek için)](https://www.psychologytoday.com/gb/blog/dream-factory/201411/what-are-the-most-common-dream-themes)
- [Rüyalarda Bilinçlilik Ölçeği Türkçe uyarlaması](https://dergipark.org.tr/en/download/article-file/3696751) · [Rüya Motifleri Ölçeği Türkçe](https://dergipark.org.tr/download/article-file/638795)
