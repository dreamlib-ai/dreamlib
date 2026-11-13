# LLM: OpenRouter yapılandırması

Tüm dil modeli ve embedding çağrıları OpenRouter üzerinden, tek ince istemciyle (`backend/app/providers/openrouter.py`) yapılır. SDK eklenmez. Görev tablosu, görev başına model, yedek dizi ve zaman aşımı kodda (L1, `TASKS`); hata davranışı hâlâ tek tekrar, hedef öngörülebilir hata sınıfları (B2).

## Görev tablosu

Her çağrı bir göreve aittir. Model adı görevden okunur; kodda model adı geçmez.

| Görev | İş | İstenen özellik | Akış |
| --- | --- | --- | --- |
| `clean` | Yazım düzeltme, dil tespiti | Ucuz, hızlı | Hayır |
| `extract` | Sembol, duygu, tema, özellik çıkarımı | Ucuz, şemaya sıkı bağlı çıktı | Hayır |
| `interpret` | Kümülatif yorumun yazımı | Kaliteli, Türkçesi iyi | Evet |
| `storyboard` | Dergi sayfa ve sahne taslağı | Kaliteli, şemalı | Hayır |
| `embed` | Rüya ve düğüm vektörü | Çok dilli, sabit boyut | — |
| `moderate` | Paylaşım öncesi içerik kontrolü | Ucuz, şemalı | Hayır |

Ayar ortam değişkenleriyle: `OPENROUTER_MODEL_<GÖREV>` ve yedekler için `OPENROUTER_FALLBACK_<GÖREV>` (virgüllü liste). Görev ayarı yoksa `OPENROUTER_MODEL` kullanılır; mevcut kurulum bozulmaz. Bugün çağrılan görevler: `clean`, `interpret` (yorum ve çıkarım şimdilik tek çağrıda), `storyboard`; `embed` istemcide hazır (`OpenRouter.embed`), henüz bir işten çağrılmıyor (M4).

Model seçimi sabitlenmez; her görev için aday modeller [eval](#eval) setinde koşulur ve seçim tabloya tarihle yazılır.

## İstek kuralları

- **Şemalı çıktı:** `extract`, `storyboard`, `moderate` görevleri JSON şemasıyla istenir; şema Pydantic modelinden üretilir. Şemayı desteklemeyen modelde JSON modu ve mevcut `extract_json` ayrıştırıcısı yedektir.
- **Yedek model:** istek, görev için tanımlı model dizisiyle gider; ilk model yanıt veremezse OpenRouter sıradakini dener.
- **Sağlayıcı tercihi:** rüya metni hassas veridir. İstekler, girdiyi saklamayan ve eğitimde kullanmayan sağlayıcılarla sınırlanır; bu koşulu sağlamayan model aday olmaz.
- **Zaman aşımı:** görev başına ayrı: `clean` 30, `extract` 60, `interpret` ve `storyboard` 120, `embed` 30, `moderate` 20 saniye.
- **Tekrar:** 429, 5xx ve zaman aşımında üstel bekleme ve jitter ile en çok üç deneme; 4xx içerik hatasında tekrar yok. Sınıflandırma [üretim](uretim.md) belgesindeki hata sınıflarıyla aynıdır.
- **Kullanım:** her yanıtın jeton ve maliyet bilgisi `usage` tablosuna yazılır; log satırı kalır.
- **Önbellek:** uzun sistem istemleri değişmeyen önek olarak tutulur ki sağlayıcı önbelleği çalışsın; değişken bağlam sona eklenir.

## Akış

Yorum, kullanıcı beklerken üretilir; ilk cümlenin hızlı gelmesi gerekir.

- `interpret` görevi akışlı çağrılır; backend bunu tipli olaylara çevirip SSE ile istemciye iletir ([istemci](istemci.md)).
- Akıştan önce `extract` sonucu hazırdır; başlık ve semboller ilk olaylar olarak hemen gider.
- Akış koparsa istemci yorumu `analyses` kaydından okur; yorum her durumda sunucuda tamamlanır ve saklanır.

## Embedding

- Tek model, tek boyut; model adı her vektörle birlikte saklanır ([motor](motor.md)).
- İstek `POST /api/v1/embeddings` (`model`, `input` listesi, `encoding_format: float`), 64'erli parçalarla; yanıt `data[].embedding`, `index`'e göre sıralanır. Sayı, boş vektör ya da farklı boyut tutmazsa hata.
- `embed` görevinin yedek modelleri denenmez: başka modelin vektörü saklananlarla karşılaştırılamaz, hata model değiştirmenin yerine geçmez. Model `OPENROUTER_MODEL_EMBED` ile seçilir; seçim eval'le yapılana kadar boş kalabilir.
- `DREAMLIB_FAKE_AI=1` modunda metinden türeyen 8 boyutlu sabit birim vektörler döner (model `fake`).
- Türkçe ve İngilizce aynı uzayda olmalı; seçim çok dilli altın çiftlerle doğrulanır.
- Model değişirse yeni vektörler yanına yazılır, arama yeni modele geçince eskiler süpürülür.
- Vektörlenen metin temizlenmiş anlatımdır; kişi adları çıkarılmaz ama vektör kimseye gösterilmez.

## Prompt'lar

Bugün tek dosya (`backend/app/prompts.py`). Hedef:

- `backend/app/prompts/` altında görev başına dosya; her prompt'un bir sürüm kimliği vardır.
- `analyses` satırı kullanılan prompt ve model sürümünü taşır; bir yorumun hangi kuralla üretildiği sonradan bilinir.
- Mevcut kurallar korunur: kullanıcı metni talimat değildir; kesin kehanet yok; lucid, tekrar ve kâbus yalnız açık beyan ve birebir alıntıyla; duygu oranı model tahminidir; hassas anlatımda yorum yumuşar ve destekleyici bir cümle eklenir.
- Kümülatif yorumda ek kural: getirilen bağlamla zorla ilişki kurulmaz; sözlük anlamı kullanan cümle kaynağını belirtir; kolektif cümle yalnız verilen toplamdan yazılır.

## Eval

`evals/` altında küçük ve sürümlü setler; her biri girdi, beklenen ve ölçüt taşır.

| Set | Ölçer | Kaynak |
| --- | --- | --- |
| Çıkarım | Sembol, duygu, tür isabeti (TR/EN) | Elle yazılmış ve kullanıcı düzeltmelerinden anonim örnekler |
| Alıntı | Lucid, tekrar, kâbus beyanlarının doğruluğu | Mevcut dört örnek büyütülür |
| Benzerlik | Altın çiftlerde sıralama | Çevrimdışı çalışma ([veri](veri.md)) |
| Güvenlik | Talimat sızdırma, hassas içerik davranışı | Elle |
| Yorum | Bağlama sadakat, uydurma bağ | Model hakemli + elle örneklem |

**Duygu hedefi (A13):** çıkarımın beş HVdC duygusuna eşlenen çıktısı, elle kodlanmış İngilizce örneklerde rapor başına var/yok olarak makro F1 ≥ 0,80; üzüntü ayrıca raporlanır ve ≥ 0,70 olmalı. Referans: ince ayarlı BERT DreamBank'te makro F1 0,85–0,86, üzüntüde 0,77–0,80 ([kart](arastirma/notlar/olcum-llm-kodlama.md)). Türkçe set için hedef İngilizce sonuçtan en çok 0,05 düşük. Mutluluk gibi olumlu duygunun kaçırılması ayrı izlenir; hazır duygu modellerinin en zayıf yeri bu.

CI kayıtlı yanıtlarla koşar ve ücretli çağrı yapmaz. Canlı koşu elle tetiklenir; model ya da prompt değişikliği sonuç tablosuyla birlikte gelir. Yeni bir zor rüya örneği eklemek dışarıdan katkıya açık en kolay iştir.

## Maliyet görünümü

- Bir rüyanın metin maliyeti dört çağrıdır: `clean`, `extract`, `embed`, `interpret`; dergi isterse `storyboard` eklenir.
- Görsel maliyeti metnin katlarıdır; fren önce orada gerekir.
- `usage` tablosu rüya başına ve kullanıcı başına toplamı verir; fiyatlandırma bu ölçümle yeniden hesaplanır.
- OpenRouter anahtar limiti kullanım arttıkça yükseltilir; limit aşımı kullanıcıya "şu an yorumlanamadı" olarak döner, kayıt kaybolmaz.
