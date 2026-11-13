# Yol haritası

Sıra bağımlılığa göre. Her faz bir öncekinin üstüne kurulur; faz içindeki işler [görevler](gorevler.md) belgesinde issue boyutunda durur. Mevcut kabul tablosu [hedefler](hedefler.md) geçerlidir; bu belge ona sıra ve gerekçe ekler.

## Faz 0: araştırma

Amaç: geliştirmeden önce neye bakılacağını belirlemek ve motoru besleyecek bilgiyi toplamaya başlamak. Kod yok.

- Altı alan: bilim, felsefe, mitoloji ve kültür, kolektif rüya, ölçüm ve veri, uygulamalar ([araştırma](arastirma.md)).
- Her alanda ilk araştırma kartları; bulunacak metinler ve veri setleri lisans kademesiyle listelenir.
- İlk tema listesi ve düğüm türü önerisi: araştırmanın [motor](motor.md) şemasında değiştirdikleri.
- Benzer uygulamaların denenmiş karşılaştırması.
- Ürün fikirlerinin süzülmesi ([fikirler](fikirler.md)).

Çıkış ölçütü: [araştırma](arastirma.md) belgesindeki Faz 0 çıktıları tamam; motor şemasına yansıyan değişiklikler yazıldı. Araştırma burada bitmez; sonraki her fazın yanında haftalık ritimle sürer.

## Faz 1: zemin

Amaç: tek doğru dal, temiz repo, açık kaynağa çıkabilecek hâl.

- Canlı dal `main`'e alınır (28 commit geride); commit'siz avatar işi bir dala bağlanır.
- Eski dallar budanır; iki ayrı migration klasörü (`backend/migrations`, `supabase/migrations`) teke iner.
- Sır temizliği: izlenmeyen klasörlerdeki env ve yönetim dosyaları repodan dışarı, anahtarlar döndürülür; tercih anketi sitesi ve alan adı kapatılır.
- Yalnız kontrol çalıştıran CI; yayın elle kalır. AGENTS'taki "CI yok" kuralı buna göre güncellenir.
- Public repo iskeleti: README, katkı rehberi, lisans, şablonlar ([açık kaynak](acik-kaynak.md)).

Çıkış ölçütü: temiz bir kopyada `npm run check` geçer, sır taraması temiz, `main` canlıyla aynı.

## Faz 2: beta çekirdeği (25 kişi, web)

Amaç: anlat → akışlı yorum → dergi → kütüphane → linkle paylaş akışı uçtan uca; motorun kişisel yarısı çalışır.

| Paket | İçerik |
| --- | --- |
| İş sistemi | Tür kaydı, bekleme, zincir, tür başına eşzamanlılık, `usage` defteri |
| LLM | Görev tablosu, şemalı çıktı, akış, yedek model, embedding |
| Yorum | `analyses` tablosu, çıkar → getir → sentezle hattı (sözlük ve kişisel bağlam) |
| Motor | `entities`, `dream_entities`, `edges`, pgvector; LLM'siz çıkarım ve indeks (benzer rüyalar betadan sonra) |
| Rıza | Üç kademe, rıza defteri, veriyi indir ve sil |
| İkon | Üslup şablonu, en sık semboller için toplu üretim |
| Dergi | `magazines`, kapak, okuyucu, otomatik kayıt, linkle paylaşım |
| Kütüphane | Masonry duvar, küçük resimler, imleçli sayfalama |
| Sözleşme | `/api/v1`, hata kodu, üretilen istemci |

Çıkış ölçütü: [vizyon](vizyon.md) içindeki beta ölçütleri ölçülebilir; fiziksel telefonda (iOS Safari, Android Chrome) akış tamamlanır.

## Faz 3: kolektif

Amaç: kullanıcılar arası bağ. Beta kullanıcıları `collective` rızası verdikçe açılır.

- Kullanıcılar arası `similar` kenarları, eşleşme modalı (REM).
- Kolektif toplamlı yorum (en az beş kişi kuralıyla).
- Herkese açık kütüphane, tepki (beğen, kaydet), şikâyet, engelleme, moderasyon.
- Kütüphane havuzu animasyonu.
- fal webhook, video (bayrak arkasında).
- A kademesi sözlüğün tamamı, kaynak gösterimi.
- Rüya bağışı formu ve ilk açık veri seti sürümü.

Çıkış ölçütü: eşleşme oranı altın çiftlerde beklenen sıralamayı verir; paylaşılan dergi sayısı boş olmayan bir keşif akışına yeter.

## Faz 4: ölçek ve mobil

- Worker ayrı süreç, doğrudan Postgres bağlantısı, okuma kopyası (belirtiye göre, [mimari](mimari.md)).
- Expo mobil uygulama; ortak istemci paketi, yerel giriş, bildirim, çevrimdışı kayıt.
- Gece işleri: düğüm birleştirme önerileri, tema kümeleri, haftalık özet.
- Genel harcama freni, abonelik ve ödeme.
- Mesajlaşma (eşleşenler arası), arkadaş ilişkisi.

## Şimdi ve sonra

| Konu | Şimdi | Sonra | Tetikleyici |
| --- | --- | --- | --- |
| Backend | Modüler monolit, Python | Worker ayrımı; servise bölme | Çizim API'yi yavaşlatırsa; ekipler ayrışırsa |
| Kuyruk | Postgres `jobs` | Mesaj aracısı | Saniyede yüzlerce iş, birden çok tüketici |
| Grafik | Postgres kenar tablosu | Graf veritabanı | Milyonlarca kenar, derin zincir sorguları |
| Vektör | pgvector | Ayrı vektör servisi | On milyonlarca vektör ya da gecikme hedefi tutmazsa |
| Veritabanı erişimi | PostgREST + SQL fonksiyonu | Doğrudan bağlantı | Vektör ve zincir sorguları yavaşlarsa |
| fal | Kuyruk + yoklama | Webhook | Faz 3 |
| İkon | Düğüm başına bir kez | Kişisel ikon | Talep ölçülürse |
| Video | Kapalı | Bayrak arkasında | Faz 3, maliyet ölçülünce |
| Kümeleme | Yok | Gece işi | Binlerce rızalı rüya |
| Keşif | Linkle paylaşım | Herkese açık akış | Yeterli paylaşılan dergi |
| Mobil | Mobil öncelikli web, PWA | Expo uygulama | Beta akışı doğrulanınca |
| Maliyet | Kullanıcı kotası, `usage` ölçümü | Genel fren, abonelik | Açık betadan önce |
| CI/CD | Yalnız kontrol | Otomatik yayın | Birden çok kişi yayın yapınca |

## Betadan sonra beklenenler

- **Benzerlik ve gerçek veri.** Kişinin kendi benzer rüyaları, vektörleme ve lab'ın gerçek veriyle ölçümü betadan sonraki ilk büyük iş ([görevler](gorevler.md), Sonraki major).

- **Veri gelir, varsayımlar değişir.** Benzerlik ağırlıkları ve eşikler çevrimdışı sayılardan gerçek rızalı rüyalara taşınır; ilk haftalarda oranlar oynar, `algo_version` bunu izlenebilir kılar.
- **Sözlük büyür.** Aday düğümler birikir; birleştirme ve onay bir bakım işi olur. Topluluk burada en çok işe yarar.
- **Maliyet görünür olur.** `usage` verisiyle rüya başına gerçek maliyet çıkar; fiyatlandırma ve günlük haklar buna göre yeniden kurulur.
- **Hassas içerik gerçek örnekle gelir.** Politika, ilk gerçek vakadan önce yazılı olmalı ([riskler](riskler.md)).
- **Paylaşım moderasyon ister.** Herkese açık kütüphane, şikâyet ve geri çekme süreci çalışmadan açılmaz.
- **Katkı gelir.** İlk dış katkılar ikon, çeviri ve eval örnekleri olur; inceleme süresi ayrılmalı.

## Belgelerin bakımı

Her `.md` en fazla 160 satır. Biten iş bu belgeden silinir, [hedefler](hedefler.md) tablosunda durumu güncellenir. Yeni karar `docs/kararlar/` altına numarayla eklenir; eski karar silinmez, yerine geçeni gösterilir.
