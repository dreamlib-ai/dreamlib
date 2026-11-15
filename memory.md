# Memory

Cenker bir hatayı düzelttiğinde düzeltmenin kalıbı buraya tek satır yazılır: ne yanlıştı → bundan sonra nasıl. Aynı konu varsa yeni satır açma, mevcut satırı güncelle. En fazla 160 satır; dolarsa birleştir ve buda.

- Commit'e Claude co-author / "Generated with" satırı eklendi → commit ve PR yazarı yalnız Cenker, ek satır yok.
- Tasarımı belgelerdeki tasarımcıya bıraktım → tasarım da bizde; ekranı biz tasarlarız, kimseyi bekleme.
- Büyük harfli, harf aralıklı, soluk gri küçük etiketler (`@cenker · ÜCRETSİZ PLAN` gibi) kullandım → yok; küçük metin de normal yazım ve okunur renkte.
- Her karta ayrı renk verdim (sarı, mavi, pembe, turuncu…) → 60-30-10: %60 krem/beyaz zemin, %30 mor, %10 asit yeşili (ana aksiyon). Gece de aynı oran.
- Yüzen, ortası kabarık "modern" navbar yaptım → referanstaki gibi: alta oturan, konturlu, yuvarlak ikon butonları, aktif olan etiketli hap.
- Ekranlar kalabalıktı → referanslardaki sadelik: az eleman, büyük yazı, her şey rahat görünür; karakter ve tek ana aksiyon öne çıkar.
- Referans: `kaynak/referans/` (Pinterest "dreamlib type"); en net beğenilenler pin 01, 14, 20, 27, 29.
- 2026-10-17: Web tasarımı statik bulundu; Cenker Duolingo gibi belirgin bir iyileştirme istedi → Progress lila/gece kimliği ve seçilmiş koala korunur; sıcak açık zemin, Nunito, basılabilen tok kontroller, etkileşime tepki veren maskot, masaüstü sol / mobil alt gezinme. Yalnız yavaş yüzdürme animasyonu canlılık için yeterli değil.
- 2026-10-24: Yeni web arayüzünde marka noktası, header aşamaları, süre/giriş etiketleri ve eylem/kısayol alt yazıları reddedildi → Toolpool `no-ai-slop.md` her yeni web işinde uygulanır; geri sol üstte yalnız erişilebilir chevron, başlangıçta başlık ve tek cümle.
- 2026-10-25: Eski Nunito/lila yönü güncel sanıldı → `dreamlib-vibe` çalışmasındaki Unbounded fontunu, kobalt paletini ve `Işıklı bulut / kuru pastel` + `Eldeki gece` koala temalarını web arayüzüne taşı.

- 2026-10-25: Koalayı çerçeveli kartta sallandırmak yerine kuru pastel çizgisini ve kâğıt dokusunu bütün arayüze taşı; Unbounded/kobalt/asit yeşilini koru. Yeni sahneler aynı referanslarla imagegen üzerinden üretilebilir. Hazır olmayan özellik ve dolgu metin gösterme; Toolpool No AI Slop ve Cenker pattern’ini uygula.

- 2026-10-25: Pastel ana ekran onaylandı; gizlilik aynı estetikte olmalı. Şimdilik yalnız Google ile kayıt/giriş; elle e-posta formu ve ayrı kayıt düğmesi yok. E-posta girişi daha sonra.

- 2026-10-25: Aynı koalayı sürekli aynı tarafta ve obje tutarken tekrarlama; ilk kuru pastel referansını koruyarak boş patili merak, esneme ve uyku pozları üret, metin boşluğuna göre sağ/sol yerleşimi değiştir.

- 2026-10-25: Onboarding v1 doku/renk onaylı; içerdeki açık dashboard kullanışsız bulundu. Onboarding onayını iç ekran onayı sayma; aynı gece dokusunu içeride sürdür, ilk ekranı doğrudan yazma eylemine aç ve boş sayaç/tekrarlanan karşılama kartlarını kaldır.

- 2026-10-26: Uygulama içine büyük arka plan koalası ve masaüstü formu taşıyan iki düzen reddedildi → `Desktop/dreamlib-vibe/app-vibe` pin-01/27/28 üzerinden telefon öncelikli gerçek uygulama düzeni kur; mevcut font/palet korunur, okunur yüzey ve küçük maskot kullan, keşfet/anlat/kütüphane ayrı ve işlevli olsun.

- 2026-10-29: Kartları ve kontrolleri yerleştirmek tek başına modernlik sağlamadı; Cenker sade/modern/estetik yön için Apple, Tiimo ve Faladdin’i birlikte incelemeyi istedi. Dreamlib’de sakin yazı yüzeyi, içerik/kontrol ayrımı ve rüya atmosferi üzerinden ilerle; boş durumlarda arama/filtre ve tekrarlanan eylem gösterme.

- 2026-11-02: Yalnız kozmetik sadeleştirme ürünü zayıf bıraktı → anket sonucunu gerçek veriden oku: Kobalta/Pastel; aynı koalanın işlevli varyantlarını giriş/kayıt/boş durumda kullan. Unbounded ve kumlu doku korunur. Ses kaydı ana eylem, yazı ikincil; ses dosyası yükleme ve “Tabir et” gönder düğmesi yok. Tek görev, tutarlı tema ve hata/iptal/yeniden deneme durumları birlikte tasarlanır.

- 2026-11-02: Lacivert zeminli koala görselini oval CSS maskesiyle iç ekranlara koymak koyu leke/gölge bıraktı → bağımsız maskotlarda gerçek alfa kanallı kesit kullan; sahne görselleri yalnız tam ekran onboarding için.

- 2026-11-15: Beyin sekmesi eklenince telefondaki alt menü iki sütunda kaldı, Beyin alta taştı; Anlat ekranı tek düğmeyle boş ve kullanışsız bulundu → gezinme tek dosyada (artık `calm.css`, üstte cam şerit); ekran ya da sekme değişince telefon boyutunda ekran görüntüsüyle bak. Telefonda alt menü kenara oturan üç eşit sekme, açık olanın ikonu sarı hapta; Anlat'ta kayıt düğmesinin etiketi, gerçek "Yazarak anlat" düğmesi ve son rüyalar.

- 2026-11-15: Tasarım "berbat" bulundu: gövdede de geniş başlık fontu (Unbounded), iki farklı koala, slayt gibi tanıtım, arka planlı koala sahneleri → sakin gece yönü (`docs/tasarim.md`): karakterli başlık fontu + sade metin fontu, tek pastel koala ve arka plansız poz seti, üstte liquid glass menü, lav lambası mikrofon, Duolingo gibi adımlar. Koalayı arka planlı koyma; font önerirken karakterli seçenekleri görsel örnekle göster.

- 2026-11-15: Sakin gece ilk turu da "AI slop" bulundu: düz renkler yapay, yükleme çubuğu, çerçeveli kartlar, logo; "daha tatlı" istendi → gradyanlı canlı zemin (three.js lav), bulut görselli düğmeler, çerçevesiz baloncuklar, bulutlu ilerleme, tokonomy gibi açılış. Düz zemin ve ince çerçeveli kart dilini varsayılan yapma.

- 2026-11-15: Tasarım yönü için Cenker'in Pinterest'ine (Chrome'da oturumu açık) bak: grenli kobalt/mor sprey, oluklu cam, risograf, liquid glass. Menüde yazı kalabalığı istemiyor; ikon yeter. Görsel üstündeki yazıya mutlaka koyu tül koy.
