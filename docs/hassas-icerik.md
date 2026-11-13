# Hassas içerik politikası (taslak)

Durum: taslak, A7. Betadan önce Cenker'in onayı ve bir ruh sağlığı uzmanının gözden geçirmesi gerekir. Bu belge hukuki ya da klinik görüş değildir. Dayanak kartı: [kâbus](arastirma/notlar/bilim-kabus.md). Riskler: [riskler](riskler.md).

## Amaç

Rüyalar korku, yas, travma, şiddet, cinsellik ve kendine zarar içerebilir. Dreamlib bu rüyaları kaydetmeye, yorumlamaya ve saklamaya devam eder; amaç bunları dışlamak değil, kişiyi yalnız bırakmadan ve korkutmadan karşılamaktır.

## İlkeler

1. **Normalleştir.** Kâbus ve kötü rüya çok yaygındır. Tek bir kötü rüya için uyarı, kırmızı kutu ya da "yardım al" mesajı gösterilmez.
2. **Teşhis koyma.** Model ve arayüz "kâbus bozukluğu", "travma", "depresyon" gibi tanı sözcüklerini kişiye yakıştırmaz, risk puanı göstermez.
3. **Yönlendir, tedavi etme.** Ürün terapi değildir. Gerektiğinde gerçek destek kaynağına yönlendirir.
4. **Ayrıntı verme.** Kendine zarar yöntemi ya da benzeri ayrıntı ne yorumda ne görselde üretilir (WHO güvenli iletişim önerileri doğrultusunda).
5. **Mahremiyet önce.** Hassas bir rüya hiçbir zaman otomatik olarak paylaşıma, kolektife ya da herkese açık kütüphaneye önerilmez.
6. **Yerel ol.** Destek kaynakları kişinin ülkesine göre gösterilir; doğrulanmamış numara gösterilmez.

## Durumlar ve davranış

| Durum | Nasıl anlaşılır | Yorum | Ek davranış |
| --- | --- | --- | --- |
| Kötü rüya, korku | Duygu ve anlatım | Yumuşak, normalleştiren dil (bugünkü prompt) | Yok |
| Kâbus (kişi öyle adlandırıyor) | `experiences: nightmare` (alıntılı) | Aynı; "kâbuslar çok yaygın" bağlamı | İsteğe bağlı "sonunu yeniden yaz" eylemi (aşağıda) |
| Sık kâbus | Kişinin kendi kayıtlarında kısa sürede birden çok kâbus beyanı (eşik aşağıda) | Aynı | Yalnız ona, sakin bir bilgi kartı ve destek kaynağı; bir kez gösterilir, kapatılabilir, tekrar sıklığı sınırlı |
| Yas, ölmüş yakın | Karakter ve tema (`deceased_visit`, `death_of_loved`) | Şefkatli; yası "çözülecek sorun" gibi ele almaz | Yok |
| Travma işaretleri (yeniden yaşama, şiddet mağduriyeti) | Anlatım ve model sınıflaması | Yorum kısa ve destekleyici; sembol çözümlemesi geri planda | Destek kaynağı satırı |
| Kendine zarar ya da intihar ifadesi | Anlatımda açık ifade (rüyanın içinde ya da kişinin kendi notunda) | Kısa, sıcak, yargısız bir yanıt; yorumun önünde | Destek kaynağı her zaman gösterilir; sıklık eşiği yok |
| Başkasına zarar, cinsel şiddet | Anlatım | Rüyanın kişiyi tanımlamadığını belirten yumuşak dil | Görsel üretimi bu sahneleri çizmez |
| Reşit olmayan izlenimi | Yaş beyanı (karar bekliyor) | — | Herkese açık paylaşım kapalı |

**Sık kâbus eşiği (öneri):** son 14 günde en az 4 kâbus beyanı. Eşik ürün kararıdır, klinik ölçüt değildir; uzman görüşüyle ayarlanır.

## Destek kaynakları

- **Acil durum:** her ülkede yerel acil numara (Türkiye'de 112).
- **Türkiye:** Bu taramada 7/24 çalışan, intihar düşüncesine özel ulusal bir hat bulunamadı; 2008'de kapanan 182 hattından sonra böyle bir hat kurulmadığı, Eylül 2026'da meslek örgütlerinin de bunun eksikliğini vurguladığı bildiriliyor. ALO 183 Aile ve Sosyal Hizmetler Bakanlığı'nın sosyal destek hattıdır, intihar hattı değildir. Gençlik Destek Hattı gibi kaynakların güncel numaraları doğrulanmadan gösterilmez.
- **Diğer ülkeler:** Find A Helpline gibi uluslararası dizinler ülkeye göre kaynak listeler; entegrasyon ve güncellik ayrıca değerlendirilmeli.
- **Kural:** her kaynak bir sorumlu kişi tarafından en az üç ayda bir kontrol edilir; kontrol tarihi kaynak listesinde tutulur.

## "Sonunu yeniden yaz" (isteğe bağlı)

Kâbus sonrası bir düğme: "İstersen bu rüyanın sonunu değiştir." Kullanıcı yeni sonu sesle ya da yazıyla anlatır; ilk anlatım korunur, yeni son ayrı saklanır, istenirse dergide son sayfa olur. Görüntü provası terapisinden esinlenir ama terapi değildir; ürün metninde tedavi iddiası olmaz.

## Uygulama

| Parça | Nerede |
| --- | --- |
| Sınıflama | `extract` görevi: `sensitive` alanı (`none`, `distress`, `trauma`, `self_harm`), alıntıyla; yalnız açık ifadede `self_harm` |
| Yorum | `interpret` prompt'unda kurallar (ilke 1–4) |
| Görsel | Storyboard prompt'unda yasak sahne listesi; fal içerik bayrağı |
| Arayüz | Destek kartı bileşeni; ülkeye göre kaynak listesi tek dosyada |
| Paylaşım | `sensitive` işaretli rüyada paylaşım önerisi yok; kullanıcı yine de kendisi paylaşabilir, öncesinde kısa bir onay |
| Log | Hassas sınıflama içerik taşımaz; ürün olayı yalnız "destek kartı gösterildi" sayar |
| Eval | `evals/` altında hassas içerik seti: yanlış alarm (sıradan korku) ve kaçırma (açık ifade) örnekleri |

## Bilinen sınırlar

- Modeller açık intihar ifadelerini makul tanır, örtük ya da edilgen ifadelerde tutarsızdır; sınıflamanın kaçırma oranı eval ile izlenir.
- Rüyadaki ölüm ya da şiddet çoğu zaman kişinin niyeti değildir; yanlış alarm, yorumu bozmamalı ve kişiyi utandırmamalıdır.
- Bu belge kullanıcı rüyasını bir uzmana iletmez; ürün acil müdahale sistemi değildir ve bunu açıkça söyler.

## Kaynaklar

- [AAFP, kâbus ve kâbus bozukluğu](https://www.aafp.org/afp/afp-community-blog/nightmares-and-nightmare-disorder-diagnosis-and-treatment)
- [JMIR 2026, LLM'lerin intiharla ilgili yanıtları ve WHO güvenli iletişim önerileri](https://www.jmir.org/2026/1/e97968/PDF)
- [Jed Foundation, yapay zekâ sektörüne açık mektup](https://jedfoundation.org/open-letter-to-the-ai-and-technology-industry/)
- [Find A Helpline, Türkiye](https://findahelpline.com/countries/tr/topics/suicidal-thoughts)
- [Evrensel, 10 Eylül 2026 dernekler açıklaması](https://www.evrensel.net/haber/6000016/derneklerden-10-eylul-intihari-onleme-gunu-aciklamasi-intihari-onlemek-kamusal-sorumluluktur)
- [T24, acil intihar hattının kapanması](https://t24.com.tr/dunya/acil-intihar-hatti-14-yildir-kapali,1007718)
