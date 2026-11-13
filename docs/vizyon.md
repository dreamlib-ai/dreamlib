# Vizyon: kolektif rüya motoru

Dreamlib bir rüya günlüğü olarak başladı. Hedef, insanların rüyalarını tek tek yorumlayan bir araçtan, rüyaları birbirine bağlayan açık bir motora geçmek: kim neyi, hangi duyguyla, kimlerle benzer görüyor.

Bu belge yönü verir. Ayrıntı: [motor](motor.md), [veri](veri.md), [üretim](uretim.md), [LLM](llm.md), [istemci](istemci.md). Sıra: [yol haritası](yol-haritasi.md). Dayanak: [araştırma](arastirma.md), [fikirler](fikirler.md). Kabul tablosu: [hedefler](hedefler.md).

## Ürün tek cümlede

Uyanınca rüyanı sesle anlatırsın; birkaç saniyede sembolleriyle okunur bir yorum, ardından rüyanın dergisi gelir; dergi kütüphanene düşer ve istersen paylaşılır; benzer rüya görenlerle ortak noktaların görünür.

## Kullanıcının yolu

| Adım | Ne görür | Arkada ne olur |
| --- | --- | --- |
| Anlat | Tek mikrofon düğmesi; yazı ikincil | Transkript, taslak kurtarma |
| Yorum | Metin akarken sembollerin küçük ikonları belirir | Çıkarım, normalize, getirme, sentez (akışlı) |
| Dergi | Sayfa çevirerek okunan dergi | Storyboard, paneller, kapak (arka plan işi) |
| Kütüphane | Kapakların durduğu duvar; havuz animasyonu | Otomatik kayıt, küçük resimler |
| Paylaş | Link ya da herkese açık kütüphane | Rıza kademesi, moderasyon |
| Eşleş | Oran ve ortak noktaları gösteren modal | Profil vektörü, kanıtlı kenar |

## İlkeler

1. **Ses önce.** Açılış ekranında tek ana eylem vardır. Yeni özellik bu ekrana düğme eklemez.
2. **Rüya varsayılan özeldir.** Kolektife katılım rüya başına açık seçimle olur ve geri alınır.
3. **Her oran açıklanır.** Benzerlik ve eşleşme yüzdesi, hangi ortak sembol, tema ve duygudan geldiğini gösterir. Açıklanamayan sayı gösterilmez.
4. **Az veride susar.** Yeterli rüya yoksa istatistik, eşleşme ya da kolektif cümle uydurulmaz.
5. **Tabir değil bağlam.** Yorum tek bir sözlük anlamı vermez; rüyanın kendisi, kişinin geçmişi ve benzer rüyalar birlikte okunur.
6. **Basit mühendislik.** Tek süreçli modüler monolit, tek veritabanı. Yeni servis ancak ölçülmüş bir sebeple gelir.
7. **Açık motor, kapalı rüya.** Kod, sembol sözlüğü, ikonlar ve eval açık; kullanıcı rüyası repoya ve açık veri setine girmez.

## Yapılmayacaklar

- Tıbbi, psikolojik ya da kehanet iddiası. Duygu oranları model tahminidir.
- Rızasız eşleştirme, rıza dışı metin gösterme, reklam için rüya verisi.
- Boş bir sosyal akışı açmak. Keşif, paylaşılan dergi sayısı anlamlı olunca açılır.
- Rüya başına canlı ikon üretimi, her rüyaya video. Video istisnadır.
- Mikroservis, mesaj kuyruğu servisi, graf veritabanı (tetikleyicisi gelmeden).
- Telifli tabir sitelerinin metnini ürüne ya da repoya koymak.

## Başarı ölçütü (beta, 25 kişi)

- Kullanıcı yardım almadan ilk rüyasını anlatıp dergisini okuyor.
- İkinci gerçek rüyasını başka bir sabah kaydetmeye dönüyor.
- En az bir dergiyi paylaşıyor ya da bir eşleşme modalını açıyor.
- Anlatımdan ilk yorum cümlesine kadar geçen süre birkaç saniye; dergi iki dakikanın altında.

Sayılar hedef önerisidir; ölçüm içeriksiz ürün olaylarıyla yapılır.

## Büyüklük varsayımları

| Evre | Kullanıcı | Rüya | Mimari etkisi |
| --- | --- | --- | --- |
| Beta | 25 | yüzler | Tek API süreci, içinde worker |
| Açık beta | binler | on binler | Worker ayrı süreç, webhook, CDN küçük resim |
| Büyüme | yüz binler | milyonlar | Doğrudan Postgres bağlantısı, gece kümeleme, okuma kopyası |

Şema ve API ilk günden üçüncü satıra göre tasarlanır; altyapı birinci satıra göre kurulur.
