# 0004: Vektörler pgvector'da, benzerlik bileşik puanla

Tarih: 2026-11-13. Durum: kabul.

## Sorun

Benzer rüyaları bulmak ve bir benzeşme oranı göstermek gerekiyor. İki soru var: vektörler nerede duracak ve oran nasıl hesaplanacak?

## Vektör deposu

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| pgvector (mevcut Postgres) | Erişim kuralıyla tek sorgu; rüya silinince vektör de gider; yeni servis yok | Çok büyük ölçekte ayrı sistemler kadar hızlı değil |
| Ayrı vektör servisi | Büyük ölçekte hız, hazır filtreleme | İkinci veri kaynağı; silme ve rıza iki yerde; maliyet |
| Bellekte indeks | En basit | Süreç yeniden başlayınca kaybolur; birden çok kopya ile uyuşmaz |

## Oran hesabı

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Yalnız embedding kosinüsü | Tek satır | Neden benzediği açıklanamaz; uzunluk ve üsluba duyarlı |
| Yalnız ortak etiket sayısı | Açıklanabilir | Eş anlamlıları ve atmosferi kaçırır |
| Bileşik puan (anlatı vektörü + IDF ağırlıklı semboller + duygu + tema + yapı) | Hem anlam hem açıklama; ağırlıklar ayarlanır | Kalibrasyon ister; daha çok kod |
| Model hakemli (iki rüyayı LLM karşılaştırır) | İnsan sezgisine en yakın | Çift başına çağrı; ölçeklenmez; tutarsız |

## Karar

Vektörler pgvector'da, model adıyla ayrı tabloda (`dream_embeddings`). Oran bileşik puandır; kullanıcıya puanın bilinen dağılımdaki yüzdelik sırası gösterilir. Ayrıntı: [motor](../motor.md).

## Gerekçe

- Ürün ilkesi: her oran açıklanır. Bileşik puan, modalda gösterilecek ortak noktaları doğrudan üretir.
- Aday bulma (kNN) ucuz ve hızlı, puanlama yalnız adaylar üzerinde koşar.
- Model hakemi yalnız eval'de kullanılır: altın çiftlerin etiketlenmesine yardım eder, çevrimiçi yolda yoktur.
- Vektör modeli değişebilir; model adını saklamak ve ayrı tablo, geçişi migration'sız yapar.

## Kurallar

- Tek embedding modeli ve tek boyut aynı anda aramada kullanılır.
- Ağırlık ve eşik değişikliği `algo_version` artırır ve altın çift sonucuyla birlikte gelir.
- Yüzde, örneklem yetersizken gösterilmez.
- Vektör kullanıcıya ya da başka kullanıcıya hiçbir uçtan dönmez.

## Yeniden değerlendirme tetikleyicileri

- On milyonlarca vektör ya da gecikme hedefinin tutmaması.
- Altın çiftlerde bileşik puanın yalın kosinüsten iyi çıkmaması: o zaman yalınlaştırılır.

## Geri dönüş yolu

Arama tek bir SQL fonksiyonunun arkasındadır; depo değişirse yalnız o fonksiyonun çağrıldığı `store` modülü değişir.
