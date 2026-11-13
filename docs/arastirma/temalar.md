# İlk tema listesi (A2)

`theme` düğümlerinin ilk tohumu. İki bağımsız kaynağın birleşimi: anketle ölçülen tipik rüya temaları ([kart](notlar/olcum-tipik-temalar.md)) ve 44 bin Reddit rüyasından denetimsiz çıkarılan 22 tema ([kart](notlar/kolektif-reddit.md)). Her tema HVdC kategorisine bağlanır ([kart](notlar/olcum-hvdc-normlar.md)).

Bu liste sınıflandırma için değil, başlangıç içindir: model tema adaylarını serbest çıkarır, bu liste normalize ederken çekirdek görevi görür; yeni temalar aday olarak eklenir ([motor](../motor.md)).

## Çekirdek temalar

"Yaygınlık" sütunu, öğrenci örneklemlerindeki ömür boyu yaygınlığın kabaca ifadesidir; kişiye gösterilmez, kolektif göstergenin taban çizgisi ve benzerlikte IDF ağırlığının ilk tahmini için kullanılır.

| Anahtar | Türkçe etiket | Kaynak | HVdC | Yaygınlık |
| --- | --- | --- | --- | --- |
| `chased` | Kovalanmak | TDQ | Etkileşim (saldırgan) | Çok yüksek |
| `falling` | Düşmek | TDQ | Etkinlik (hareket) | Çok yüksek |
| `paralysis` | Hareket edememek, felç olmak | TDQ (Almanya) | Etkinlik | Orta |
| `school` | Okul, sınav, ders | TDQ, Reddit | Mekân, başarısızlık | Yüksek |
| `work` | İş, işyeri | Reddit | Mekân, etkinlik | Orta |
| `sexual` | Cinsellik | TDQ, Reddit | Etkileşim (cinsel) | Yüksek |
| `relationships` | İlişkiler, aile, partner | Reddit | Karakterler | Çok yüksek |
| `cheating` | Aldatma, aldatılma | Reddit (tekrarlayan) | Etkileşim | Orta |
| `animals` | Hayvanlar | Reddit | Karakterler (hayvan) | Yüksek |
| `supernatural` | Doğaüstü varlıklar, hayalet | Reddit | Karakterler (yaratık) | Orta |
| `religious` | Dinî ve ruhani | Reddit | — | Orta |
| `flying` | Uçmak | TDQ | Etkinlik (hareket) | Yüksek |
| `violence_death` | Şiddet ve ölüm | Reddit | Etkileşim (saldırgan) | Yüksek |
| `death_of_loved` | Sevdiği birinin ölümü | TDQ | Karakterler, talihsizlik | Orta |
| `deceased_visit` | Ölmüş birinin görünmesi | TDQ | Karakterler | Orta |
| `teeth` | Dişlerin dökülmesi | TDQ, Reddit (beden) | Nesne (beden) | Orta |
| `body` | Beden, kan, yaralanma | Reddit | Nesne (beden) | Orta |
| `pregnancy_birth` | Hamilelik ve doğum | Reddit (canlı rüya) | Hayat olayı | Düşük |
| `late` | Geç kalmak, yetişememek | TDQ | Başarısızlık | Yüksek |
| `lost` | Kaybolmak, yolu bulamamak | TDQ | Mekân, talihsizlik | Orta |
| `naked_public` | Herkesin önünde çıplak olmak | TDQ | Etkileşim | Orta |
| `house_rooms` | Evde yeni odalar keşfetmek | TDQ | Mekân (iç) | Orta |
| `water` | Su, deniz, sel, boğulma | TDQ | Mekân (dış), talihsizlik | Orta |
| `disaster` | Afet, yangın, deprem | TDQ | Talihsizlik | Orta |
| `war` | Savaş, asker | Reddit | Etkileşim (saldırgan) | Düşük, olaya duyarlı |
| `vehicle` | Araç, kaza, fren tutmaması | TDQ | Nesne, talihsizlik | Orta |
| `technology` | Telefon, ekran, medya | Reddit | Nesne | Orta |
| `space_aliens` | Uzay, uzaylılar | Reddit | Mekân, karakter | Düşük |
| `time` | Zaman, zaman yolculuğu | Reddit | — | Düşük |
| `weather` | Hava, fırtına | Reddit | Mekân (dış) | Düşük |
| `sounds` | Sesler, sessizlik | Reddit | Etkinlik (işitme) | Düşük |
| `control` | Rüyayı kontrol etmek, fark etmek | Reddit (lucid) | — | Düşük |
| `life_events` | Düğün, taşınma, mezuniyet | Reddit | Hayat olayı | Orta |
| `trapped` | Kapana kısılmak, kilitli ya da bağlı kalmak, nefes alamamak | TDQ | Talihsizlik | Bilinmiyor |
| `own_death` | Öldürülmek, kendini ölü görmek | TDQ | Talihsizlik | Bilinmiyor |
| `killing` | Birini öldürmek | TDQ | Etkileşim (saldırgan) | Bilinmiyor |
| `repetition` | Bir şeyi tekrar tekrar denemek | TDQ | Başarısızlık | Bilinmiyor |
| `powers` | Büyülü güç, üstün bilgi | TDQ | Başarı | Bilinmiyor |
| `transformation` | Başka biri ya da bir şey olmak: karşı cins, hayvan, nesne, yeniden çocuk | TDQ | Karakterler (rüyacı) | Bilinmiyor |
| `presence` | Odada bir varlık sezmek, çok yakında bir yüz görmek | TDQ | Karakterler | Bilinmiyor |
| `food` | Yemek, lezzetli yiyecekler | TDQ | Yeme-içme | Bilinmiyor |
| `money` | Para bulmak | TDQ | İyi talih | Bilinmiyor |
| `toilet` | Tuvalet bulamamak ya da utanmak | TDQ | Talihsizlik | Bilinmiyor |
| `mirror` | Kendini aynada görmek | TDQ | Nesne | Bilinmiyor |

## TDQ eşlemesi (A12)

Tipik Rüyalar Anketi'nin 56 maddelik sürümü (Nielsen 2012, ek; yanıt 0 hiç – 4 on bir ve üstü) her maddesiyle bir anahtara bağlandı:

- `chased` 1 · `violence_death` 2 · `repetition` 3 · `paralysis` 4, 44 · `food` 5 · `late` 6 · `water` 7, 21 · `trapped` 8, 15, 39
- `animals` 9, 24, 40 · `money` 10 · `flying` 11 · `falling` 12, 37 · `naked_public` 13, 14 · `powers` 16, 20 · `supernatural` 17, 56
- `teeth` 18 · `mirror` 19 · `disaster` 21, 22, 23, 34, 54 · `transformation` 25, 26, 49, 50 · `own_death` 27, 28 · `presence` 29, 45
- `toilet` 30 · `school` 31, 38 · `sexual` 32 · `vehicle` 33 · `deceased_visit` 35 · `death_of_loved` 36 · `technology` 41 · `killing` 42
- `space_aliens` 46, 47, 48 · `religious` 51, 52 · `house_rooms` 53 · `pregnancy_birth` 55
- Anahtarsız kalan madde: 43 (deliler). TDQ karşılığı olmayanlar (Reddit'ten): `work`, `relationships`, `cheating`, `body`, `lost`, `time`, `weather`, `sounds`, `control`, `life_events`, `war`

Maddeler F5 onboarding sorusunun ("hangilerini gördün") ham listesidir; ölçeğin kendisi değil, yalnız tema adları kullanılır.

## Aday temalar

Çekirdeğe rızalı veride sıklık görülünce girer.

| Anahtar | Etiket | Kaynak |
| --- | --- | --- |
| `deceased_request` | Ölmüş yakının bir şey istemesi ya da haber vermesi | Türk halkbilimi ([kart](notlar/kultur-turk-halkbilimi.md)) |
| `omen_marriage` | Kısmet, evlenecek kişiyi görmek | Türk halkbilimi |

## Kurallar

- **Etiket dili:** anahtar İngilizce ve sabit; etiket her dilde ayrı (`entities.labels`). Türkçe etiketler bu tablodan gelir; diğer diller topluluk işidir.
- **Çoklu tema:** bir rüya birden çok tema taşır; her biri ağırlık ve anlatımdan alıntıyla.
- **Tür ile tema ayrı:** `genres` (gündelik, fantastik…) ve deneyimler (lucid, tekrar, kâbus) tema değildir; ayrı alanlarda kalır.
- **Yaygın tema bilgi taşımaz:** "çok yüksek" yaygınlıktaki temalar benzerlik puanında düşük ağırlık alır ([motor](../motor.md)).
- **Olaya duyarlı temalar:** `war`, `disaster`, `religious` gibi temalar toplumsal olaylarla dalgalanır ([kart](notlar/kolektif-reddit.md)); kolektif göstergede en anlamlı adaylar bunlardır.
- **Kültür farkı:** Türkçe anlatılarda farklı sıklıklar beklenir (ör. dinî figürler, ölmüş yakınlar); taban oranları rızalı veriden yeniden hesaplanana kadar bu tablo yalnız başlangıçtır.

## Eksikler

- TDQ maddelerinin tek tek yaygınlık oranları okunmadı (Nielsen 2003, Kanada; tam metin bot korumalı); yeni satırların yaygınlığı bilinmiyor.
- Türk kültürüne özgü sık temalar (ör. rüyada ölmüş yakının bir şey istemesi, kutsal mekânlar, düğün) için Türkçe kaynak taranacak ([kart](notlar/kultur-paylasma.md)).
- "Yaygınlık" sütunu nitel bir tahmin; oranlar kişiye gösterilmez.
