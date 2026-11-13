# 0006: Beta mobil öncelikli web, mobil uygulama sonra Expo ile

Tarih: 2026-11-13. Durum: kabul. İlgili: 2026-10-24, Expo ön yüzünün silinmesi.

## Sorun

Ürün mobil öncelikli ama beta web'de yapılacak. Aynı backend iki istemciye hizmet etmeli; web'de yapılan iş mobilde çöpe gitmemeli.

## Seçenekler

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Web şimdi (React + Vite), mobil sonra Expo; ortak API istemcisi ve mantık | Beta hızlı; mobilde yerel animasyon ve bildirim; aynı dil | Arayüz iki kez yazılır |
| Baştan evrensel uygulama (Expo, web dahil) | Tek arayüz kodu | Mevcut web yeniden yazılır; web'de animasyon ve yerleşim kısıtları; iki ay önce bırakılmış yol |
| Web'i kabukla sarmak (Capacitor) | Mağazaya en hızlı çıkış; tek arayüz | Yerel his zayıf; ses kaydı ve arka plan davranışı sınırlı; dergi ve havuz animasyonlarında performans riski |
| Yalnız PWA | Mağaza süreci yok | iOS'ta bildirim ve arka plan kısıtlı; keşfedilebilirlik düşük |
| Flutter | Tek kod, iyi animasyon | Yeni dil; web ile hiçbir şey paylaşılmaz |

## Karar

Beta: mevcut web, telefon genişliğinde tasarlanır ve ana ekrana eklenebilir hâle getirilir. Mobil uygulama beta akışı doğrulandıktan sonra Expo ile yazılır; API istemcisi, tipler ve kayıt/taslak/oturum mantığı ortak pakete çıkar. Sözleşme kuralları: [istemci](../istemci.md).

## Gerekçe

- Betanın sorusu "insanlar ikinci rüyalarını kaydetmeye dönüyor mu"; bunu web cevaplar.
- Ürünün ayırt edici yüzeyleri (sayfa çeviren dergi, kütüphane havuzu, ses kaydı) telefonda yerel his ister; kabuk çözümü tam burada zayıf.
- Sunucu yapısal veri verdiği ve animasyon istemcide kaldığı için arayüzün iki kez yazılması sınırlı bir maliyettir; pahalı kısım (motor, üretim, sözleşme) paylaşılır.

## Şimdiden uyulan kurallar

- Ekranlar veriyi yalnız `api.ts` üzerinden alır.
- İş mantığı bileşenlerden ayrı dosyalarda durur.
- Kimlik Bearer jetonla; çereze dayanan hiçbir akış yok.
- Uzun işlerin yoklamayla okunabilen kalıcı karşılığı var; istemci açık bağlantıya güvenmez.
- Sunum kararları (animasyon, düzen) sunucu verisine sızmaz.

## Yeniden değerlendirme tetikleyicileri

- Beta kullanıcıları ağırlıkla telefonda ve PWA sürtünmesi geri dönüşü düşürüyorsa mobil uygulama öne alınır.
- Mağazada hızla bulunmak iş gereği olursa geçici olarak kabuk çözümü yayımlanabilir.

## Geri dönüş yolu

API sözleşmesi istemciden bağımsız olduğu için hangi mobil teknoloji seçilirse seçilsin backend değişmez. Ortak paket TypeScript'tir; Expo dışı bir seçimde yalnız o paketin karşılığı yeniden yazılır.
