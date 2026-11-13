# 0003: İlişkiler Postgres'te tipli kenar tablosuyla tutulur

Tarih: 2026-11-13. Durum: kabul.

## Sorun

Rüyalar, semboller, temalar ve kişiler arasında ilişkiler kurulacak; yeni ilişki türleri sonradan eklenebilmeli ve zincirler (rüya → sembol → rüya → tema) sorgulanabilmeli. Bunun için ayrı bir graf veritabanı gerekir mi?

## Seçenekler

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Postgres: `relation_types` kaydı + tek `edges` tablosu | Mevcut veritabanı; rüya, rıza ve kenar aynı işlemde; erişim kuralı aynı sorguda; yeni servis yok | Derin zincirlerde recursive CTE yavaşlar; graf algoritmaları elle yazılır |
| İlişki başına ayrı tablo | Tipli ve dar tablolar | Her yeni ilişki türü migration; "eklenebilir zincir" hedefine aykırı |
| Neo4j gibi graf veritabanı | Zincir sorguları ve graf algoritmaları hazır | İkinci veritabanı; iki yerde tutarlılık; rıza silme iki sistemde; barındırma maliyeti |
| Postgres üstünde graf eklentisi | Aynı veritabanında graf sorgu dili | Barındırıcıda bulunmayabilir; taşınabilirlik düşer |

## Karar

Tek `edges` tablosu ve `relation_types` kaydı. Yeni ilişki türü bir kayıt satırı ve kodda bir puanlayıcıdır; şema değişmez. Ayrıntı: [motor](../motor.md).

## Gerekçe

- Beta ve açık beta ölçeğinde kenar sayısı milyonun altında; indeksli bir tablo yeter.
- Ürünün sorduğu sorular sığ: bir rüyanın komşuları, iki kişinin ortakları, bir sembolün birlikte görüldükleri. Derinlik üçü geçmez.
- Rıza geri çekildiğinde kenarların aynı işlemde silinmesi gizlilik için şart; iki sistemde bu güvence zayıflar.
- Kanıt (`evidence`) ve sürüm (`algo_version`) alanları her kenarı açıklanabilir ve yeniden hesaplanabilir kılar.

## Kurallar

- Kenar yazan tek yer puanlayıcılardır; elle kenar yazılmaz (`series` hariç, kullanıcı bağı).
- Her kenar hangi sürümle üretildiğini taşır; sürüm değişince eski kenarlar süpürülür.
- Zincir sorguları SQL fonksiyonudur ve derinlik sınırı taşır.
- Erişim kuralı (özel, kolektif, herkese açık) sorgunun içindedir; uygulama katmanına bırakılmaz.

## Yeniden değerlendirme tetikleyicileri

- On milyonlarca kenar ve indeksle çözülemeyen yavaşlık.
- Ürün, derin yol ya da topluluk bulma gibi graf algoritmalarını çevrimiçi istemeye başlarsa.

## Geri dönüş yolu

`edges` tablosu düz ve tipli olduğu için bir graf sistemine toplu aktarılabilir. Graf sistemi gelirse yalnız analitik okuma için eklenir; doğruluk kaynağı Postgres kalır.
