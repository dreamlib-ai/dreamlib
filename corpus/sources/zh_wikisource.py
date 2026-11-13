"""Chinese Wikisource: classical dream texts (周公解夢, 夢林玄解, 周禮 占夢, 列子, 潛夫論 夢列 ...).

robots.txt disallows /w/ (so /w/api.php and action=raw) for every agent; only
rendered article pages under /wiki/ are fetched. One API probe is attempted so the
refusal is logged in blocked.jsonl.

Run: backend/.venv/Scripts/python -m corpus.sources.zh_wikisource
"""

from __future__ import annotations

import html
import json
import re
from urllib.parse import quote

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries

SOURCE = "zh-wikisource"
BASE = "https://zh.wikisource.org/wiki/"
LICENSE = "Original text public domain (PD-old); Wikisource transcription CC BY-SA 4.0"
RIGHTS = "Public domain; transcription by Wikisource contributors (Wikimedia Foundation hosts)"

# title -> (file name, role)
PAGES = {
    "周公解夢": ("zhougong-jiemeng.html", "dictionary"),
    "夢林玄解": ("menglin-xuanjie.html", "index"),
    "夢林玄解/夢林玄解叙": ("menglin-xuanjie-xu.html", "passages"),
    "夢林玄解/夢林玄解卷之首": ("menglin-xuanjie-juan-shou.html", "passages"),
    "周禮/春官宗伯": ("zhouli-chunguan.html", "zhouli"),
    "列子/周穆王篇": ("liezi-zhoumuwang.html", "liezi"),
    "莊子/齊物論": ("zhuangzi-qiwulun.html", "zhuangzi"),
    "潛夫論/卷七": ("qianfulun-juan7.html", "qianfulun"),
    "詩經/斯干": ("shijing-sigan.html", "sigan"),
    "詩經/無羊": ("shijing-wuyang.html", "wuyang"),
    "太平御覽/0397": ("taiping-yulan-0397.html", "passages"),
    "太平御覽/0398": ("taiping-yulan-0398.html", "passages"),
    "太平御覽/0399": ("taiping-yulan-0399.html", "passages"),
    "太平御覽/0400": ("taiping-yulan-0400.html", "passages"),
    "藝文類聚/卷079": ("yiwen-leiju-079.html", "passages_dream_section"),
    "酉陽雜俎/卷八": ("youyang-zazu-juan8.html", "passages_dream_section"),
}


def url_of(title: str) -> str:
    return BASE + quote(title, safe="/:")


def content_html(page: str) -> str:
    m = re.search(r'<div class="mw-content-ltr mw-parser-output"[^>]*>(.*?)<div class="printfooter"', page, re.S)
    body = m.group(1) if m else page
    body = re.sub(r'<span class="mw-editsection">.*?</span>\s*</span>', "", body, flags=re.S)
    body = re.sub(r"<style.*?</style>|<script.*?</script>", "", body, flags=re.S)
    body = re.sub(r'<sup[^>]*class="reference".*?</sup>', "", body, flags=re.S)
    return body


def strip(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).replace("\xa0", " ")


def sections(page: str) -> list[tuple[str, list[str]]]:
    """Split content into (heading, paragraphs)."""
    body = content_html(page)
    parts = re.split(r'<h[234][^>]*>(.*?)</h[234]>', body, flags=re.S)
    out: list[tuple[str, list[str]]] = []
    heading = ""
    for i, part in enumerate(parts):
        if i % 2 == 1:
            heading = strip(part).strip()
            continue
        paras = [strip(p).strip() for p in re.findall(r"<(?:p|dd|li|div class=\"poem\")[^>]*>(.*?)</(?:p|dd|li|div)>", part, re.S)]
        paras = [p for p in paras if p]
        if paras:
            out.append((heading, paras))
    return out


def polarity(text: str) -> str:
    good = any(k in text for k in ("吉", "祥", "福"))
    bad = any(k in text for k in ("凶", "禍", "災"))
    if good and bad:
        return "koşullu"
    if good:
        return "iyi"
    if bad:
        return "kötü"
    return "bilinmiyor"


def base_row(url: str, locator: str, author: str = "") -> dict:
    return {
        "source": SOURCE,
        "tradition": "Çin klasik",
        "language": "lzh",
        "url": url,
        "locator": locator,
        "license": LICENSE,
        "rights_holder": RIGHTS,
        "attributed_author": author,
    }


def parse_dictionary(page: str, url: str) -> list[dict]:
    """周公解夢: seven-character lines, separated by full-width spaces, under 27 headings."""
    rows = []
    for heading, paras in sections(page):
        if not heading:
            continue  # opening poem
        n = 0
        for para in paras:
            for line in re.split(r"[　\s]+", para):
                line = line.strip()
                if len(line) < 3 or not re.fullmatch(r"[㐀-鿿豈-﫿]+", line):
                    continue
                n += 1
                symbol, meaning, split = line, line, "none"
                idx = line.find("主", 2)
                if 2 <= idx <= len(line) - 2:
                    symbol, meaning, split = line[:idx], line[idx:], "主"
                row = base_row(url, f"{heading} #{n}", "托名周公旦 (attributed)")
                row.update(
                    symbol_raw=symbol,
                    condition="",
                    meaning=meaning,
                    line_raw=line,
                    split=split,
                    polarity=polarity(meaning),
                    domain=heading,
                )
                rows.append(row)
    return rows


def find_text(page: str, pattern: str) -> str:
    text = re.sub(r"\s+", "", "".join(p for _, ps in sections(page) for p in ps))
    m = re.search(pattern, text)
    return m.group(0) if m else ""


def typology_rows(url: str, locator: str, author: str, items: list[tuple[str, str]], context: str) -> list[dict]:
    rows = []
    for sym, meaning in items:
        row = base_row(url, locator, author)
        row.update(symbol_raw=sym, condition="", meaning=meaning, polarity="bilinmiyor",
                   domain="rüya tipi (sınıflandırma)", context_raw=context)
        rows.append(row)
    return rows


def parse_zhouli(page: str, url: str) -> list[dict]:
    ctx = find_text(page, r"占夢：掌其歲時.*?遂令始難驅疫。")
    if not ctx:
        return []
    names = re.findall(r"[一二三四五六]曰(.夢)", ctx)
    return typology_rows(url, "春官宗伯·占夢之職", "", [(n, "六夢之一") for n in names], ctx)


def parse_liezi(page: str, url: str) -> list[dict]:
    ctx = find_text(page, r"覺有八徵，夢有六候。.*?幾虛語哉？」")
    if not ctx:
        return []
    rows = typology_rows(url, "卷第三·周穆王篇", "列禦寇 (attributed)",
                         [(n, "六候之一，神所交也") for n in re.findall(r"[一二三四五六]曰(.夢)", ctx)], ctx)
    # physiological cause -> dream content pairs stated in the same passage
    pairs = [
        ("陰氣壯", "夢涉大水而恐懼"), ("陽氣壯", "夢涉大火而燔焫"), ("陰陽俱壯", "夢生殺"),
        ("甚飽", "夢與"), ("甚饑", "夢取"), ("以浮虛爲疾者", "夢揚"), ("以沈實爲疾者", "夢溺"),
        ("藉帶而寢", "夢蛇"), ("飛鳥銜髮", "夢飛"), ("將陰", "夢火"), ("將疾", "夢食"),
        ("飲酒者", "憂"), ("歌儛者", "哭"),
    ]
    for cond, dream in pairs:
        m = re.search(re.escape(cond) + r"[，則]*" + re.escape(dream), ctx)
        if not m:
            continue
        row = base_row(url, "卷第三·周穆王篇", "列禦寇 (attributed)")
        if cond in ("飲酒者", "歌儛者"):
            # 飲酒者憂，歌儛者哭: one who drinks (in a dream) grieves, one who sings/dances weeps
            row.update(symbol_raw=cond, condition="", meaning=m.group(0), polarity="kötü")
        else:
            row.update(symbol_raw=dream, condition=cond, meaning=m.group(0), polarity="bilinmiyor")
        row.update(domain="beden/neden-rüya ilişkisi", context_raw=ctx)
        rows.append(row)
    return rows


def parse_qianfulun(page: str, url: str) -> list[dict]:
    ctx = find_text(page, r"凡夢，有直、有象.*?天祿永終。")
    if not ctx:
        return []
    rows = []
    # each example ends with 此謂X之夢也
    chunks = re.split(r"(此謂.{1,3}?之夢也。)", ctx[ctx.find("在昔"):])
    for i in range(0, len(chunks) - 1, 2):
        example, label = chunks[i].strip(), chunks[i + 1]
        kind = re.match(r"此謂(.{1,3}?)之夢也", label).group(1)
        row = base_row(url, "卷七·夢列第二十八", "王符")
        row.update(symbol_raw=f"{kind}之夢", condition="", meaning=example + label, polarity="bilinmiyor",
                   domain="rüya tipi (sınıflandırma)")
        rows.append(row)
    # explicit symbol readings quoted from the Odes
    for sym, meaning in (("惟熊惟羆", "男子之祥"), ("惟虺惟蛇", "女子之祥"), ("眾惟魚矣", "實惟豐年")):
        if sym in ctx:
            row = base_row(url, "卷七·夢列第二十八", "王符")
            row.update(symbol_raw=sym, condition="", meaning=meaning, polarity="iyi", domain="象之夢 örneği")
            rows.append(row)
    for sym, meaning in (("貴人夢之", "即為祥"), ("賤人夢之", "即為妖"), ("君子夢之", "即為榮"), ("小人夢之", "即為辱")):
        if sym + meaning in ctx:
            row = base_row(url, "卷七·夢列第二十八", "王符")
            row.update(symbol_raw="(aynı rüya)", condition=sym, meaning=meaning,
                       polarity="iyi" if meaning in ("即為祥", "即為榮") else "kötü", domain="人位之夢")
            rows.append(row)
    return rows


def parse_odes(page: str, url: str, which: str) -> list[dict]:
    rows = []
    if which == "sigan":
        ctx = find_text(page, r"吉夢維何？.*?女子之祥。")
        pairs = [("維熊維羆", "男子之祥"), ("維虺維蛇", "女子之祥")]
        loc = "小雅·鴻鴈之什·斯干"
    else:
        ctx = find_text(page, r"牧人乃夢.*?室家溱溱。")
        pairs = [("衆維魚矣", "實維豐年"), ("旐維旟矣", "室家溱溱")]
        loc = "小雅·鴻鴈之什·無羊"
    for sym, meaning in pairs:
        if ctx and sym in ctx and meaning in ctx:
            row = base_row(url, loc, "")
            row.update(symbol_raw=sym, condition="大人占之", meaning=meaning, polarity="iyi",
                       domain="doğum/bereket", context_raw=ctx)
            rows.append(row)
    return rows


def passages(page: str, url: str, title: str, dream_only: bool) -> list[dict]:
    out = []
    for heading, paras in sections(page):
        if dream_only and "夢" not in heading:
            continue
        for i, p in enumerate(paras, 1):
            if dream_only or "夢" in p or not title.startswith("太平御覽"):
                out.append({"source": SOURCE, "title": title, "section": heading, "n": i, "text": p, "url": url,
                            "license": LICENSE})
    return out


def main() -> None:
    f = Fetcher(Meta(source=SOURCE, license=LICENSE, rights_holder=RIGHTS, tradition="Çin klasik"), delay=2.0)
    # Logged on purpose: the API path is disallowed by robots.txt.
    try:
        f.get("https://zh.wikisource.org/w/api.php?action=query&list=search&srsearch=%E8%A7%A3%E5%A4%A2&format=json",
              save=False)
    except Blocked:
        pass

    entries_path = ROOT / SOURCE / "entries.jsonl"
    if entries_path.exists():
        entries_path.unlink()  # rebuilt from the saved pages every run
    passage_rows: list[dict] = []
    rows: list[dict] = []
    for title, (fname, role) in PAGES.items():
        url = url_of(title)
        try:
            r = f.get(url, name=fname)
        except Blocked as e:
            print("blocked", title, e)
            continue
        except Exception as e:  # noqa: BLE001
            print("error", title, e)
            continue
        page = r.text
        got: list[dict] = []
        if role == "dictionary":
            got = parse_dictionary(page, url)
        elif role == "zhouli":
            got = parse_zhouli(page, url)
        elif role == "liezi":
            got = parse_liezi(page, url)
        elif role == "qianfulun":
            got = parse_qianfulun(page, url)
            passage_rows += passages(page, url, title, dream_only=True)
        elif role in ("sigan", "wuyang"):
            got = parse_odes(page, url, role)
        elif role == "zhuangzi":
            ctx = find_text(page, r"昔者莊周夢[為爲]胡蝶.*?此之謂物化。")
            if ctx:
                passage_rows.append({"source": SOURCE, "title": title, "section": "胡蝶夢", "n": 1, "text": ctx,
                                     "url": url, "license": LICENSE})
        elif role.startswith("passages"):
            passage_rows += passages(page, url, title, dream_only=role.endswith("dream_section"))
        rows += got
        print(f"{title}: {len(got)} entries")
    write_entries(SOURCE, rows)
    with (ROOT / SOURCE / "passages.jsonl").open("w", encoding="utf-8") as fh:
        for p in passage_rows:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    print("entries", len(rows), "passages", len(passage_rows))


if __name__ == "__main__":
    main()
