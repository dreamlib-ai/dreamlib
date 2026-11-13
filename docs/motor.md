# Motor: rüya grafiği, benzerlik, eşleşme, kümülatif yorum

Motor, rüyaları düğümlere (sembol, tema, duygu…) bağlar ve düğümler ile rüyalar arasında tipli, kanıtlı kenarlar kurar. Hepsi Postgres içindedir. Kararlar: [0003](kararlar/0003-postgres-grafigi.md), [0004](kararlar/0004-pgvector-embedding.md).

## Şema

| Tablo | İçerik |
| --- | --- |
| `entity_kinds` | Düğüm türleri: `symbol`, `theme`, `emotion`, `place`, `action`, `archetype`; araştırmadan eklenenler `character` (rol, tanıdıklık), `interaction` (saldırgan, dostça, cinsel), `setting` (iç/dış, tanıdıklık), `outcome` (başarı, başarısızlık, talih), `motif` (Thompson dizini). Yeni tür bir satırdır ([HVdC eşlemesi](arastirma/notlar/olcum-hvdc-normlar.md)) |
| `entities` | Düğüm sözlüğü: tür, kanonik anahtar, çok dilli etiketler, embedding, Wikidata QID, durum (`candidate`, `approved`, `merged`), `merged_into` |
| `entity_aliases` | Yazım ve dil varyantları → düğüm |
| `dream_entities` | Rüya → düğüm: ağırlık, kaynak (`model`, `user`), çıkarıcı sürümü, anlatımdan alıntı |
| `relation_types` | İlişki kaydı: anahtar, kaynak ve hedef türü, simetrik mi, puanlayıcı adı ve sürümü |
| `edges` | Kenar: tür, kaynak, hedef, ağırlık (0–1), `evidence` jsonb, `algo_version`, zaman |
| `dream_embeddings` | Rüya vektörü: model adı, boyut, tür (`narrative`, `symbolic`); HNSW indeksli |
| `lexicon_entries` | A kademesi tabir anlamları: düğüm, gelenek, dil, anlam, kaynak, yer bilgisi |
| `analyses` | Her yorum ayrı satır: pipeline, prompt ve model sürümü, girdi özeti, çıktı, maliyet |
| `consents` | Rıza defteri: kullanıcı, kapsam, sürüm, verildi, geri çekildi |

`dreams` tablosu sahibinin okuduğu geniş kayıt olarak kalır; ilişki ve arama yeni tablolardan yürür. Mevcut `features` ve `objects` alanları geçişte `dream_entities` satırlarına açılır, eski kayıtlar isteğe bağlı yeniden yorumla dolar.

## Yeni ilişki türü eklemek

İlişki türleri koda gömülü sabit bir liste değildir.

1. `relation_types` tablosuna satır: `key`, uç türleri, simetri.
2. `backend/app/engine/relations/` altında bir puanlayıcı: iki ucu alır, ağırlık ve kanıt döndürür.
3. Puanlayıcı kayda adıyla bağlanır; `index` işi kayıtlı tüm puanlayıcıları çalıştırır.

Şema değişmez, mevcut kenarlar bozulmaz. Puanlayıcı değişirse `algo_version` artar; eski kenarlar yeni sürüm yazılana kadar okunur, sonra süpürülür.

Başlangıç türleri:

| Anahtar | Uçlar | Anlam |
| --- | --- | --- |
| `similar` | rüya ↔ rüya | Bileşik benzerlik |
| `recurs` | rüya → rüya | Aynı kişide tekrar eden örüntü |
| `series` | rüya → rüya | Kullanıcının kendi kurduğu bağ |
| `co_occurs` | düğüm ↔ düğüm | Birlikte görülme (PMI) |
| `is_a`, `same_as` | düğüm → düğüm | Sözlük hiyerarşisi ve birleştirme |
| `rem` | kişi ↔ kişi | Önbelleklenmiş eşleşme |
| `evokes_motif` | rüya → motif | Masal ve mit motifi eşleşmesi; alıntıyla doğrulanır ([kart](arastirma/notlar/kultur-motif-dizini.md)) |
| `day_residue` | rüya → gündüz olayı | Uyanık hayattan iz; kullanıcı bağlar ya da model önerir ([kart](arastirma/notlar/bilim-sureklilik.md)) |

Zincir sorguları (rüya → sembol → başka rüya → tema) derinliği üçle sınırlı recursive CTE ile yazılır ve SQL fonksiyonu olarak sunulur.

## İndeksleme (otonom)

Rüya kaydedilince ya da yeniden yorumlanınca `index` işi kuyruğa girer ([üretim](uretim.md)):

1. **Çıkar:** LLM, şemaya bağlı çıktıyla sembol, yer, eylem, duygu ve tema adaylarını alıntılarıyla verir.
2. **Normalize et:** aday önce `entity_aliases` içinde aranır, yoksa embedding ile en yakın onaylı düğüme bağlanır; eşik altındaysa `candidate` düğüm açılır.
3. **Vektörle:** anlatı metni ve sembol listesi ayrı ayrı embed edilir.
4. **Komşu bul:** kNN ile en yakın adaylar; erişim kuralı sorgunun içindedir (kendi rüyaları + rızalı rüyalar).
5. **Puanla ve yaz:** kayıtlı puanlayıcılar çalışır, eşik üstü kenarlar kanıtıyla yazılır.

Aday düğümler birikince gece işi benzerlerini birleştirme önerisine çevirir; onay elle ya da yüksek güvenle otomatik olur. İkon kütüphanesi onaylı düğümleri izler.

## Benzeşme oranı

`similar` puanı tek bir embedding uzaklığı değildir; açıklanabilsin diye bileşiktir:

| Bileşen | Hesap | Neden |
| --- | --- | --- |
| Anlatı | Vektör kosinüsü | Olay örgüsü ve atmosfer |
| Semboller | IDF ağırlıklı kesişim | Nadir ortak sembol, sık olandan değerlidir |
| Duygu | Duygu dağılımı kosinüsü | Aynı olay farklı duyguyla farklı rüyadır |
| Tema ve tür | Kesişim | Kaba gruplama |
| Yapı | Bakış açısı, lucid/tekrar/kâbus beyanı | Deneyim biçimi |

Ağırlıklar `algo_version` ile sürümlenir; ilk değerler çevrimdışı çalışmadan gelir ([veri](veri.md)). Kullanıcıya gösterilen yüzde ham puan değil, puanın bilinen dağılımdaki yüzdelik sırasıdır. `evidence` alanı ortak sembolleri, bileşen puanlarını ve örneklem büyüklüğünü taşır; modal bunu çizer.

## Kişi eşleşmesi (REM)

- Profil vektörü, kişinin `collective` ya da `public` rızalı rüyalarından kurulur: ortalama anlatı vektörü, sembol sıklık vektörü, duygu dağılımı.
- Oran, bir profil açıldığında hesaplanır ve `rem` kenarı olarak sürüm ve örneklem sayısıyla önbelleklenir; taraflardan biri yeni rüya ekleyince bayatlar.
- Her iki tarafta en az üç rızalı rüya yoksa oran gösterilmez.
- Modal şunları gösterir: oran, ortak semboller (ikonlarıyla), ortak temalar, duygu örtüşmesi ve yalnız iki taraf da paylaştıysa en benzer rüya çifti.
- Kişiye tek başına bir "uyku" ya da "psikoloji" yüzdesi verilmez; oran her zaman iki kişi arasındadır.

## Kümülatif yorum

Tek çağrılı yorumun yerini dört adımlı hat alır:

1. **Çıkar** ve 2. **normalize et** (indekslemeyle ortak).
3. **Getir:**
   - sözlük: rüyadaki düğümlerin A kademesi anlamları, gelenek ve kaynak bilgisiyle;
   - kişisel: kullanıcının en benzer geçmiş rüyaları (vektör araması; "son 15 kayıt" kuralının yerini alır, izin yine rüya başına);
   - kolektif: benzer rızalı rüyalardan toplamlar ("bu sembol en çok şu duyguyla görülüyor"), yalnız en az beş kişiden.
4. **Sentezle:** model bu bağlamla yorumu yazar; bağ yoksa zorlamaz. Çıktı parçalıdır: rüyanın kendisi, semboller, sende tekrar edenler, başkalarında.

Her yorum `analyses` tablosuna sürümleriyle yazılır; aynı rüyanın eski yorumu silinmez. Sözlük anlamı kullanılan cümle kaynağını taşır.

## Erişim kuralları

- `private` rüya yalnız sahibinin kişisel bağlamına girer; başkasıyla kenarı olmaz.
- `collective` rüya toplamlara ve eşleşmeye girer; metni, başlığı ve görseli kimseye gösterilmez.
- `public` rüyanın dergisi herkese açıktır; ham anlatım yine yalnız sahibindedir.
- Rıza düşürülünce ilgili kenarlar ve önbellekler aynı işlemde silinir.

## Ölçüm

`evals/` altında küçük, sürümlü setler: çıkarım (TR/EN), benzerlik altın çiftleri, alıntı denetimi, hassas içerik. CI kayıtlı yanıtlarla koşar; canlı model koşusu elle tetiklenir ve sonuç tabloya yazılır.
