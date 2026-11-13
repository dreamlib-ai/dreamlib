# 0001: Backend modüler monolit olarak kalır

Tarih: 2026-11-13. Durum: kabul.

## Sorun

Motor; yorum, indeksleme, ikon, dergi, video ve eşleşme gibi farklı iş yükleri getiriyor. Beta 25 kişi, hedef büyük ölçek. Baştan mikroservis mi, monolit mi?

## Seçenekler

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Modüler monolit, tek kod tabanı, iki rol (`api`, `worker`) | Tek yayın, tek veritabanı işlemi, kolay yerel kurulum, katkıcı için düşük eşik | Bir modüldeki hata tüm süreci etkileyebilir; tek dil |
| Mikroservisler (yorum, üretim, motor ayrı) | Bağımsız ölçek ve yayın | Dağıtık işlem, servisler arası sözleşme, gözlem ve yayın yükü; tek geliştirici için ağır |
| Monolit + sunucusuz işlevler (üretim için) | Çizim yükü ayrışır | İki çalışma ortamı, durum paylaşımı zorlaşır, yerel kurulum karışır |

## Karar

Modüler monolit. Katmanlar klasörle ayrılır (`routes`, `engine`, `pipelines`, `providers`, `store`); modüller birbirine yalnız açık fonksiyonlarla dokunur. Worker aynı koddan ayrı süreç olarak çalışabilir (bugün de mümkün).

## Gerekçe

- İş yükünün darboğazı dış servis beklemesi; ölçek sorunu süreç sayısıyla çözülür, servis sayısıyla değil.
- Kalıcı Postgres kuyruğu, işlerin API'den ayrışmasını zaten sağlıyor.
- Açık kaynakta katkıcının tek komutla her şeyi ayağa kaldırabilmesi, mimari saflıktan değerli.
- Mikroservisin çözdüğü sorunlar (ekipler arası bağımsızlık, farklı ölçek profilleri) henüz yok.

## Servise bölme tetikleyicileri

- Worker'lar birden çok makineye yayılmalı ve Postgres kuyruğu yetmiyor.
- Bir modülün ölçek ya da güvenlik profili diğerlerinden kalıcı biçimde ayrışıyor (ör. ayrı ağda çalışması gereken moderasyon).
- Birden çok ekip aynı kod tabanında birbirini bekliyor.

## Geri dönüş yolu

Modül sınırları korunursa bir modül ayrı servise taşınabilir: `pipelines` zaten yalnız kuyruk ve `store` üzerinden konuşur. İlk aday üretim worker'ıdır; taşımak kod değil yayın değişikliğidir.
