"""Wikipedia dream pages from official dumps (dumps.wikimedia.org), 25 languages.

Streams each language's pages-articles-multistream index (not stored), finds
dream-related titles, then fetches only the matching bz2 streams with HTTP Range
and extracts wikitext. Every URL passes Fetcher.allowed() first; delays respected.
License: CC BY-SA 4.0 (text), contributors per page history.

Run: backend/.venv/Scripts/python -m corpus.sources.wikipedia_dumps [lang ...]
"""

from __future__ import annotations

import bz2
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import unescape

from corpus.fetch import ROOT, Blocked, Fetcher, Meta

SOURCE = "wikipedia-dumps"
BASE = "https://dumps.wikimedia.org"
T = {
 "en": "Dream|Dream interpretation|Oneiromancy|Lucid dream|Nightmare|Dream dictionary|Sleep paralysis|Activation-synthesis hypothesis|The Interpretation of Dreams|Oneirology|Dream incubation|Dreamtime|Ibn Sirin|Artemidorus|Oneirocritica|Night terror|Hypnagogia|Dream recall|Daydream|Dream diary|Dream yoga|Continual-activation theory|Neurocognitive theory of dreaming|Smorfia|Dream journal|Dream telepathy|Prophetic dream|Dreams in Islam|Dreams in Judaism|Kamil al-Ta'bir|Zhou Gong Jie Meng|Duke of Zhou's Interpretation of Dreams|Dream argument",
 "tr": "Rüya|Rüya tabiri|Berrak rüya|Kâbus|Kabus|Uyku felci|Rüyaların Yorumu|İbn Sirin|Artemidoros|Oneiromansi|Rüya yorumu|Rüya bilimi|Karabasan|Bilinçli rüya|Gece dehşeti|Tabirname|Rüya günlüğü",
 "ar": "حلم|تفسير الأحلام|حلم واضح|كابوس|شلل النوم|ابن سيرين|علم الأحلام|رؤيا|الحلم الصافي|تأويل الأحلام|تعبير الرؤيا|الرؤيا في الإسلام|الأحلام في الإسلام|الكابوس|الرؤيا الصادقة|الأحلام",
 "fa": "رؤیا|خواب|تعبیر خواب|کابوس|فلج خواب|ابن سیرین|خواب روشن|خواب دیدن|رویا|خوابگردی|تعبیر رویا|کامل التعبیر",
 "ur": "خواب|تعبیر خواب|ابن سیرین|ڈراؤنا خواب|خواب کی تعبیر|نیند کا مفلوج ہونا|رؤیا|خوابوں کی تعبیر",
 "he": "חלום|פתרון חלומות|חלום צלול|סיוט|שיתוק שינה|פרשנות החלומות|פירוש החלומות|חלום נבואי|פתרון חלום|חלומות ביהדות|חלומות בתלמוד|ספר חלומות",
 "zh": "夢|梦|解梦|周公解梦|清醒梦|噩梦|睡眠瘫痪|梦的解析|梦境|释梦|周公解夢|夢的解析|夢境|夢魘|清明夢|梦魇|解夢|占梦|梦占|夢占",
 "ja": "夢|夢占い|明晰夢|悪夢|金縛り|夢判断|夢の解釈|周公解夢|夢解き|正夢|初夢|夢違え|夢学|夢日記|夢告|夢合わせ|夢解釈",
 "ko": "꿈|해몽|자각몽|악몽|수면 마비|꿈의 해석|꿈 해석|가위눌림|주공해몽|길몽|흉몽|태몽|꿈풀이|예지몽",
 "hi": "स्वप्न|सपना|स्वप्न फल|स्वप्न विज्ञान|दु:स्वप्न|स्पष्ट स्वप्न|स्वप्नफल|स्वप्न शास्त्र|स्वप्नशास्त्र|सपनों की व्याख्या|ख्वाब|स्वप्न विश्लेषण|नींद का पक्षाघात|दुःस्वप्न|ख़्वाब",
 "id": "Mimpi|Tafsir mimpi|Mimpi jernih|Mimpi buruk|Lumpuh tidur|Ibnu Sirin|Primbon|Ta'bir mimpi|Mimpi lucid|Penafsiran mimpi|Ilmu mimpi",
 "vi": "Giấc mơ|Giải mộng|Mơ tỉnh|Ác mộng|Bóng đè|Mộng|Mơ|Giải mã giấc mơ|Chu Công giải mộng|Giấc mộng",
 "th": "ความฝัน|ทำนายฝัน|ฝันรู้ตัว|ฝันร้าย|อัมพาตขณะหลับ|ฝัน|การทำนายฝัน|การตีความฝัน|ฝันกลางวัน|ตำราทำนายฝัน",
 "ru": "Сон|Сновидение|Толкование сновидений|Осознанное сновидение|Кошмар|Сонный паралич|Онейромантия|Толкование снов|Онейрология|Сонник|Сны|Ясное сновидение|Онейроскопия|Сновидения|Интерпретация сновидений|Сон (физиология)|Ночной кошмар",
 "de": "Traum|Traumdeutung|Klartraum|Albtraum|Schlafparalyse|Die Traumdeutung|Oneiromantie|Traumforschung|Artemidor von Daldis|Ibn Sirin|Traumbuch|Traumdeuter|Traumtagebuch|Alptraum|Traumsymbol|Traumarbeit|Traumanalyse|Luzider Traum|Oneirologie|Schlafstarre",
 "fr": "Rêve|Onirologie|Oneiromancie|Rêve lucide|Cauchemar|Paralysie du sommeil|L'Interprétation des rêves|Interprétation des rêves|Clef des songes|Onirocritique|Songe|Oniromancie|Clé des songes|Terreur nocturne|Rêve éveillé|Journal de rêves|Onirisme|Artémidore de Daldis|Ibn Sirin|Songes",
 "es": "Sueño|Interpretación de los sueños|Oniromancia|Sueño lúcido|Pesadilla|Parálisis del sueño|La interpretación de los sueños|Onirología|Ensueño|Diario de sueños|Artemidoro de Daldis|Ibn Sirin|Onirocrítica|Terror nocturno|Sueños",
 "it": "Sogno|Interpretazione dei sogni|Oneiromanzia|Sogno lucido|Incubo|Paralisi nel sonno|L'interpretazione dei sogni|Smorfia napoletana|Onirologia|Smorfia|Onironautica|Artemidoro di Daldi|Ibn Sirin|Onirocritica|Diario dei sogni|Sogni|Paralisi del sonno|Terrore notturno|Libro dei sogni",
 "pt": "Sonho|Interpretação dos sonhos|Oniromancia|Sonho lúcido|Pesadelo|Paralisia do sono|A Interpretação dos Sonhos|Onirologia|Sonhos|Artemidoro de Daldis|Ibn Sirin|Diário de sonhos|Terror noturno|Onirocrítica|Jogo do bicho",
 "pl": "Sen|Sennik|Marzenie senne|Sen jasny|Koszmar senny|Paraliż przysenny|Objaśnianie marzeń sennych|Oneiromancja|Interpretacja snów|Sny|Koszmar|Marzenia senne|Artemidor z Daldis|Ibn Sirin|Sennik egipski|Oneirologia",
 "el": "Όνειρο|Ονειροκρίτης|Ονειρομαντεία|Διαυγές όνειρο|Εφιάλτης|Παράλυση ύπνου|Η ερμηνεία των ονείρων|Ονειροκριτική|Ονειροκριτικά|Ονειρολογία|Ερμηνεία των ονείρων|Αρτεμίδωρος|Αρτεμίδωρος ο Δαλδιανός|Όνειρα|Νυχτερινός τρόμος",
 "la": "Somnium|Oneirocritica|Artemidorus|Somnia|Somnus|Oneirologia|Somnium Scipionis|Artemidorus Daldianus|Insomnium|Oneiromantia|Ibn Sirin",
 "bn": "স্বপ্ন|দুঃস্বপ্ন|স্বপ্নব্যাখ্যা|ঘুমের পক্ষাঘাত|স্বপ্নের ব্যাখ্যা|সুস্বপ্ন|স্বপ্ন বিজ্ঞান|ইবনে সিরিন|খোয়াব|স্বপ্নতত্ত্ব|স্বপ্নফল|স্বপ্ন ব্যাখ্যা|স্বপ্নদোষ",
 "sw": "Ndoto|Ndoto mbaya|Tafsiri ya ndoto|Ndoto za mchana|Kupooza usingizini|Usingizi|Ibn Sirin|Mfasiri wa ndoto|Ndoto za usiku|Ndoto ya wazi|Ndoto za kutisha|Ndoto za kinabii",
 "nl": "Droom|Droomduiding|Lucide droom|Nachtmerrie|Slaapverlamming|Oneiromantie|Droomuitleg|Droominterpretatie|Droomanalyse|Droomonderzoek|Dromen|Droomwerk|Artemidorus van Daldis|Ibn Sirin|Nachtelijke verschrikking|Droomdagboek|Lucide dromen|Oneirologie|Droomboek|Slaapparalyse",
}
LANGS = list(T)
OUT = ROOT / SOURCE
REDIR = re.compile(r"\s*#\s*[^\s\[:]+\s*:?\s*\[\[([^\]|#]+)", re.I)


def norm(s: str) -> str:
    return s.replace("_", " ").strip().casefold()


def scan_index(f: Fetcher, lang: str, targets: set[str]):
    """Stream the index (not stored); return found, end offsets, line count, last-modified."""
    url = f"{BASE}/{lang}wiki/latest/{lang}wiki-latest-pages-articles-multistream-index.txt.bz2"
    if not f.allowed(url):
        raise Blocked(url)
    f._wait("dumps.wikimedia.org")
    found: dict[str, tuple[int, int, str]] = {}
    ends: dict[int, int] = {}
    pending: list[int] = []
    st = {"last": None, "n": 0}

    def handle(parts):
        for ln in parts:
            st["n"] += 1
            try:
                off_s, id_s, title = ln.decode("utf-8").split(":", 2)
                off = int(off_s)
            except Exception:
                continue
            if off != st["last"]:
                for w in pending:
                    ends[w] = off
                pending.clear()
                st["last"] = off
            k = norm(title)
            if k in targets and k not in found:
                found[k] = (off, int(id_s), title)
                if off not in ends and off not in pending:
                    pending.append(off)

    with f.client.stream("GET", url) as r:
        if r.status_code in (401, 403, 451):
            f._block(url, f"http {r.status_code}")
            raise Blocked(str(r.status_code))
        r.raise_for_status()
        lastmod = r.headers.get("last-modified", "")
        dec = bz2.BZ2Decompressor()
        buf = b""
        for chunk in r.iter_raw(1 << 20):
            data = chunk
            while data:
                if dec.eof:
                    dec = bz2.BZ2Decompressor()
                out = dec.decompress(data)
                data = dec.unused_data if dec.eof else b""
                buf += out
                parts = buf.split(b"\n")
                buf = parts.pop()
                handle(parts)
    return found, ends, st["n"], lastmod


PAGE = re.compile(r"<page>(.*?)</page>", re.S)


def fetch_streams(f: Fetcher, lang: str, found: dict, ends: dict):
    url = f"{BASE}/{lang}wiki/latest/{lang}wiki-latest-pages-articles-multistream.xml.bz2"
    if not f.allowed(url):
        raise Blocked(url)
    by_off: dict[int, list] = {}
    for off, pid, title in found.values():
        by_off.setdefault(off, []).append((pid, title))
    pages = {}
    for off, items in sorted(by_off.items()):
        end = ends.get(off)
        rng = f"bytes={off}-{end - 1}" if end else f"bytes={off}-{off + 3_000_000}"
        f._wait("dumps.wikimedia.org")
        r = f.client.get(url, headers={"Range": rng})
        if r.status_code in (401, 403, 451):
            f._block(url, f"http {r.status_code}")
            raise Blocked(str(r.status_code))
        if r.status_code != 206:
            print(lang, "range not honoured", r.status_code)
            continue
        try:
            xml = bz2.BZ2Decompressor().decompress(r.content).decode("utf-8", "replace")
        except Exception as e:
            print(lang, off, "decode fail", e)
            continue
        want = dict(items)
        for m in PAGE.finditer(xml):
            blk = m.group(1)
            pid = int(re.search(r"<id>(\d+)</id>", blk).group(1))
            if pid in want:
                tx = re.search(r"<text[^>]*>(.*?)</text>", blk, re.S)
                rev = re.search(r"<revision>.*?<id>(\d+)</id>.*?<timestamp>([^<]+)</timestamp>", blk, re.S)
                pages[pid] = {"title": want[pid], "text": unescape(tx.group(1)) if tx else "",
                              "rev": rev.group(1) if rev else "", "ts": rev.group(2) if rev else ""}
    return pages


def main() -> None:
    langs = sys.argv[1:] or LANGS
    OUT.mkdir(parents=True, exist_ok=True)
    f = Fetcher(Meta(SOURCE, license="CC BY-SA 4.0", rights_holder="Wikipedia contributors (Wikimedia Foundation)",
                     tradition="encyclopedic"), delay=2.0, timeout=300)
    statp = OUT / "status.json"
    status = json.loads(statp.read_text(encoding="utf-8")) if statp.exists() else {}

    def save():
        statp.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")

    for lang in langs:
        if status.get(lang, {}).get("done"):
            continue
        targets = {norm(t) for t in T[lang].split("|")}
        pages: dict = {}
        n, lastmod = 0, ""
        try:
            for _ in range(3):
                found, ends, n, lastmod = scan_index(f, lang, targets)
                new = fetch_streams(f, lang, found, ends)
                pages.update(new)
                have = {norm(x["title"]) for x in pages.values()}
                targets = set()
                for p in new.values():
                    m = REDIR.match(p["text"]) if p["text"].lstrip().startswith("#") else None
                    if m and norm(m.group(1)) not in have:
                        targets.add(norm(m.group(1)))
                if not targets:
                    break
        except Blocked as e:
            status[lang] = {"done": True, "blocked": str(e)}
            save()
            continue
        except Exception as e:
            print(lang, "error", type(e).__name__, e, flush=True)
            status[lang] = {"error": f"{type(e).__name__}: {e}"}
            save()
            continue
        (OUT / "files" / lang).mkdir(parents=True, exist_ok=True)
        for pid, p in pages.items():
            body = p["text"].encode("utf-8")
            rel = f"files/{lang}/{pid}.wiki"
            (OUT / rel).write_bytes(body)
            row = {"url": f"https://{lang}.wikipedia.org/wiki/{p['title'].replace(' ', '_')}",
                   "source_dump": f"{BASE}/{lang}wiki/latest/", "page_id": pid, "title": p["title"],
                   "revision": p["rev"], "revision_ts": p["ts"], "dump_last_modified": lastmod,
                   "fetched_at": datetime.now(timezone.utc).isoformat(),
                   "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "path": rel, "lang": lang,
                   "source": SOURCE, "license": "CC BY-SA 4.0", "rights_holder": "Wikipedia contributors",
                   "tradition": "encyclopedic"}
            with f.manifest.open("a", encoding="utf-8") as mf:
                mf.write(json.dumps(row, ensure_ascii=False) + "\n")
        status[lang] = {"done": True, "index_lines": n, "pages": len(pages),
                        "titles": sorted(p["title"] for p in pages.values())}
        save()
        print(lang, "index", n, "pages", len(pages), flush=True)


if __name__ == "__main__":
    main()
