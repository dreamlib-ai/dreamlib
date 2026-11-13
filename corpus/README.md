# Rüya tabiri korpusu

Tabir sözlüğü (Faz D) için kaynak toplama. Kod burada, ham veri git dışında `CORPUS_ROOT` altında (varsayılan `corpus-data/raw`; `CORPUS_CONTACT` ile kendi iletişim adresini ver). Kaynak atlası ve hak sahipleri raporu aynı klasörün üstünde `reports/`.

## Kurallar

- Her istek `fetch.Fetcher` üzerinden: robots.txt (bizim ajan, ClaudeBot, anthropic-ai) kontrolü, host başına bekleme, 401/403/451'de dur. Bot korumasını, girişi, ödeme duvarını aşma; `Blocked` gelirse kaynak `blocked.jsonl`'a düşer ve görüşülecekler listesine girer.
- Her kaynak kendi klasöründe: `raw/<kaynak>/files/` ham dosyalar, `manifest.jsonl` (url, tarih, sha256, lisans, hak sahibi), `entries.jsonl` çıkarılmış satırlar, `notes.md` kısa durum.
- Kaynak betikleri `corpus/sources/<kaynak>.py`; çalıştırma `backend/.venv/Scripts/python -m corpus.sources.<kaynak>` (repo kökünden). Yeni bağımlılık yok (httpx + stdlib).
- Ham veri ve çıkarılmış satırlar repoya girmez; yalnız kod.

## entries.jsonl satırı

```text
source, tradition, language, symbol_raw, condition, meaning, polarity (iyi/kötü/nötr/koşullu/bilinmiyor),
domain, url, locator (bölüm/sayfa/madde), license, rights_holder, attributed_author
```

Bilinmeyen alan boş kalır; uydurma yok. `meaning` kaynaktaki metnin kendisi (çeviri ayrı alan `meaning_tr` ile eklenebilir).
