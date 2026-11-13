# Tasarım

- Kaynak: `kaynak/prototip/1. Dreamlib -1.dc.html` (tıklanabilir prototip; okunur, git'e girmez). Ekran ve akış fikirleri oradan: onboarding (giriş, gizlilik, hatırlatma), Anlat (ses/yazı) → metin onayı → analiz → stil ve panel sayısı → manga kitapçığı → kütüphane (kitapçıklar, metinler, takvim, tekrar eden semboller); Keşfet, Profil, seri ve rozetler.
- Prototip yön gösterir, birebir kopyalanmaz; sadeleştir. Tasarımı biz yapıyoruz.
- **Web tasarım yönü (2026-10-25):** Unbounded, kobalt/gece laciverti, açık yüzey ve asit yeşili korunur. Kuru pastel koala ve gerçek kâğıt dokusu girişin tamamını kaplar; görseller çerçeveye alınmaz ve sallandırılmaz. Giriş ve gizlilik iki adımdır; hazır olmayan özellikler gösterilmez. Ana ekran, Anlat ve kütüphane aynı dili kullanır. Ağır gölge, kabartma, dekoratif ikon ve tekrar eden açıklama yok. Uygulama içi yapı 26 Ekim’de app-vibe referanslarıyla yenilendi: Keşfet/Anlat/Kütüphane, küçük pastel koala, açık okunur çalışma yüzeyleri, kobalt/gece/asit yeşili palet.
- Yeni görseller built-in imagegen ile iki mevcut koala referansından üretildi: `frontend/src/assets/koala-cloud-wide.png` (giriş ve ana ekran), `koala-night-pastel.png` (önceki gece pozu, arşiv). Orijinaller korunur. Üretim ana istemi: aynı koala anatomisi ve ince kuru pastel tüy çizgileri, kobalt lacivert dokulu kâğıt, bal rengi yerel ışık; geniş sahnede sağda ışıklı bulut tutan koala ve solda metin boşluğu; portrede ayı gösteren altın kenarlı küçük gece penceresi. Yazı, çerçeve, fazladan şekil, plastik/3D görünüm yok. Referans rolleri: Işıklı bulut çizim dili ve doku, Eldeki gece poz ve elde tutulan obje.
- **Eski web yönü (2026-10-17):** Nunito ve Progress lila/gece kimliğiyle canlı, dokunsal bir arayüz. Bu renk ve font yönü 25 Ekim’de kobalt/Unbounded tasarımıyla değişti. Masaüstü sol gezinme, mobil sabit alt gezinme, haftalık gerçek kayıtlar ve hareket azaltma desteği geçerli kaldı. Kayan slogan bandı ve sahte istatistik yok.
- Renk, yazı, boşluk ve köşe değerleri `frontend/src/theme.css` içinde token olarak durur; değişim tek dosyadan olur. Bileşen stilleri `frontend/src/app.css`. **Maskot (2026-10-16, kesinleşti):** eski Perest bırakıldı. Yeni maskot beyaz koala: kalın-ince değişen siyah kontur, katmanlı tüy, soğuk lila hücre gölgeleri, pembe iç kulak, parlak göz ve burun, göz kırpıyor ve dili çıkık, alnında tüy kıvrımı, kalın beyaz çıkartma kenarı. Koyu zemin `#2C2838` (paneli aynı), yazı Bagel Fat One, harfleri zıplayan ve çerçevesiz, koalanın pençeleri yazının uzun harflerine ("d", "b") sarılır. Logo (koala + yazı) tek görsel: `frontend/src/assets/lockup.png`, favicon `frontend/public/favicon.png`, profil resmi `brand/`. Çıkartma yazısına dış çerçeve, ay ve yıldız eklenmez (Cenker reddetti). Yeni poz gerekirse fal ile referanslı üretilir (Go `explore` aracı 24 Ekim 2026'da Python geçişinde silindi; istemleri git geçmişinde, `backend/cmd/explore/refs.go`, set 9 ve 10 bu karakterin istemleri; referans görselleri `kaynak/referans/` altında git dışı), zemin `scripts/cutout.ps1` ile kesilir. Üretim sonrası ince kenar çizgisi gibi kalıntıları kontrol et; model "görünmez kenar" dese bile çiziyor.
- Prototip dosyasındaki eski varsayılanlar (Indigo, Olive, Nunito) artık geçerli değil.
- Arayüz Türkçe; metinler tek dosyada toplanır (ileride İngilizce gelecek). Kod, değişken ve dosya adları İngilizce.

- Önceki gizlilik varyantı: girişte tek Google ile devam et eylemi; elle e-posta formu ve ayrı giriş/kayıt ekranı yok. Gizlilik adımı aynı geniş pastel kompozisyonu kullanır. Gizlilik görseli `frontend/src/assets/koala-night-wide.png`, built-in imagegen ile onaylı geniş bulut sahnesi (kompozisyon/doku) ve Eldeki gece (poz/obje) referanslarından üretildi. İstem: sağda tam boy oturan, ayı gösteren pirinç kenarlı küçük gece penceresini tutan aynı koala; solda metin için boş koyu kobalt kâğıt, ince kuru pastel tüy ve sıcak krem ışık; çerçeve/yazı/fazladan obje yok.

## Yeni pozlar

Onaylanan ana giriş kompozisyonu korunur. Gizlilikte meraklı koala solda, seçimler sağda; Anlat boş durumunda gerinen koala; kütüphanenin boş durumunda solda uyuyan koala kullanılır. Sallanma animasyonu yok, eller boştur.

Üç görsel built-in imagegen ile üretildi. Referanslar `koala-glow-cloud.png` (kimlik ve kuru pastel çizgi) ve `koala-cloud-wide.png` (lacivert kâğıt ve kompozisyon). Proje dosyaları `frontend/src/assets/` içindedir.

- `koala-curious-left.png`: yatay sahne, solda oturup sağa doğru merakla eğilen koala; bir boş pati yanağa, diğeri dize dayanır; sağ yarı metin için boş kâğıt.
- `koala-stretch.png`: dikey sahne, uykudan kalkıp bir kolunu yukarı uzatan, esneyen koala; diğer kol aşağıda, doğal anatomi, tam boy görünür.
- `koala-sleep-left.png`: yatay sahne, solda ön koluna yaslanıp kıvrılarak uyuyan koala; sağ yarı boş kâğıt.

Ortak istem: exact first reference koala identity, huge feathered ears, delicate hand-drawn dry pastel fur, warm cream-gray fur and honey rimlight, charcoal nose, continuous cobalt navy chalk paper. Both paws empty; no held objects, props, stars, text, borders, plastic/3D finish or vector outlines. Her sahnenin hareketi ve metin boşluğu ayrıca yukarıdaki biçimde belirtilir.

## Uygulama içi yapı (26 Ekim)

Referanslar yerel `dreamlib-vibe/app-vibe/` (git dışı): pin-01 (net bölümler ve alt gezinme), pin-27 (kompakt kartlar ve okuma sırası), pin-28 (görsel arşiv). Telefon öncelikli düzen; masaüstünde içerik genişliği sınırlıdır. Font Unbounded, renkler mevcut kobalt/gece/açık yüzey/asit yeşili. Onboarding v1 korunur. Koyu dokuyu bütün sayfaya büyütüp yazının arkasına koala koyma yaklaşımı reddedildi.

- `Explore.tsx`: giriş kartı, gerçek hesap günlüğü, altı başlıklı rüya atlası ve yerel dialog. Atlas sabit düşünme sorularıdır; sosyal kullanıcı akışı veya kesin tabir değildir. Sosyal feed backend’de yok.
- `Tell.tsx`: tek kolon yazı alanı, yorum seçimi, görünürlük bilgisi ve ana eylem. `VoiceInput.tsx` mikrofon kaydını veya ses dosyasını mevcut transkripsiyon API’sine verir; bölümden çıkınca kayıt durur. Görsel koala yazının arkasına gelmez.
- Sonuç ayrı okuma sayfasıdır; nesneler, duygular ve çizim ayarları açılır detaylardır. Kitapçık ilerleme ve paneller aynı akışta kalır.
- `Library.tsx`: metin/etiket araması, kitapçık/yazı filtreleri, iki sütun mobil kapaklar, metin kayıtlarında kendi rüya alıntısı; boş durumda küçük koala. Özgün metin detaydan açılır.
- `workspace.css` uygulama içini kapsar; onboarding CSS’si değişmez. React bileşeni gezinmede tutulduğu için rüya taslağı sekmeler arasında kaybolmaz.

Yeni asset `frontend/src/assets/koala-app.webp` (yaklaşık 617 KB). Built-in imagegen, `koala-glow-cloud.png` kimlik ve kuru pastel stili referansıyla üretildi; alfa korunarak WebP kodlandı. Son istem: full body seated Dreamlib koala, huge feathered ears, warm cream-grey dry pastel fur, honey rimlight, dark oval nose, one empty paw under chin and one on knee, compact silhouette, transparent background, no props/text/frame/floor, no vector or 3D finish. Ham üretim Codex generated_images alanında kalır; uygulama kendi asset’ini kullanır.

## Sakin rüya günlüğü (29 Ekim)

Cenker uygulamayı hâlâ yavan buldu; sade/modern/estetik yön için Apple, Tiimo ve Faladdin’in incelenmesini istedi. [Apple Materials](https://developer.apple.com/design/human-interface-guidelines/materials) içerik ve kontrol katmanlarını ayırma; [Tiimo](https://www.tiimoapp.com/) yumuşak yüzey ve sade planlama; [Faladdin mağaza görselleri](https://play.google.com/store/apps/details?id=com.faladdin.app&hl=tr) gece atmosferi için kaynak alındı. Bunlar Dreamlib’e uyarlanan tasarım çıkarımlarıdır; üçüncü taraf görselleri ürüne alınmadı.

- `editorial.css`: uygulama içi sakin yüzeyler, belirgin başlıklar, azaltılmış konturlar, yalnız gezinmede hafif geçirgenlik; Unbounded/kobalt/gece/asit yeşili korunur. Onboarding ve mevcut kaydedilmemiş giriş/CSS işleri bu katmandan ayrıdır.
- Keşfet’te yalnız rüya anlatma eylemi ve atlas öne çıkar; günlük özeti gerçek kayıt varsa görünür. Atlasın soruları ayrıntıda kalır.
- Anlat’ta tekrarlanan başlık kartı kaldırıldı, tek okunur yazı yüzeyi ve yerel yorum seçimi kullanılır. Koala başlığın yanında kalır, metnin arkasında değildir.
- Kütüphanede kayıt yokken arama/filtre/yeni rüya ikonu gösterilmez; ilk kayıt ana eylemdir. Kayıt varsa arama/filtreler görünür ve detaydan dönünce seçim korunur.
- Görsel inceleme 320/390 px ve masaüstünde, gerçek bileşenlerin ayrı SSR önizlemesiyle yapıldı. Bu önizleme hesap/giriş kanıtı değildir; gerçek oturum kapalıydı. Otomatik test çalıştırılmadı, TypeScript/build başarılı.

## Anket teması ve ses önceliği (2 Kasım)

1 Kasım'daki kart/koala ağırlığı ve ardından sistem fontlu, görselsiz koyu düzen reddedildi. Yeni yön kişisel tahmine değil, Supabase `preference_survey_summary()` salt-okunur sonucuna dayanır: 34 tamamlanmış anket; Kobalta 9 renk seçimi, Pastel 7 birincilik ve 16 ilk-dört seçimi. Bunlar anonim ön tercihtir, bilimsel genelleme değildir.

- Renk kaynağı tercih anketinin kazanan paleti (anket kapandı, sonuçlar veritabanında): Kobalta `#2457C5 / #F3C84B / #F6F1E6`. Ana yüzey, mavi ailesinin gece tonu `#102343`; sarı yalnız ana eylem ve seçili durumlarda, krem metinlerde. Unbounded değişmez, dört ağırlık Latin/Türkçe alt kümeli WOFF2 ve OFL lisansıyla yerelden sunulur. Gren ve yavaş ışık bütün akışta devam eder.
- Kazanan Pastel karakteri: `koala-cloud-wide` giriş/işleme, `koala-curious-left` gizlilik/kayıt, `koala-sleep-left` boş kütüphane. Kaynak PNG'ler korunur, uygulama kalite 90 WebP sürümlerini kullanır; dört sahne toplam yaklaşık 1,3 MB. Koala metnin arkasına ve kart kutusuna sokulmaz; pozlar kendi işlevlerinde kullanılır.
- Giriş tek Google eylemidir; hazır olmayan Apple kontrolü görünmez. Gizlilik ayrı görevdir. Ana uygulama Anlat ve Kütüphane'den oluşur; boş Keşfet/atlas kaldırıldı. İlk ekran kayıt odaklıdır; yazmak ikincildir. Metin taslağı sekme değişiminde korunur, açıkça yeni rüya başlatıldığında yeni kayıt açılır.
- Anlat: büyük mikrofon, kayıt sırasında süre/bitir/iptal; sonra düzenlenebilir transkript ve yalnız ikonlu gönderim. Dosya yükleme, tabir türü seçimi ve görünürlük metni yoktur. Analiz kullanıcı göndermeden başlamaz; backend varsayılan evrensel yorum ve hesap görünürlüğü korunur.
- [Libraries.dev Voice](https://libraries.dev/voice) MIT `voice-glow` 0.3.0 `VoiceBeam` aynı MediaStream'i dinler; ikinci mikrofon açmaz. Kayıt istemi yalnız kullanıcı eylemiyle başlar. 2 dakika/8 MB sınırı, izin reddi, cihaz kaybı, sekme/görünürlük değişiminde iptal; ağ hatasında aynı Blob'dan yeniden deneme ve transkripsiyonda 60 saniye timeout/AbortController vardır. Azaltılmış harekette efekt durur.
- Mobil cam gezinme iki sekme ve kayan seçim yüzeyi kullanır. Güvenli alt boşluk, küçük telefon için kısa sahne, portre tablet için yığılmış onboarding, klavye/focus ve azaltılmış sayfa hareketi desteklenir. Sonuç açık okuma alanıdır; kütüphane arama/filtreyi yalnız kayıt varken gösterir.

`tests/recorder.test.mjs` izin/iptal/format/boyut/süre/cihaz durumlarını sınar. `tests/ui.html` yalnız geliştirmede gerçek Workspace/Onboarding bileşenlerini sentetik MediaStream ve yerel API yanıtlarıyla açar; mikrofon izni istemez, ücretli sağlayıcıya gitmez, production build'e girmez. `?retry`, `?denied`, `?slow`, `?populated`, `?onboarding`, `?privacy` durumları vardır. Tarayıcıda kayıt → hata → aynı kayıttan yeniden deneme → metni düzenleme → gönderim → kayıt → kütüphane ve yeni rüya akışı doğrulandı. Bu, gerçek hesap/sağlayıcı ve fiziksel mikrofon doğrulaması değildir. Canlıya yayın yapılmadı.

Temiz `b4e5dbe` checkout üzerinde `npm run check`: 30 backend + 18 frontend testi ve TypeScript/Vite build başarılı. Önceden var olan Apple/auth/CSS değişiklikleri commit dışında korundu; bu yüzden çalışma klasörünün 20 frontend testiyle sayı farkı vardır. 320 × 568, 390 × 844, 768 × 1024 ve 1280 × 900 yerleşimleri gerçek bileşenlerle incelendi; test fixture Türkçe metni de kontrol edildi. Üretim paketi yalnız uygulama girişini, WebP sahnelerini ve yaklaşık 156 KB yerel WOFF2 fontlarını içerir; test/örnek veri girişleri yayın paketinde yoktur.
