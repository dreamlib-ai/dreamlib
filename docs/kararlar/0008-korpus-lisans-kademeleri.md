# 0008: Korpus lisans kademeleri

Tarih: 2026-11-13. Durum: kabul. İlgili: 2026-10-27 rüya korpusu kaydı (kasa).

## Sorun

Yaklaşık 650 bin tabir satırı ve 75 bin gerçek rüya anlatısı toplandı. Çoğunun hakkı saklı ya da ticari kullanıma kapalı. Ürün abonelikle gelir elde edecek ve repo açık olacak. Hangi veri nereye girebilir?

## Seçenekler

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Hepsini ürüne bağla | En zengin yorum, dolu kolektif | Telif ve lisans ihlali; açık repoda dağıtım ihlali büyütür |
| Betada gelir yokken NC veriyi istatistik tohumu olarak kullan | Kolektif ilk günden dolu görünür | Abonelik öncesi sökmek gerekir; gri alan; kullanıcıya gösterilen sayı izinsiz veriden gelir |
| Lisans kademeleri: A ürüne, B yalnız çevrimdışı, C hiç | Savunulabilir; açık veri setiyle uyumlu | Kolektif katman betada seyrek; sözlük dar başlar |
| İzin gelene kadar B'ye hiç dokunma | En temkinli | Benzerlik eşiği ve çıkarım ölçümü gerçek veri birikene kadar kör kalır |

## Karar

Üç kademe:

| Kademe | Lisans | Ürün | Public repo | Kullanım |
| --- | --- | --- | --- | --- |
| A | Kamu malı, CC0, CC BY, CC BY-SA | Evet, kaynak gösterilerek | Evet | Sembol sözlüğü, yorumda alıntı, açık veri seti |
| B | CC BY-NC(-SA) ya da izin bekleyen | Hayır | Hayır | Yerelde araştırma, ölçüm ve eşik çalışması |
| C | Hakları saklı | Hayır | Hayır | Yalnız kapsam haritası |

B ile yapılan çevrimdışı çalışmadan ürüne yalnız ağırlık ve eşik sayıları taşınır. Ayrıntı: [veri](../veri.md).

## Gerekçe

- Açık kaynak ve AGPL, veride de temiz olmayı gerektirir; repoya giren veri herkesçe yeniden dağıtılır.
- Yorumun kalitesi sözlük hacminden değil, rüyanın kendisine ve kişinin geçmişine bağlanmasından gelir; A kademesi klasik kaynaklar kaynak gösterimi için yeterlidir.
- Çevrimdışı ölçüm, ürüne veri taşımadan motorun ilk ayarını yapmayı sağlar.
- Kalıcı çözüm rızalı kullanıcı verisi ve bağışlanan rüyalardır; bunlar birikince sayılar oradan yeniden hesaplanır.

## Kurallar

- Her korpus satırı lisans ve hak sahibi alanı taşır; alan boşsa satır C sayılır.
- Dışa aktarım betiği yalnız A kademesini okur; kademe listesi kodda açıkça yazılıdır.
- B ve C metni modele yeniden yazdırılarak ürüne taşınmaz.
- CC BY-SA kaynaklı alanlar açık veri setinde aynı lisansla ve kaynak gösterilerek yayımlanır.
- İzin yazışmaları saklanır; yazılı izin gelen kaynak A'ya yükseltilir ve bu belge güncellenir.
- Toplayıcılar robots.txt ve erişim reddini aşmaz (mevcut kural).

## Yeniden değerlendirme tetikleyicileri

- DreamBank ya da SDDb hak sahiplerinden yazılı izin.
- Bir C kaynağıyla lisans anlaşması.
- Hukuki görüş, çevrimdışı çalışmadan sayı taşımayı da sakıncalı bulursa: sayılar yalnız A ve rızalı kullanıcı verisinden üretilir.

## Geri dönüş yolu

Ürüne giren her sözlük satırı kaynağını taşır; bir kaynağın durumu değişirse satırları tek sorguyla çıkarılır. Ağırlık ve eşikler `algo_version` ile sürümlüdür; kaynağı tartışmalı bir sayı yeni sürümle değiştirilir.
