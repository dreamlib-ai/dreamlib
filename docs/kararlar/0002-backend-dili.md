# 0002: Backend dili Python kalır

Tarih: 2026-11-13. Durum: kabul. Önceki karar: 2026-10-24, Go'dan Python'a geçiş.

## Sorun

Hedef "verimli bir dille yazılmış backend". Bugünkü backend Python 3.13 + FastAPI, canlıda ve testli. Verim için dil değiştirmek gerekir mi?

## Seçenekler

| Seçenek | Artı | Eksi |
| --- | --- | --- |
| Python + FastAPI (mevcut) | Çalışan kod ve testler; veri ve embedding araştırmasıyla aynı dil; en geniş katkıcı kitlesi | İstek başına CPU ve bellek maliyeti yüksek; tip güvencesi çalışma anında |
| Go | Düşük bellek, tek ikili dosya, güçlü eşzamanlılık | Tam yeniden yazım; iki ay önce bırakılmış yol; veri betikleri yine Python |
| TypeScript (Node ya da Bun) | Web, mobil ve backend tek dil; tipler paylaşılır | Tam yeniden yazım; veri işleri Python'da kalır |
| Rust | En yüksek verim | En yavaş geliştirme; katkıcı eşiği yüksek |

## Karar

Python kalır.

## Gerekçe

- Bir isteğin süresi ve maliyeti dil modeli ve görsel üretim beklemesidir; backend'in kendi CPU süresi bunun yanında ölçülemeyecek kadar küçük.
- CPU ağırlıklı tek iş olan vektör araması Postgres içinde koşar.
- Yeniden yazım kullanıcıya görünür bir şey kazandırmaz, betayı haftalarca geciktirir.
- Verim mimariden gelir: `async` G/Ç, kalıcı kuyruk, yeniden ödememe, ucuz görev modelleri, önceden üretilmiş ikon ve küçük resimler.

## Verim için alınan önlemler

- Tüm dış çağrılar `async` ve paylaşılan `httpx` istemcisiyle.
- Ağır iş API sürecinden kuyruğa alınır; worker ayrı süreç olabilir.
- Vektör ve zincir sorguları SQL fonksiyonu olarak veritabanında.
- Bağımlılık listesi kısa tutulur (bugün dört paket).

## Yeniden değerlendirme tetikleyicileri

- Ölçümle, backend'in kendi CPU süresi istek süresinin anlamlı bir payı olursa.
- Bellek maliyeti barındırma faturasında belirleyici kalem olursa.
- Dar ve sıcak bir yol çıkarsa (ör. gerçek zamanlı ses akışı): yalnız o yol ayrı bir küçük bileşen olarak başka dilde yazılır.

## Geri dönüş yolu

API sözleşmesi OpenAPI şemasıyla tanımlı ve istemci ondan üretiliyor; backend başka dilde yeniden yazılırsa istemciler değişmez. Veritabanı şeması ve SQL fonksiyonları dilden bağımsızdır.
