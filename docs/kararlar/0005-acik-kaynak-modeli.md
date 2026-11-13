# 0005: Temiz geçmişli public repo, AGPL-3.0

Tarih: 2026-11-13. Durum: kabul. Önceki karar: yalnız yan repolar (sözlük, eval) açık olacaktı.

## Sorun

Dreamlib açık kaynak bir proje olacak ve dış katkı alacak. Repo bugün özel; geçmişinde onlarca dal ve çalışma ağacında izlenmeyen sır dosyaları var. Neyi, nasıl ve hangi lisansla açacağız?

## Kapsam

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Tüm uygulama açık, temiz geçmişle yeni repo | Geçmişteki sır riski sıfır; en geniş katkı alanı; "rüyanla ne yapıyoruz" sorusuna tam cevap | Eski commit geçmişi public'te görünmez |
| Mevcut repoyu public yapmak | Geçmiş korunur | Sızıntı bulunursa geçmişi yeniden yazmak ve her anahtarı döndürmek gerekir; iç notlar da açılır |
| Açık çekirdek (motor açık, prompt ve yayın kapalı) | Bazı parçalar korunur | İki repo senkronu; katkıcı tam sistemi çalıştıramaz |
| Yalnız yan repolar | En az risk | Topluluk projesi olmaz |

## Lisans

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| AGPL-3.0 | Kodu servis olarak çalıştıran da değişikliklerini açar; klonlanıp kapatılmayı önler | Bazı şirketler AGPL koda katkı vermez ya da kullanmaz |
| Apache-2.0 | Düşük katkı engeli, patent maddesi | Kapalı klon serbest |
| MIT | En basit | Patent maddesi yok, klon serbest |

## Karar

Tüm uygulama, temizlenmiş ağaçtan tek ilk commit ile yeni public repoda; lisans AGPL-3.0. Eski özel repo arşiv olarak kalır. Adımlar: [açık kaynak](../acik-kaynak.md).

## Gerekçe

- Projenin değeri veride ve toplulukta; kodun kapalı tutulması koruma sağlamaz, AGPL ise açık kalmasını güvenceye alır.
- Toplumsal amaç (açık rüya sözlüğü) ile kapalı servis klonu çelişir.
- Temiz geçmiş, tarama ne kadar iyi olursa olsun kalan sızıntı riskini ortadan kaldırır.
- Abonelik geliri barındırılan servisten gelir; AGPL bunu engellemez.

## Sonuçları

- "Repoda CI yok" kuralı değişir: dış katkı için yalnız kontrol çalıştıran CI gerekir. Yayın elle kalır.
- Yayın kimlikleri, iç adresler ve anket yönetim bilgisi repodan çıkar.
- Veri ve ikonlar koddan ayrı lisanslanır (CC ailesi); tablo açık kaynak planındadır.
- Katkıcıdan telif devri istenmez; katkı, projenin lisansıyla verilmiş sayılır ve bu katkı rehberinde yazar.
- Bağımlılık eklerken AGPL ile uyum kontrol edilir.

## Yeniden değerlendirme tetikleyicileri

- AGPL, önemli bir katkıcı ya da ortak için somut engel olursa.
- Ayrı bir istemci kitaplığı (ör. üretilen API istemcisi) daha serbest lisans gerektirirse: yalnız o paket ayrı lisanslanır.

## Geri dönüş yolu

Lisans, telif sahiplerinin onayıyla değiştirilebilir; katkıcı sayısı arttıkça zorlaşır. Bu yüzden karar çıkıştan önce verildi. Repo istenirse yeniden özele alınabilir ama yayımlanmış sürüm AGPL altında kalır.
