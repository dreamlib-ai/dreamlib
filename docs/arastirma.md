# Araştırma programı

Motor, rüyalar hakkında bildiğimiz kadar iyi olur. Eldeki korpus ağırlıkla tabir sözlüğü; rüyanın biyolojisi, felsefesi, mitolojisi, kültürlerdeki yeri ve ölçüm yöntemleri eksik. Bu program o açığı kapatır ve proje boyunca sürer: Faz 0 onu başlatır, sonraki her fazın yanında paralel yürür ([yol haritası](yol-haritasi.md)).

Araştırmanın amacı okumak değil, motora bir şey taşımaktır: yeni bir düğüm türü, bir ilişki türü, bir metrik, bir yorum kuralı ya da bir arayüz fikri.

## Alanlar

| Alan | Soru | Belge |
| --- | --- | --- |
| Bilim | Rüya neden ve nasıl oluşur; içeriğini ne belirler | [bilim](arastirma/bilim.md) |
| Felsefe | Rüya nedir: deneyim mi, hayal mi; benlik rüyada nerede | [felsefe](arastirma/felsefe.md) |
| Mitoloji ve kültür | İnsanlar rüyayı tarih boyunca nasıl okudu ve paylaştı | [mitoloji ve kültür](arastirma/mitoloji-kultur.md) |
| Kolektif rüya | Bir toplum aynı dönemde benzer rüyalar görür mü; bu nasıl ölçülür | [kolektif](arastirma/kolektif.md) |
| Ölçüm ve veri | Rüya içeriği nasıl kodlanır, hangi ölçek ve veri setleri var | [ölçüm ve veri](arastirma/olcum-veri.md) |
| Uygulamalar | Benzer ürünler ne yaptı, neden tuttu ya da battı; kimden ne öğrenilir | [uygulamalar](arastirma/uygulamalar.md) |

Araştırmadan doğan ürün fikirleri: [fikirler](fikirler.md).

## Döngü

1. **Soru.** Her araştırma tek bir soruyla başlar ("tipik rüya temaları kültürden kültüre ne kadar değişir?"). Sorular alan belgelerinde durur.
2. **Tara.** Önce derleme ve ansiklopedi maddesi, sonra birincil kaynak. Kaynağın türü not edilir: hakemli çalışma, kitap, klasik metin, gazete yazısı, ürün sayfası.
3. **Kart yaz.** Bulgu kısa bir karta dökülür (aşağıdaki şablon), `docs/arastirma/notlar/` altına.
4. **Taşı.** Kartın "motora etkisi" satırı bir göreve, bir karar kaydına ya da bir fikre dönüşür; dönüşmüyorsa kart yine kalır ama iş açılmaz.
5. **Veri varsa topla.** Bulunan açık veri ya da metin, lisans kademesiyle birlikte korpus hattına girer ([veri](veri.md)).

## Kart şablonu

```text
# <soru>
Tarih, alan
Kısa cevap: iki üç cümle
Kaynaklar: başlık, yazar, yıl, bağlantı, tür (hakemli / kitap / klasik / gazete / ürün)
Güven: yüksek / orta / düşük ve nedeni
Motora etkisi: düğüm türü | ilişki türü | metrik | yorum kuralı | arayüz | yok
Açık kalan: sıradaki soru
Veri: varsa adı, lisansı, kademesi
```

Kart en çok bir ekran tutar. Uzun alıntı yapılmaz; kaynak özetlenir ve bağlanır.

## Kaynak kuralları

- İddia ile kanıt ayrılır. Bir tek çalışmanın bulgusu "gösterildi" diye yazılmaz; örneklem ve yöntem not edilir.
- Rüya araştırmasının zayıf noktaları bilinerek okunur: çoğu örneklem öğrenci, çoğu veri hatırlanan rüya, çoğu ölçek doğrulanmamış.
- Popüler yazılar ve ürün blogları yalnız iz sürmek için kullanılır; karta dayanak olmaz.
- Dinî ve kültürel gelenekler kendi terimleriyle aktarılır; doğru ya da yanlış diye sıralanmaz.
- Metin toplarken mevcut kurallar geçerlidir: robots.txt ve erişim reddi aşılmaz, lisans kademesi yazılır.
- Ürüne giren hiçbir cümle tıbbi ya da psikolojik teşhis iddiası taşımaz; araştırma bulgusu yoruma "şöyle bir görüş var" olarak girer.

## Bulgu motora nasıl girer

| Bulgu türü | Örnek | Nereye |
| --- | --- | --- |
| Sınıflandırma | Tipik rüya temaları listesi | `theme` düğümleri için tohum |
| Kodlama şeması | Karakter, etkileşim, duygu, mekân kategorileri | Çıkarım prompt'u ve `entity_kinds` |
| Sembol kaynağı | Bir geleneğin serbest lisanslı tabirnamesi | A kademesi sözlük |
| Örüntü | Olumsuz rüyalarda anlatı döngüleri | Yeni metrik ya da puanlayıcı bileşeni |
| Ölçek | Hatırlama netliği, lucidlik ölçeği | Journal alanı |
| Kuram | Süreklilik: rüya uyanık hayatı yansıtır | Yorum kuralı, kişisel bağlam ağırlığı |
| Uyarı | Kolektif örüntü iddiaları küçük örnekleme dayanıyor | Arayüz dili ve en az kişi kuralı |
| Motif | Masal ve mit motifleri dizini | Yeni ilişki türü: rüya → motif |

## Ritim

| Sıklık | Ne |
| --- | --- |
| Haftalık | Bir soru, bir kart |
| Aylık | Alan belgelerinin güncellenmesi: kapanan soru silinir, yenisi eklenir |
| Faz başında | O fazın işlerini etkileyen soruların öne alınması |
| Sürekli | Yeni bulunan kaynak ve veri setinin korpus atlasına işlenmesi |

Kart yazmak dışarıdan katkıya açıktır: bir kültürün rüya geleneğini bilen ya da bir alanı okuyan herkes kart ekleyebilir ([açık kaynak](acik-kaynak.md)).

## Faz 0 çıktıları

İlk tur 2026-11-13'te yapıldı: [kartlar](arastirma/notlar/), [tema listesi](arastirma/temalar.md), [hassas içerik taslağı](hassas-icerik.md), [fikir süzmesi](fikirler.md). İkinci tur aynı gün (A10–A13). Üçüncü tur 2026-11-14: uygulama karşılaştırmasının ikinci turu (A4). Kalan yalnız uzman okuması (A7, kenarda); kültür kartı topluluğa açık iş.

Faz 0'ın bitmesi için kod gerekmez; şunlar gerekir:

- Her alan için ilk kartlar (alan başına en az üç).
- İlk tema listesi: tipik rüya temaları, kaynaklarıyla.
- İlk düğüm türü ve ilişki türü önerisi: araştırmanın [motor](motor.md) şemasında neyi değiştirdiği.
- Bakılan uygulamaların karşılaştırma tablosu ve bizden farkı.
- Bulunacak metinler listesi: hangi klasik, hangi derleme, hangi veri seti, hangisi serbest.
- Hassas içerik politikası için okuma (kâbus, travma, yas rüyaları).

## İlk on soru

1. Tipik rüya temaları hangileri ve kültürler arasında ne kadar ortak?
2. Hall–Van de Castle şemasının kategorileri bizim düğüm türlerimize nasıl oturur; neresi eksik kalır?
3. Dil modelleriyle rüya içeriği kodlamanın bilinen doğruluğu ve tuzakları neler?
4. "Benzer rüya" araştırmada nasıl tanımlanmış; hangi benzerlik ölçüleri denenmiş?
5. Toplumsal olaylar rüya içeriğini ölçülebilir biçimde değiştiriyor mu?
6. Rüya paylaşmanın kişiye ve ilişkiye etkisi hakkında ne biliniyor?
7. Geleneklerin sembol okuma mantığı nasıl farklılaşıyor (koşula bağlı anlam, rüyayı görenin kimliği, zıddıyla yorum)?
8. Türkçe ve Türkiye'ye özgü rüya araştırması ve geleneği ne durumda?
9. Rüya hatırlamayı ne artırır; sabah kaydı için en iyi an ve yöntem ne?
10. Önceki kolektif rüya uygulamaları neden kalıcı olamadı?
