# Veri: envanter, hazırlık, gelecek

Motorun üç veri kaynağı var: tabir geleneği (semboller ve anlamları), gerçek rüya anlatıları ve kullanıcıların kendi rüyaları. Her birinin hakkı ve kullanım yeri farklıdır. Karar: [0008](kararlar/0008-korpus-lisans-kademeleri.md).

## Eldeki veri

Kod `corpus/` altında (şu an yalnız `main` dalında; canlı dal `main`'e alınınca birleşir); ham veri git dışında (`CORPUS_ROOT`). Yaklaşık 20 GB, 650 bin tabir satırı, 100 kadar kaynak. Satır biçimi `corpus/README.md` içinde.

| Tür | Örnek kaynak | Büyüklük | Durum |
| --- | --- | --- | --- |
| Klasik tabirname | Artemidoros, Achmet, EEBO, Gutenberg, zh-wikisource | on binlerce satır | Çoğu serbest lisans |
| İslami ve Doğu gelenekleri | OpenITI, GRETIL, Sefaria | ~8 bin satır + işlenmemiş metin | Çoğu NC |
| Modern sözlük siteleri | TR, EN, ZH, JA, KO, FR, IT, DE, RU, PT | ~550 bin satır | Hakları saklı |
| Gerçek rüya anlatısı | DreamBank türevleri (~30 bin), SDDb (~44 bin), dream-observatory (1,6 bin) | ~75 bin rapor | NC ya da izin gerekli |
| Akademik | arXiv, EuropePMC, OpenAlex | üst veri ve makale | Okuma listesi için |
| İşlenmemiş | Internet Archive OCR (603 metin, 11,6 GB) | 9 bin gürültülü satır | Satıra çevrilecek |

## Lisans kademeleri

| Kademe | Lisans | Ürüne girer | Public repoya girer | Kullanım |
| --- | --- | --- | --- | --- |
| A | Kamu malı, CC0, CC BY, CC BY-SA | Evet, kaynak gösterilerek | Evet (işlenmiş sözlük) | Sembol sözlüğü, yorumda alıntı |
| B | CC BY-NC(-SA), izin bekleyen | Hayır | Hayır | Yerelde araştırma, ölçüm, eşik |
| C | Hakları saklı | Hayır | Hayır | Yalnız kapsam haritası (hangi kültürde hangi sembol var) |

B ve C'den ürüne metin, çeviri ya da model eliyle yeniden yazılmış anlam taşınmaz. İzin gelirse kaynak A'ya yükselir ve bu tablo güncellenir.

## Hazırlık hattı

Betikler `corpus/` içinde, çıktılar git dışında. Yeni bağımlılık gerektiren araştırma betikleri backend'e girmez.

1. **Birleştir.** Tüm `entries.jsonl` dosyaları tek tabloda; kaynak, dil, lisans kademesi alanlarıyla.
2. **Tekilleştir.** Aynı kaynaktan kopyalanmış satırlar ve siteler arası alıntılar ayıklanır.
3. **Kavrama bağla.** Sembol başlıkları çok dilli embedding ile kümelenir; her küme bir `concept_id` alır, mümkünse Wikidata QID'ye bağlanır. Belirsiz kümeler elle onaya düşer.
4. **Alanları doldur.** Boş `polarity`, `condition`, `domain` alanları A kademesinde modelle doldurulur ve örneklemle denetlenir.
5. **Dışa aktar.** A kademesi `lexicon` olarak ürüne ve açık veri setine çıkar: kavram, gelenek, anlam, kaynak, yer bilgisi.
6. **OCR metinleri.** Internet Archive kitapları madde madde ayrıştırılır; çoğu kamu malı olduğu için A'ya girer.

Çıktı ürüne iki tablo olarak gelir: kavramlar `entities` tablosunu tohumlar, anlamlar `lexicon_entries` tablosuna girer ([motor](motor.md)).

## Rüya anlatılarıyla çevrimdışı araştırma

B kademesi anlatılar ürüne girmez ama motoru ayarlamak için yerelde kullanılır:

- **Sembol istatistiği:** sıklık, IDF, birlikte görülme. Benzerlik puanındaki ağırlıkların ilk değerleri buradan gelir.
- **Çıkarım ölçümü:** DreamBank-annotated içindeki Hall–Van de Castle etiketleri, çıkarım prompt'unun karakter ve duygu bulma başarısını ölçer.
- **Benzerlik eşiği:** aynı kişinin seri rüyaları "benzer", rastgele çiftler "benzemez" kabul edilerek puan dağılımı çıkarılır.
- **Altın çiftler:** elle seçilmiş 100 kadar çift, puanlayıcı her değiştiğinde yeniden koşulur.

Bu çalışmanın ürüne taşınan tek şeyi ağırlık ve eşik sayılarıdır; anlatı metni, türevi ya da kaynak bazlı tablo taşınmaz. Ürün verisi biriktikçe sayılar rızalı kullanıcı rüyalarından yeniden hesaplanır.

## Gelecekte toplanacak veri

| Kaynak | Ne verir | Koşul |
| --- | --- | --- |
| Uygulama rüyaları | Türkçe ağırlıklı gerçek anlatı, düzeltilmiş etiketler | Rüya başına `collective` ya da `public` rızası |
| Kullanıcı düzeltmeleri | Model çıkarımının doğrusu | Zaten ayrı saklanıyor; eval'e anonim girer |
| Rüya bağışı formu | CC0 açık veri seti | Yetişkin onayı, kişisel bilgi ayıklama, elle gözden geçirme |
| Eşleşme geri bildirimi | "Bu benzerlik doğru mu" | Puanlayıcı ayarı için |
| İzin yazışmaları | DreamBank, SDDb, OpenITI ticari izin | Yazılı yanıt saklanır |

Türkçe gerçek rüya anlatısı neredeyse hiç yok; uygulamanın kendisi bu açığı kapatacak tek kaynaktır.

## Rıza ve gizlilik

Rüya metni sağlık, inanç ve özel hayat bilgisi taşıyabilir; açık rıza gerekir. Kademeler [0007](kararlar/0007-riza-kademeleri.md) içinde.

- Araştırma ve kolektif kullanım kayıt anında topluca değil, rüya başına sorulur.
- Kolektif toplamlar en az beş farklı kişinin rüyasından üretilir.
- Rıza geri çekilince rüyanın kenarları, paylaşımı ve toplamdaki payı silinir.
- LLM sağlayıcısına giden metin için veri saklamayan sağlayıcı tercih edilir ([LLM](llm.md)).
- Hesap silme tüm rüyaları, görselleri, kenarları ve rıza kayıtlarını siler; açık veri setine bağışlanmış anonim kayıt geri çağrılamaz ve bu, bağış anında söylenir.

## Açık işler

- Hak sahiplerine izin yazıları (liste kasa kaydında).
- Kore ve Japon kaynaklarının zayıf kalan kısımları, Wikipedia dökümü.
- Hassas içerik etiketi (kâbus, travma, kendine zarar) için küçük bir eval seti.
- Rüya bağışı formunun metni ve yaş doğrulama yaklaşımı.
