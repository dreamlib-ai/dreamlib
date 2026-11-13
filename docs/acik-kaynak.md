# Açık kaynak planı

Dreamlib'in motoru, sözlüğü, ikonları ve ölçüm setleri açık olacak; kullanıcı rüyaları hiçbir zaman. Karar: [0005](kararlar/0005-acik-kaynak-modeli.md). Lisans AGPL-3.0.

## Neden açık

- Rüya herkesin gördüğü ama kimsenin ortak bir yerde tutmadığı bir şey. Açık bir sembol sözlüğü ve ikon kütüphanesi tek bir ürünün ötesinde işe yarar.
- "Rüyanla ne yapıyorsunuz" sorusunun en dürüst cevabı kodun kendisidir.
- Kültürlere özgü tabir bilgisi tek kişiyle toplanamaz; topluluk işidir.

## Çıkış adımları

1. Sır temizliği: izlenmeyen klasörlerdeki parola ve env dosyaları dışarı, ilgili anahtar ve parolalar döndürülür.
2. Geçmiş taraması yapılır; sonuç ne olursa olsun public repo temiz ağaçtan tek ilk commit ile açılır. Eski özel repo arşiv kalır.
3. Ağaçtan çıkarılanlar: yayın notlarındaki proje kimlikleri ve iç adresler, anket yönetim bilgisi, tasarım keşif klasörleri, ham veri yolları.
4. Anahtarsız yerel kurulum çalışır hâle gelir (sahte sağlayıcılar).
5. Kök dosyalar: README (İngilizce) ve README.tr, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, LICENSE.
6. `.github/`: issue ve PR şablonları, etiketler, yalnız kontrol çalıştıran CI.
7. İlk on beş kadar küçük iş "good first issue" olarak açılır ([görevler](gorevler.md) içindeki 🌱 satırları).
8. Duyuru: kısa bir yazı ve örnek bir dergi.

Repoda hiçbir zaman bulunmayacaklar: kullanıcı rüyası, B ve C kademesi korpus verisi, anahtarlar, yayın kimlikleri.

## Katkı şeritleri

Kod yazmayan da katkı verebilmeli. Her şeridin kendi klasörü, kısa bir rehberi ve hazır işleri olur.

| Şerit | Ne yapılır | Kimin için |
| --- | --- | --- |
| İkonlar | Bir sembolün küçük ikonunu çiz ya da iyileştir | Çizerler, tasarımcılar |
| Sözlük | Sembol etiketlerini kendi diline çevir, eş anlamlıları bağla | Herkes |
| Gelenekler | Kendi kültürünün serbest lisanslı tabir kaynağını ekle | Araştırmacılar, meraklılar |
| Eval | Modelin zorlandığı bir rüya örneği ekle | Herkes |
| Dergi düzenleri | Yeni bir sayfa düzeni tasarla | Ön yüz geliştiriciler |
| Çeviri | Arayüz metinlerini çevir | Herkes |
| Motor | Yeni bir ilişki türü ve puanlayıcısı yaz | Backend geliştiriciler |
| Koala | Maskota yeni poz | Çizerler |
| Araştırma | Bir soruya kaynaklı kısa bir araştırma kartı yaz ([araştırma](arastirma.md)) | Okuyanlar, kendi kültürünü bilenler |

Her şeritte ilk katkı on beş dakikada yapılabilecek kadar küçük tutulur.

## Eğlenceli ve sıcak tutan şeyler

- **Haftanın sembolü:** her hafta bir sembol seçilir; ikonu, çevirileri ve geleneklerdeki anlamları o hafta tamamlanır.
- **Rüya gecesi:** aylık sürüm; her sürüm bir sembolün adını taşır, notları kısa ve resimlidir.
- **Katkıcı duvarı:** uygulamanın künye sayfasında ve README'de; şeride göre küçük koala rozetleri (ikon ustası, sözlük bekçisi, gelenek taşıyıcısı).
- **İlk katkı karşılaması:** ilk PR'ı birleşen kişiye teşekkür ve sıradaki küçük iş önerisi.
- **Rüya bağışı:** isteyen, anonim bir rüyasını açık veri setine bağışlar; katkı kod olmak zorunda değildir.
- **Görünür yol haritası:** proje panosunda fazlar; kimin neyi aldığı açık.

Ton: meraklı, nazik, şakacı. Rüya yorumlarında kimsenin inancı ya da geleneği küçümsenmez; bu, davranış kurallarında yazılıdır.

## Ritim

| Sıklık | Ne |
| --- | --- |
| Sürekli | Küçük, tek konulu commit'ler; her PR bir işi kapatır |
| Haftalık | Haftanın sembolü; açık PR'ların incelenmesi; yeni küçük işlerin açılması |
| Aylık | Sürüm notu, katkıcı duvarı güncellemesi |
| Faz sonunda | Yol haritası ve karar kayıtlarının gözden geçirilmesi |

Düzenli küçük commit bir gösteri değil, işin doğal biçimidir: [görevler](gorevler.md) belgesindeki her satır tek PR'dır.

## Repo kuralları

- Dallar `feat/<konu>`, `fix/<konu>`; `main`'e yalnız PR ile, squash merge.
- Commit'ler Conventional Commits, İngilizce, kısa.
- Kod, değişken ve dosya adları İngilizce. Public yüz (README, katkı rehberi, issue şablonları) İngilizce; Türkçe README yanında durur. Ürün kararları ve iç belgeler Türkçe kalabilir.
- PR şablonu: ne değişti, neden, nasıl denendi, dikkat.
- CI geçmeden birleştirme yok; yayın elle yapılır.
- Yeni bağımlılık bir issue'da gerekçesiyle tartışılır.
- Güvenlik açığı herkese açık issue ile değil, SECURITY dosyasındaki özel kanalla bildirilir.

## Yönetim

Küçük başlar: tek bakımcı, kararlar `docs/kararlar/` altında yazılı. Düzenli katkı veren kişiler şerit bakımcısı olur (ör. ikonlar, sözlük). Büyük yön değişiklikleri önce issue'da tartışılır, sonra karar kaydı olur.

## Açık veri

| Veri | Lisans | Yer |
| --- | --- | --- |
| Sembol sözlüğü (kavram, etiketler, hiyerarşi) | CC BY-SA 4.0 | Repo ve veri seti sürümü |
| A kademesi tabir anlamları | Kaynağının lisansı, alan bazında belirtilir | Veri seti sürümü |
| İkonlar | CC BY 4.0 | Repo |
| Bağışlanan rüyalar | CC0 | Veri seti sürümü; elle gözden geçirilmiş |
| Eval setleri | CC BY 4.0 | Repo |

Kullanıcı rüyaları, vektörleri ve kenarları açık veri değildir.

## Yapılmadan açılmayacaklar

- Sır temizliği ve anahtar döndürme tamamlanmadan repo public olmaz.
- Anahtarsız yerel kurulum çalışmadan "katkı bekliyoruz" denmez.
- Davranış kuralları ve güvenlik kanalı olmadan dış katkı kabul edilmez.
