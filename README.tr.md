# Dreamlib

Uyanınca rüyanı sesle anlat. Dreamlib onu sembolleriyle okur, küçük resimli bir dergiye çevirir, kütüphanende saklar ve istersen benzer rüya görenlerle ortak noktalarını gösterir.

Dreamlib açık bir rüya motorudur: kod, sembol sözlüğü, ikon kütüphanesi ve ölçüm setleri açıktır. Rüyaların açık değildir. Kendin bağışlamadıkça hiçbir rüya bu repoya ya da açık bir veri setine girmez.

English: [README.md](README.md)

## Bugün çalışanlar

- Ses öncelikli rüya kaydı; yazı ikinci seçenek
- Sembol, duygu, tür ve bakış açısıyla yorum
- Arka planda çizilen, karakteri tutarlı resimli kitapçık
- Arama, filtre, tarih ve favorili özel kütüphane

## Yapılmakta olanlar

- Rüyaları sembol, tema ve duygu üzerinden bağlayan rüya grafiği
- Açıklanabilir benzerlik: her eşleşme oranı arkasındaki ortak noktaları gösterir
- Rüyayı kendi geçmiş rüyalarınla ve izin vermiş kişilerin benzer rüyalarıyla birlikte okuyan yorum
- Sayfa çevrilerek okunan, paylaşılabilen dergiler ve kapak duvarı gibi görünen kütüphane
- Aynı backend üstünde mobil uygulama

Plan: [docs/vizyon.md](docs/vizyon.md), [docs/yol-haritasi.md](docs/yol-haritasi.md). Kararlar ve bedelleri: [docs/kararlar](docs/kararlar). İşler: [docs/gorevler.md](docs/gorevler.md).

## Yapı

```text
frontend/  React + TypeScript + Vite
backend/   Python + FastAPI, Postgres iş kuyruğu, OpenRouter ve fal istemcileri
corpus/    tabir kaynağı toplayıcıları (yalnız kod, veri yok)
docs/      mimari, motor, veri, yol haritası, kararlar
scripts/   setup, dev, check
```

## Başlangıç

```powershell
npm run setup   # frontend paketleri + backend/.venv; backend/.env oluşur
npm run dev     # backend :8080 (şema /docs), frontend :5173
npm run check   # pytest, tip kontrolü ve build
```

`backend/.env` içinde `DREAMLIB_DEV_AUTH=1` ve `DREAMLIB_FAKE_AI=1`, tüm akışı Supabase projesi ve ücretli anahtar olmadan, bellekte hesaplar ve örnek yapay zekâ cevaplarıyla çalıştırır. Gerçek yorum ve görsel için kendi anahtarın gerekir; `backend/env.example` dosyasına bak.

## Katkı

Yardım etmek için backend kodu yazmak gerekmez. Bir sembolün ikonunu çizebilir, sembol etiketlerini diline çevirebilir, kültürünün kamu malı bir tabirnamesini ekleyebilir ya da ölçüm setine zor bir rüya ekleyebilirsin. Başlangıç: [CONTRIBUTING.md](CONTRIBUTING.md).

[Davranış kurallarını](CODE_OF_CONDUCT.md) oku. Güvenlik sorunlarını [SECURITY.md](SECURITY.md) içindeki özel kanaldan bildir.

Çalışma kuralları ve kod düzeni: [AGENTS.md](AGENTS.md).

## Lisans

Kod AGPL-3.0. Sözlük verisi, ikonlar ve ölçüm setleri kendi Creative Commons lisanslarını taşır: [docs/acik-kaynak.md](docs/acik-kaynak.md).
