# Lab: LLM'siz analiz

Rüya metninin analizini mümkün olduğunca dil modeli olmadan, kurallar ve sözlüklerle yapmak. LLM bu yolda karşılaştırma ölçütü ve yedektir; her parametre önce kuralla denenir, kural hedefi tutturamazsa nedeni ölçülür.

## İlkeler

- **Kanıtlı:** her sonuç, metindeki yeriyle birlikte hangi sözcük ya da kalıptan geldiğini taşır. "Neden korku dedin?" sorusunun cevabı her zaman gösterilebilir.
- **Ölçülü:** her motor model ile aynı eval setinde, aynı tabloda ölçülür (`python evals/run.py --engine lexicon`). Hedefler `evals/targets.toml`'da.
- **Yerel ve ucuz:** kod yalnız standart kütüphane kullanır; metin makineden çıkmaz, çağrı başına maliyet yok.
- **HVdC'ye sadık:** Hall–Van de Castle kodlaması çoğu kategoride yalnız açıkça söyleneni kodlar (duygu ancak "korktum" diye yazılmışsa). Bu, sözlük yaklaşımının zayıflığı değil, kodlama kuralının kendisi.

## Durum

| Parametre | Kuralla | Durum |
| --- | --- | --- |
| Duygu (beş HVdC sınıfı) | Kök sözlüğü, Türkçe olumsuzluk (`-ma/-me`, `-sız`) ve İngilizce `not/never` cümlecik içinde | v0: `backend/app/lab/emotions.py` |
| Bakış açısı | Cümle cümle: gözlemci işaretleri ("kendimi dışarıdan", "like a movie") ve birinci tekil ekler/zamirler (`-dım`, `-yorum`, `ben`, `I`) | v0: `backend/app/lab/perspective.py` |
| Olumsuzlama, zaman | Dil bilgisi ekleri, zaman sözcükleri | Kolay |
| Yiyecek, nesneler | HVdC nesne sınıflarına göre sözlük | Sözlük emeği |
| Mekân | İç/dış, tanıdık/yabancı sözlüğü | Sözlük emeği |
| Karakterler | Akrabalık, meslek, zamir sözlükleri, sayı; cinsiyet Türkçede çoğu zaman yazılmaz | Orta |
| Etkileşimler (saldırı, dostluk, cinsellik) | Fiil sözlükleri; kimin kime yaptığı için cümle çözümleme gerekir | Zor |
| Talih, başarı, başarısızlık | Kalıp + fiil sözlüğü | Orta |
| Beyanlar (lucid, tekrar, kâbus) | Uygulamanın kendi işaret listesi (`classification.MARKERS`), cümle birebir alıntı, inkâr eden cümle sayılmaz | v0: `backend/app/lab/experiences.py`; ölçüm `quote` setini bekliyor |
| Temalar, tür | Sözlük kümeleri ve yukarıdaki kodların birleşimi | Ölçümden sonra |
| Benzerlik | HVdC kod sayıları vektörü + TF-IDF/BM25 | Yapılabilir, aşağıda |

### Duygu v0'ın ilk ölçümü

Sentetik 10 örnekte (`evals/extract`): makro F1 0,69, üzüntü 1,00, mutluluk 0,80. Kaçırdıklarının hepsi duygunun söylenmediği, davranıştan çıkarıldığı örnekler (bağırma, kovalanma, "hiç bu kadar hafif hissetmemiştim"). Sentetik set bu örnekleri çıkarımla kodlamıştı; HVdC kuralıyla kodlanan gerçek sette bu örneklerde duygu kodu olmaz. Ders: altın set HVdC kılavuzuna sadık kodlanmalı. Çıkarılan duygu istenirse ayrı bir parametre olur, karıştırılmaz.

### Bakış açısı v0'ın ilk ölçümü

14 örnekte (10 birinci şahıs, 3 gözlemci, 1 karışık) doğruluk 0,93 (hedef 0,85). Kaçan tek örnek bilerek konmuş zor örnek: "Kendimi dışarıdan izliyordum… Yatağımda uyuyordum" — ikinci cümledeki fiil izlenen benliği anlatıyor, kural bunu katılım sayıp `mixed` diyor. Kayıtlı model yanıtlarında 0,00 görünmesi, o sentetik yanıtlarda bakış açısı alanı olmamasından; model ölçümü gerçek koşuyla yapılır.

### Bulunan hata

Uygulamanın `classification.normalized` işlevi her `I`'yı Türkçe kuralla `ı`'ya çevirdiği için İngilizce beyan işaretleri ("knew i was dreaming") hiç eşleşmiyordu: modelin doğru İngilizce lucid ve tekrar beyanları da reddediliyordu. `has_marker` her iki küçük harf biçimine bakıyor.

## Yapıyı beslemek için gerekenler

1. **Altın set (en önemlisi).** HVdC kılavuzuna göre elle kodlanmış raporlar, Türkçe ve İngilizce, parametre başına en az 200 rapor ve iki kodlayıcı. Kaynaklar:
   - İngilizce: DreamBank raporları ve yayımlanmış HVdC kodları (lisans: araştırma kullanımı; NC ise yalnız çevrimdışı ölçümde, B kademesi).
   - Türkçe: Çelepi tezi (A14, PDF bekleniyor), kendi yazdığımız ve rıza veren kullanıcıların düzelttiği raporlar.
2. **Sözlükler.** Kendi açık (CC0) Türkçe ve İngilizce sözlüklerimiz, HVdC kategorilerine göre: duygu (başlandı), nesne, mekân, karakter, etkileşim fiilleri, talih kalıpları. Lisansı kısıtlı sözlükler (NRC gibi) yalnız karşılaştırma için.
3. **Türkçe biçimbilim.** Bugün kök başı eşleşmesi ve olumsuzluk ekleri yetiyor. Karakter ve etkileşim için ek çözümleme gerekecek: Zemberek (Java, Apache-2.0, çevrimdışı araç) ya da kendi yazacağımız saf Python ek ayırıcı. İkisi de yeni bağımlılık ya da büyük iş, karar gerekir.
4. **Ölçüm döngüsü.** Her yeni kural ya da sözlük girdisi `evals/run.py --engine lexicon` ile ölçülür; LLM sonucu aynı tabloda tavan olarak durur. Kaçırılan her örnek ya sözlüğe girer ya da "kural dışı" diye not edilir.

## Embedding (L4) seçenekleri

L4 istemcisi hazır ama model seçilmedi; seçilene kadar vektör üretilmez. LLM'siz hedefle üç yol:

| Yol | Ne | Artı | Eksi |
| --- | --- | --- | --- |
| A. Kod vektörü + TF-IDF | HVdC kod sayıları ve sözcük ağırlıkları, standart kütüphane | Açıklanabilir ("ikisinde de korku ve su var"), ücretsiz, bağımlılık yok | Eş anlamlıları kaçırır (deniz/okyanus) |
| B. Yerel açık model | multilingual-e5-small ya da bge-m3, ONNX ile makinede | Anlam benzerliği, metin dışarı çıkmaz | Yeni Python bağımlılığı, 100–500 MB model, onay gerekir |
| C. API (bugünkü L4) | OpenRouter embedding modeli | Kurulum yok | Ücretli, metin dışarı çıkar |

Öneri: benzerliğin ilk sürümü A ile kurulur (`similar` puanı zaten bileşik ve açıklanabilir olmalı, [motor](motor.md)). B, eş anlam eksikliği ölçümde görünürse eklenir. C yalnız karşılaştırma için kalır.

## Sıradaki adımlar

1. Beyanlar için `quote` eval seti (kesinlik hedefi 0,95).
2. Sentetik setin HVdC kuralına göre yeniden kodlanması ve gerçek örneklerle büyütülmesi.
3. Kod vektörü + TF-IDF benzerliği (A), altın çiftlerle ölçüm.
4. Nesne, mekân ve karakter sözlükleri.
