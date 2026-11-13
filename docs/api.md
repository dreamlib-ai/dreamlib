# API

Backend FastAPI; çalışırken etkileşimli şema `http://127.0.0.1:8080/docs`. Hata her yerde `{"error": "Türkçe mesaj"}` ve uygun durum kodu. Giriş gereken uçlar `Authorization: Bearer <Supabase access token>` ister Jeton backend'de projenin açık anahtarlarıyla (JWKS, ES256) doğrulanır; çıkış yapılmış jeton süresi dolana kadar (1 saat) geçerli kalır (yerelde `DREAMLIB_DEV_AUTH=1` ile `dev-` ile başlayan 12+ karakterli herhangi bir jeton).

| Uç | Giriş | Ne yapar |
| --- | --- | --- |
| `GET /healthz` | hayır | Hangi servisler açık (llm, images, speech, editor, accounts, worker) ve kuyruktaki iş sayısı (`queued`) |
| `POST /api/clean` | evet | `{text}` → `{cleanText, language}` yazım düzeltme |
| `POST /api/analyze` | evet | `{text, type, mood?, sleep?, personal?}` → başlık, etiketler, yorum, nesneler, duygular |
| `POST /api/images` | evet | `{prompt, style, count}` → 202 `{id}` (en çok 4 görsel); sonuç `GET /api/jobs/{id}` panellerinde |
| `POST /api/transcribe?lang=tr` | evet | Ham ses gövdesi (Content-Type `audio/*`, 8 MB) → `{text}` |
| `POST /api/manga` | evet | `{title, text, style, panels: 4\|6\|9, consistent}` → 202 `{id}`; kitapçığı worker yapar |
| `GET /api/jobs/{id}` | evet | `{status: running\|done\|failed, done, total, panels, error}` |
| `POST /api/jobs/{id}/panels/{n}/redo` | evet | Biten kitapçığın n. panelini yeniden çizer |
| `POST /api/dreams` | evet | Rüyayı kaydeder (`jobId` verilirse paneller ve çizim taslağı sunucudan alınır) |
| `PUT /api/dreams/{uuid}?existing=false` | evet | Aynı rüyayı sabit kimlikle oluşturur/günceller; tekrar istek kayıt çoğaltmaz. `existing=true` silinen kaydı yeniden oluşturmaz |
| `POST /api/events` | evet | Yalnız sabit ürün olayı, UUID olay kimliği ve platform; içerik/ek alan kabul etmez, servis loguna takma hesap koduyla yazar |
| `GET /api/dreams`, `GET /api/dreams/{id}` | evet | Kütüphane; panel `url`'leri süreli imzalı |
| `GET /api/dreams/{id}/status` | evet | Rüya için çalışan tüm işler (`index`, `glyph`, `magazine`…) tek yerden: `{dreamId, busy, jobs:[{id, kind, status, done, total, error, parentId}]}`. Başkasının rüyası 404 |
| `DELETE /api/dreams/{id}` | evet | Rüyayı ve görsellerini siler |
| `POST /api/dreams/{id}/panels/{n}/redo` | evet | Kayıtlı çizim taslağından paneli yeniler; eski taslaksız kayıt 409 |

Notlar
- İşler kalıcı kuyrukta (`jobs` tablosu) durur, API yeniden başlasa da kaldığı yerden sürer. Ayrıntı: `docs/mimari.md`. Kuyruktaki iş dışarıya `running` olarak görünür.
- Kitapçık: storyboard (LLM) + paneller (fal kuyruğu, 3 eşzamanlı) + private Storage kovası `dream-images`. `consistent` açıkken ilk panel sonraki panellere referanstır; edit hatası sessizce farklı karaktere dönüşmez.
- Ücretli her uç giriş ister (misafir anonim oturum yeterli). Günlük haklar, 24 saat:

  | Hak | Misafir | Hesap | Ayar |
  | --- | --- | --- | --- |
  | Kitapçık ve görsel işi (başarısız sayılmaz) | 3 | 10 | `DAILY_LIMIT_GUEST`, `DAILY_LIMIT_USER` |
  | Yorum: clean, analyze, transcribe (ortak) | 30 | 100 | `DAILY_TEXT_GUEST`, `DAILY_TEXT_USER` |
  | Panel yenileme | 10 | 30 | `DAILY_REDO_GUEST`, `DAILY_REDO_USER` |

  İş hakkı `jobs` tablosundan, yorum ve yenileme hakkı `call_log` tablosundan sayılır (`take_call`); kaç API kopyası çalışırsa çalışsın sayaç tek.
- 429: kullanıcının zaten bir işi sürüyor ya da günlük hakkı doldu. 409: iş sürerken kayıt ya da panel yenileme; aynı kitapçığı ikinci kez kaydetmek.
- Bitmiş işler 7 gün sonra silinir; rüyaya kaydedilmemiş kitapçıkların görselleri de gider. Yenilenen panelin eski dosyası silinir.
- Gövde sınırı 1 MB (ses 8 MB). Şema `supabase/migrations/` içinde tarih sırasıyla: `20261014000001…06` başlangıç şeması, paneller ve Storage, ruh hali ve uyku, çizim taslağı, iş kuyruğu, günlük haklar ve kullanıcı kilitleri; sonrakiler anket, günlük ve özellik alanları. Supabase CLI ile uygulanır: `supabase db query --linked --project-ref <proje-ref> -f supabase/migrations/<dosya>.sql` (önce bir kez `supabase login`).

- Manga isteğinde isteğe bağlı UUID `requestId` verilebilir. Aynı hesap ve aynı içerikle tekrar aynı işi döndürür; kota/üretim yeniden çalışmaz. Farklı içerik 409; başka hesabın işi okunmaz. Kaydetmede `job.state.savedDreamId` aynı kitapçığın başka rüyaya kopyalanmasını engeller.

- Analiz `personal=true` ise geçmiş bağlamını kullanır; varsayılan false. `excludeId` isteğe bağlı UUID, düzenlenen rüyayı kaynaklardan çıkarır. Liste sorgusu yalnız kullanıcıya ait en çok 15 kaydı getirir; metin parçaları kayıt başına 200 karakterdir.

- `PATCH /api/dreams/{id}/journal`: zorunlu `revision`; isteğe bağlı `title`, `originalText`, `dreamedOn` (YYYY-MM-DD/null), `favorite`, `reflection`, `addition:{id:UUID,text}`, `refresh`, `personal`. Kayıt sahibi süzülür, beklenen revizyonla atomik güncelleme yapılır; çakışma 409. Ayrıntılar zamanlıdır, ilk anlatım korunur. Yenileme düşünceyi dışlar, anlatım ve tüm ayrıntılar 4000 karakteri aşarsa kesmek yerine 400 döner. Analiz ve çizim eskiliği ayrı tutulur. Şema: `supabase/migrations/20261102111656_dream_journal.sql`.

- Analiz ve kayıt JSON'unda `features`: sürüm, `genres` (daily/fantasy/scifi/romance/adventure/suspense), `perspective` (first-person/observer/mixed/unknown), people/places/events ve `experiences:[{kind,quote}]`. kind lucid/recurring/nightmare; açık beyanın anlatımdaki alıntısı doğrulanır. Modelin eşanlamlı `type` anahtarı kind'a normalize edilir. Eski kayıtlar version=0 kalır; yeniden yorumla güncellenir.
- Journal PATCH ek alanları: `classification:{genres?,perspective?,experiences?,tags?}` ve `recall` (boş/clear/fragmentary/faint). Düzeltmeler model verisini silmez; [] bilinçli boş seçimdir, null modele döner. Yeniden yorum düzeltmeleri korur. Yeni kolon: `supabase/migrations/20261102113817_dream_features.sql`. Kişisel yorum geçmişte kullanıcı tarafından düzeltilen temaları kullanır.
