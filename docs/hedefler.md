# Dreamlib ürün hedefi

2 Kasım 2026: kullanıcı aşağıdaki kapsamı sırayla uygulama yetkisi verdi. Genel maliyet freni ertelendi; CI/CD kurulmaz. REM, iki kişinin profili üzerinden hesaplanan açıklanabilir bir MVP algoritmasıdır. Kişi başına tek bir bilimsel/uyku ölçümü değildir. Özel rüyalar izinsiz eşleştirmeye açılmaz.

## Kabul ve uygulama sırası

| İş | Kabul ölçütü | Durum |
| --- | --- | --- |
| Ürün onboarding’i | Anket estetiği, kısa sahneler, REM kökeni ve ürün anlamı, geç/geri/tekrar, erişilebilir mobil akış | Uygulandı; 320/390 px ve masaüstü kontrol edildi |
| Canlı koala ve atmosfer | Dokunma tepkisi, sahne hareketi, karakterin durumuna uygun hareket; azaltılmış hareket desteği | İlk CSS hareketleri uygulandı; karakter içi animasyon geliştirmesi açık |
| Ses akışı | İzin reddi, kesinti, arka plan, taslak/iş kurtarma gerçek telefon kabulü | Çekirdek mevcut; kapsamlı fiziksel cihaz testi açık |
| Tarih ve düzenleme | Rüya tarihi/kayıt tarihi ayrı; aynı kimlik; eski analiz/çizim durumunun belirtilmesi | Yayında; revizyon, sahiplik, gerçek DB ve mobil UI doğrulandı |
| Sonradan ayrıntı | Zamanlı ses/metin ekleme; ilk anlatım korunur; isteğe bağlı yeniden analiz | Yayında; sentetik ses UI ve gerçek DB/model yenileme geçti |
| Kişisel düşünce | Kullanıcının notu anlatım ve model yorumundan ayrı | Yayında; yorum girdisinden dışlandığı test edildi |
| Tür/tema | Sistem belirler; çoklu etiket; kullanıcı düzeltmesi; başta seçim yok | Yayında; model ve kullanıcı düzeltmesi ayrı saklanır |
| Duygu/deneyim | Tahmin ve kullanıcı beyanı ayrı; lucid/tekrar iddiası uydurulmaz | MVP yayında; açık alıntı denetimi ve 4 gerçek model örneği geçti |
| Kütüphane | Favori, tarih aralığı, tür/duygu/tema arama ve filtreleri birlikte çalışır | Favori/tarih/tür/duygu/tema/arama birlikte çalışır; mevcut liste sınırı 200 |
| Hazır avatar | Seçim hesapta; sonraki çizimlere kalıcı referans | Açık |
| Avatar tasarımı | Yüz/saç/ten/kıyafet/aksesuar; sahneler arasında tutarlılık | Açık |
| Bakış açısı | Birinci kişi, dışarıdan kendini görme, gözlemci; anlatımdan öneri | Açık |
| Analiz kalitesi | Somut olaylara bağ; kişisel geçmiş; geri bildirim ve değerlendirme | Temel mevcut; geliştirme açık |
| Kişisel anlamlar | Kişi/mekân açıklamalarını izinle kullan; düzenle/sil | Açık |
| Görsel kontrolü | Avatar/stil/bakış tutarlılığı; tek panel yenileme ve ayrıntı düzeltme | API temeli var; UI açık |
| Kitapçık | Okuma, kapak, indirme, seçerek paylaşım; tek rüya kaydı | Üretim/kayıt var; çıktı ve okuma açık |
| Rüya serileri | Kullanıcının bağı ile algoritmanın önerisi ayrı | Açık |
| Zamansal değişim | Gerçek kayıtlara dayalı duygu/tema değişimi; az veride temkin | Açık |
| Haftalık özet | Tarih aralığı, kaynak rüyalara bağlantı; veri yoksa rapor yok | Açık |
| İstatistikler | Tür/duygu/kişi/mekân/tekrar/hatırlama/kayıt sıklığı; sayım yöntemi belli | Açık |
| REM algoritması | Tema/olay/duygu/kişi/mekân benzerliği, gerekçeler, örnek çiftlerle kalite ölçümü | Açık |
| Kişisel REM bağları | Kendi kayıtları arasındaki örüntüler ve zamansal değişim | Yalnız tekrar eden etiket temeli var |
| İki kişi arasında REM | Profilde hesaplama; karşılıklı izinli/seçilmiş veri; örnek sayısı ve sürüm | Açık |
| Sosyal keşif | Paylaşılmış kitapçıklar, beğeni/kaydet/emoji, engelle/şikâyet/paylaşımı geri al | Açık |
| Aylık kitap | Rüya seçimi, tek kapak, okunabilir indirme | Açık |
| Bilgi/hatırlatma | Kaynaklı içerik ve okuma listesi; isteğe bağlı sabah bildirimi | Açık |
| Gizlilik/hesap | Veriyi indir/sil; kişisel anlam/avatar/sosyal izinlerini kapsa | Açık |

## Doğrulama

Her paket kendi veri/API/UI sınırlarıyla doğrulanır. Model testi, fiziksel telefon testi ve sentetik tarayıcı testi ayrı belirtilir. Hazır olmayan bir özellik onboarding’de `Geliştiriyoruz` olarak görünür; özellik bitince bu durum güncellenir. İlk onboarding tanıtımı otomatik zamanlayıcıyla atlamaz; klavye, dokunma kaydırması ve düğmelerle ilerler.
