# 0007: Rüya başına üç rıza kademesi

Tarih: 2026-11-13. Durum: kabul. İlgili: "özel rüyalar izinsiz eşleştirmeye açılmaz" ([hedefler](../hedefler.md)).

## Sorun

Kolektif motor, rüyaların birbirine bağlanmasını ister. Rüya metni ise sağlık, inanç ve özel hayat bilgisi taşıyabilir. Hangi rüya, neye, kimin izniyle girer?

## Seçenekler

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Kayıtta tek genel onay | En az sürtünme, en dolu kolektif | Açık rıza sayılmaz; kullanıcı neye izin verdiğini bilmez; tek kötü rüya için geri dönüş yok |
| İki kademe (özel, herkese açık) | Basit | Eşleşmek isteyen ama dergisini göstermek istemeyen kullanıcı dışarıda kalır; kolektif boş kalır |
| Rüya başına üç kademe (özel, kolektif, herkese açık) | Kullanıcı anonim katkı ile gösterimi ayırır; geri alınabilir; hukuken savunulur | Bir seçim daha; anlatması gerekir |
| Alan bazında ince ayar (semboller evet, metin hayır…) | En çok kontrol | Anlaşılmaz; arayüz ağırlaşır |

## Karar

Rüya başına üç kademe:

| Kademe | Kimler ne görür | Motora girişi |
| --- | --- | --- |
| `private` (varsayılan) | Yalnız sahibi | Yalnız kişinin kendi benzer rüyaları ve kişisel yorum bağlamı |
| `collective` | Kimse metni, başlığı, görseli görmez | Anonim toplamlar ve eşleşme oranı; kanıtta yalnız ortak sembol ve tema adları |
| `public` | Dergi herkese açık; ham anlatım yine yalnız sahibinde | `collective` ile aynı, ek olarak dergi kütüphanede ve eşleşmede gösterilebilir |

Hesap düzeyinde ayrı bir varsayılan tercih olabilir ama her rüya kendi kademesini taşır ve kademe sonradan değiştirilebilir.

## Gerekçe

- Kolektif katmanın dolması için "göstermeden katıl" seçeneği gerekir; çoğu kişi rüyasını yayımlamak istemez ama benzerini merak eder.
- Rüya başına seçim, kullanıcının tek bir hassas rüyayı dışarıda tutmasına izin verir.
- Açık, kapsamı belli ve geri alınabilir rıza KVKK ve GDPR'ın özel nitelikli veri şartlarına uyar.

## Kurallar

- Rıza `consents` defterine kapsam, metin sürümü ve zamanla yazılır; geri çekme de bir kayıttır.
- Kademe düşürülünce ilgili kenarlar, önbelleklenmiş eşleşmeler ve paylaşım aynı işlemde silinir.
- Kolektif toplam en az beş farklı kişinin rüyasından üretilir.
- Erişim kuralı veritabanı sorgusunun içindedir.
- Rıza metni değişirse eski rıza yeni kapsamı kapsamaz; yeniden sorulur.
- Araştırma ve açık veri seti bağışı bu kademelerden ayrıdır ve ayrıca sorulur.

## Yeniden değerlendirme tetikleyicileri

- Kullanıcıların büyük çoğunluğu seçimi hiç değiştirmiyorsa arayüzdeki yeri sadeleştirilir (kademeler kalır).
- Arkadaş ilişkisi gelirse "yalnız arkadaşlarım" kademesi eklenebilir.

## Geri dönüş yolu

Kademe bir sütun ve bir kayıt defteridir; yeni kademe eklemek ya da ikisini birleştirmek veri kaybı olmadan yapılır. Daraltmak her zaman mümkündür; genişletmek yeni rıza ister.
