# Riskler ve önlemler

Sıra etkiye göre. Her riskin bir sahibi iş vardır ([görevler](gorevler.md)); önlem alınmadan ilgili özellik açılmaz.

## Gizlilik ve rıza

| Risk | Sonuç | Önlem |
| --- | --- | --- |
| Rüya metni sağlık, inanç, cinsellik gibi özel nitelikli bilgi taşır | KVKK/GDPR ihlali, güven kaybı | Rüya başına açık rıza, rıza defteri, varsayılan özel ([0007](kararlar/0007-riza-kademeleri.md)) |
| Kolektif toplamdan kişi tanınır | Küçük grupta kimlik ifşası | En az beş kişi kuralı; betada toplam cümleleri çoğunlukla kapalı kalır |
| Benzerlik kanıtı başkasının metnini sızdırır | Rıza dışı gösterim | Kanıt yalnız ortak sembol ve tema adlarını taşır; metin yalnız iki taraf da paylaştıysa |
| Anlatımda üçüncü kişilerin adı geçer | Rızası olmayan kişinin verisi | Paylaşılan dergide ham anlatım yok; altyazılar storyboard'dan gelir, moderasyonda ad kontrolü |
| LLM sağlayıcısı girdiyi saklar | Veri üçüncü tarafta kalır | Yalnız veri saklamayan sağlayıcılar ([LLM](llm.md)); gizlilik metninde açıkça yazılır |
| Rıza geri çekildi ama kenar kaldı | Silinmesi gereken veri yaşıyor | Kademe düşürme ve kenar silme aynı işlemde; testle doğrulanır |
| Logda rüya metni | Sızıntı | Mevcut kural korunur: doğrulama hatası ve ürün olayı içerik taşımaz |

## Hassas içerik

- Kâbus, travma ve kendine zarar anlatımları gelecek. Yorum bugün yumuşatıyor; yazılı bir politika yok.
- Politika betadan önce yazılır: hangi sinyalde yorum nasıl değişir, hangi durumda yardım kaynağı gösterilir, neyin paylaşıma çıkamayacağı.
- Model teşhis koymaz, risk puanı göstermez. Davranış eval setiyle denetlenir.
- Reşit olmayan kullanıcı: yaş beyanı ve paylaşım kısıtı kararı açık; herkese açık kütüphaneden önce verilmeli.

## Hukuk ve lisans

| Risk | Önlem |
| --- | --- |
| Telifli tabir metni ürüne ya da repoya girer | Lisans kademeleri; dışa aktarım yalnız A kademesinden ([0008](kararlar/0008-korpus-lisans-kademeleri.md)) |
| NC lisanslı anlatıdan türev ürüne sızar | Çevrimdışı çalışmadan yalnız ağırlık ve eşik sayıları taşınır; izin yazıları |
| Toplayıcı kodu sitelerin kurallarını çiğner | Mevcut kural: robots.txt ve 401/403/451'de dur; engel aşılmaz |
| AGPL ile bağımlılık lisansı uyuşmazlığı | Yeni bağımlılık eklenirken lisans kontrolü |
| Katkıcı, telifli ikon ya da metin gönderir | Katkı rehberinde kaynak beyanı; ikonlar için açık lisans şartı |
| Üretilen görselde gerçek kişi ya da marka | İstemde yasak; şikâyet ve kaldırma süreci |

## Maliyet

- Görsel, metnin katları kadar pahalı; video daha da fazla. Genel harcama freni bilinçli olarak ertelendi; `usage` defteri frenden önce gelir ki neyin frenleneceği bilinsin.
- Kötüye kullanım: anonim oturumlar günlük hakla sınırlı (mevcut). Açık betadan önce genel fren şart.
- Yeniden deneme maliyeti: saklı istek adresleri sayesinde çizilen panel yeniden ödenmez (mevcut); yeni iş türleri aynı kuralı izlemeli.
- Embedding ve çıkarım her rüyada koşar; ucuz görev modelleri bu yüzden ayrı seçilir.

## Soğuk başlangıç

25 kişiyle kolektif katman seyrek kalır.

- Eşleşme iki kişi arasında hesaplandığı için küçük grupta da çalışır; beta kullanıcıları birbirini tanıyan bir grup olursa en değerli özellik bu olur.
- Kolektif toplam cümleleri çoğunlukla görünmez; yerini sözlük ve kişisel bağlam doldurur. Boşluk uydurma veriyle kapatılmaz.
- Herkese açık akış betada açılmaz; linkle paylaşım yeterlidir.
- Benzerlik oranları ilk haftalarda oynar; sürüm numarası ve "beta" ibaresi bunu dürüstçe gösterir.

## Kalite

| Risk | Önlem |
| --- | --- |
| Model sembol uydurur ya da bağ zorlar | Alıntı zorunluluğu, getirilen bağlama sadakat kuralı, eval |
| Aynı sembol onlarca düğüme dağılır | Alias tablosu, embedding ile bağlama, birleştirme önerileri |
| Oran yüksek ama rüyalar alakasız | Bileşik puan, altın çiftler, kullanıcıdan "doğru mu" geri bildirimi |
| İkon üslubu kayar | Tek şablon ve referans; elle onay |
| Model ya da prompt değişince davranış bozulur | Sürümlü `analyses`, eval sonuç tablosu olmadan değişiklik yok |

## Operasyon

- Tek geliştirici: yayın elle, CI yalnız kontrol. Yayın adımları yazılı; geri dönüş bir önceki sürümü yeniden yayınlamaktır.
- Tek bölge, tek API kopyası: betada kabul edilir; kuyruk kalıcı olduğu için süreç ölümü iş kaybettirmez.
- Sağlayıcı kesintisi: yedek model dizisi (LLM); fal kesintisinde iş kuyrukta bekler, kullanıcıya süre söylenir.
- Yedek: veritabanı yedeği ve Storage silme politikası betadan önce doğrulanır.

## Açık kaynak

| Risk | Önlem |
| --- | --- |
| Geçmişte sır | Temiz geçmişli yeni repo, tarama, anahtar döndürme ([0005](kararlar/0005-acik-kaynak-modeli.md)) |
| Açık koddan saldırı yüzeyi | Güvenlik bildirimi adresi; sır ve iç adres repoda yok; RLS ve sahip süzmesi koda değil veritabanına da dayanır |
| Katkı incelemesi zaman yer | Küçük ve net işler, şablonlar, CI; haftada belirli inceleme zamanı |
| Proje klonlanıp kapalı servis yapılır | AGPL |
| Topluluk gelmez | Kod dışı katkı şeritleri, düzenli küçük commit, görünür yol haritası |

## Karar bekleyenler

- Hassas içerik politikası ve reşit olmayan kullanıcı yaklaşımı.
- Genel harcama freninin zamanı.
- Herkese açık kütüphanede takma ad mı gerçek kullanıcı adı mı.
- Rüya bağışı formunun kapsamı.
