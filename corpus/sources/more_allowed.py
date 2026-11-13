"""Robots-allowed dream dictionaries (RU, ES, PT-BR, DE, FA, UR, VI) not crawled before.

One module, one raw folder per site (see SITES). Builds on dreamnum_common.Runner:
every request goes through corpus.fetch.Fetcher, fetched pages are re-read from
disk on rerun, and entries.jsonl is rewritten from the saved files every 300
pages (so a long crawl always leaves a usable file).

Run: backend/.venv/Scripts/python -m corpus.sources.more_allowed <source> [--fetch-only]
primbon-com is a search-snowball (the site only exposes ?mimpi=<word>&submit=1).
"""

from __future__ import annotations

import html as htmlmod
import json
import re
import sys
import time
from urllib.parse import unquote, urljoin, urlparse

from corpus.fetch import ROOT, Blocked, Fetcher, Meta, write_entries
from corpus.sources.dreamnum_common import (
    Runner, Site, author_in, blocks, clean, decode, first, h1, log, region,
)

NUM_HEAD = r"(?i)เลข|رقم|numer|n[uú]mero|palpite|jogo do bicho|sorte|lott?er|lotería|số|bộ số|cặp số|lô đề"


# ------------------------------------------------------------------ generic

def generic(url: str, html: str, *, sym_re: str = "", sym_from_title: bool = False, stop_re: str = r"$^",
            skip_head: str = r"$^", min_len: int = 40, numbers: bool = False, author_head: str = "",
            numbered: bool = False, require_h1: str = "", head_tags=("h2", "h3", "h4", "h5"),
            drop_re: str = r"$^") -> list[dict]:
    bl = blocks(html)
    start = next((i for i, b in enumerate(bl) if b[0] == "h1"), -1)
    title = bl[start][1] if start >= 0 else ""
    if sym_from_title or not title:
        title = first(r"<title[^>]*>(.*?)</title>", html) or title
    if require_h1 and not re.search(require_h1, title):
        return []
    sym = re.sub(sym_re, "", title).strip(" -–|:") if sym_re else title
    sym = re.split(r"\s+[|–-]\s+|:\s", sym)[0].strip()
    if not sym:
        return []
    rows: list[dict] = []
    head, buf = "", []

    def flush():
        nonlocal buf
        txt = "\n".join(buf).strip()
        buf = []
        if not txt or re.search(skip_head, head or "-"):
            return
        row = {"symbol_raw": sym, "condition": head, "meaning": txt, "locator": head or "intro"}
        if author_head:
            m = re.search(author_head, head)
            if m:
                row["attributed_author"] = clean(m.group(1))
            else:
                a = author_in(head)
                if a:
                    row["attributed_author"] = a
        if numbers and re.search(NUM_HEAD, head):
            ns = re.findall(r"(?<!\d)\d{1,4}(?!\d)", txt)
            if ns:
                row["numbers"] = ns[:40]
                row["domain"] = "lottery-numbers"
        rows.append(row)

    for tag, t, lead in bl[start + 1:] if start >= 0 else bl[1:]:
        if re.search(stop_re, t):
            break
        if tag in head_tags:
            flush()
            head = re.sub(r"[▼▶►▲]", "", t).strip()
            continue
        if re.search(drop_re, t):
            continue
        if tag in ("p", "li", "div", "br", "td", "blockquote") and len(t) >= min_len:
            if numbered:
                m = re.match(r"^\d{1,2}[.)]\s*([^:]{4,160}):\s+(.{20,})", t)
                if m:
                    flush()
                    rows.append({"symbol_raw": sym, "condition": m.group(1).strip(), "meaning": m.group(2).strip(),
                                 "locator": head or "list"})
                    continue
            buf.append(t)
    flush()
    return rows


def with_opts(**kw):
    return lambda url, html: generic(url, html, **kw)


# --------------------------------------------------------------- astromeridian

AUTH = (r"(?:сонник[а-я]*|соннику|толкователю(?:\s+снов)?|толкованию)\s+(?:по\s+)?"
        r"((?:[А-ЯЁ]\.\s?){0,2}[А-ЯЁ][а-яё\-]+(?:\s+[А-ЯЁ][а-яё\-]+)?)")


def parse_astro(url: str, html: str) -> list[dict]:
    rows = generic(url, html, sym_re=r"^К чему (?:снится|снятся|снилась|снился)\s*", stop_re=r"^(Автор:|Добавить комментарий|Добавить свой сон)",
                   min_len=3, author_head=AUTH, drop_re=r"^(Сонник толкование снов по|Сборник сонников)")
    for r in rows:
        a = r.get("attributed_author", "")
        if a and a.lower() in ("снов", "сонника", "снится", "астромеридиана") and a.lower() != "астромеридиана":
            r.pop("attributed_author")
        if not r.get("attributed_author") and "сонн" in r["locator"].lower():
            r["attributed_author"] = r["locator"]
        r["meaning"] = re.sub(r"^[👍👎\s]+", "", r["meaning"])
    return rows


# --------------------------------------------------------------------- felomena

def parse_felomena(url: str, html: str) -> list[dict]:
    bl = blocks(html)
    sym = ""
    for tag, t, _ in bl:
        if tag == "h2" and t.startswith("Сонник "):
            sym = t[len("Сонник "):].strip()
            break
    if not sym:
        m = re.search(r"Сонник\s+(.+?)\s+(?:приснил|снится)", h1(html))
        sym = m.group(1) if m else ""
    if not sym:
        return []
    rows, head, buf = [], "", []

    def flush():
        nonlocal buf
        txt = "\n".join(buf).strip()
        buf = []
        if txt:
            rows.append({"symbol_raw": sym, "condition": head, "meaning": txt, "locator": head or "intro",
                         "attributed_author": "Феломена (site)"})

    seen_h1 = False
    for tag, t, _ in bl:
        if tag == "h1":
            seen_h1 = True
            continue
        if not seen_h1:
            continue
        if re.search(r"^(Комментарии|Оставить комментарий|Читайте также|Добавить комментарий)", t):
            break
        if tag in ("h2", "h3"):
            flush()
            head = re.sub(r"[▼▶►▲]", "", t).strip()
        elif tag in ("p", "li") and len(t) >= 40:
            buf.append(t)
    flush()
    return rows


# ------------------------------------------------------------------ euroresidentes

def parse_euro(url: str, html: str) -> list[dict]:
    if "diccionario_significado_de" in url:
        return generic(url, html, sym_re=r"^Significado de\s+(?:Soñar\s+con\s+)?", stop_re=r"^(Comentarios|Deja tu comentario|Sueños relacionados)",
                       min_len=25, skip_head=r"(?i)relacionad|comentari", head_tags=("h2", "h3", "h4"))
    # letter page: h3 headword followed by a short meaning paragraph
    rows, cur, buf = [], "", []
    for tag, t, _ in blocks(html):
        if tag == "h3":
            if cur and buf:
                rows.append({"symbol_raw": cur, "condition": "", "meaning": " ".join(buf), "locator": "indice letra"})
            cur, buf = t, []
        elif tag == "p" and cur and len(t) > 30 and not t.startswith(("Para ver", "Ver más")):
            buf.append(t)
    if cur and buf:
        rows.append({"symbol_raw": cur, "condition": "", "meaning": " ".join(buf), "locator": "indice letra"})
    return [r for r in rows if not r["symbol_raw"].startswith("Interpretación")]


# ------------------------------------------------------------------ beytoote (fa)

AD = r"تخفیف|OFF|پرفروش|%|اقساطی|خرید|کلیک"


def parse_beytoote(url: str, html: str) -> list[dict]:
    bl = blocks(html)
    last_h1 = max((i for i, b in enumerate(bl) if b[0] == "h1"), default=-1)
    if last_h1 < 0:
        return []
    sym = bl[last_h1][1]
    if sym == "تعبیر خواب":
        sym = re.sub(r"^تعبیر خواب\s*", "", first(r"<title[^>]*>(.*?)</title>", html))
    ps = []
    for tag, t, _ in bl[last_h1 + 1:]:
        if tag == "p":
            if re.search(AD, t) and len(t) < 90:
                break
            ps.append(t)
        elif tag == "h3" and ps:
            break
    if not ps or not sym:
        return []
    return [{"symbol_raw": sym, "condition": "", "meaning": "\n".join(ps), "locator": "madde"}]


# ---------------------------------------------------------------- tables (vi)

def parse_vi_table(url: str, html: str) -> list[dict]:
    rows = []
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", html):
        tds = [clean(re.sub(r"(?s)<[^>]+>", " ", x)) for x in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
        tds = [t for t in tds if t != ""]
        if len(tds) >= 3 and tds[0].isdigit():
            ns = re.findall(r"\d{1,3}", tds[2])
            if ns:
                rows.append({"symbol_raw": tds[1], "condition": "", "meaning": tds[2], "numbers": ns,
                             "domain": "lottery-numbers", "locator": f"stt {tds[0]}"})
    return rows


def parse_ngaydep(url: str, html: str) -> list[dict]:
    if "trung-so" in url:
        return parse_vi_table(url, html)
    return generic(url, html, numbered=True, min_len=30, stop_re=r"^(Xem thêm|🔗)", skip_head=r"(?i)xem thêm|các số")


# --------------------------------------------------------------------- tabeerinfo

def parse_tabeer(url: str, html: str) -> list[dict]:
    i = html.find("entry-content entry")
    if i < 0:
        return []
    j = min([x for x in (html.find("post-bottom-meta", i), html.find("<!-- .entry-content", i)) if x > 0] or [len(html)])
    body = re.sub(r"(?is)<(script|style|ins|noscript)[^>]*>.*?</>", " ", html[i:j])
    paras = [clean(re.sub(r"(?s)<[^>]+>", " ", x)) for x in re.findall(r"(?is)<p[^>]*>(.*?)</p>", body)]
    paras = [p for p in paras if p]
    title = h1(html)
    if not paras:
        return []
    if len(paras) >= 2:
        sym = paras[0].strip(" :.۔")
        mean = chr(10).join(paras[1:])
    else:
        sym, mean = title, paras[0]
    return [{"symbol_raw": sym, "condition": "", "meaning": mean, "locator": title}]


# ------------------------------------------------------------------- dawateislami

def parse_dawat(url: str, html: str) -> list[dict]:
    t = generic(url, html, min_len=60)
    pg = re.search(r"page-(\d+)", url)
    for r in t:
        r["locator"] = f"page {pg.group(1)}" if pg else "book"
    return t


def parse_sennik(url: str, html: str) -> list[dict]:
    slug = unquote(urlparse(url).path).rsplit("/", 1)[-1].replace(".html", "")
    sym = re.sub(r"^sennik-", "", slug).replace("-", " ")
    rows = generic(url, html, min_len=40, stop_re=r"^(Komentarz|Zostaw|Podobne|Zobacz też|Powiązane)",
                   skip_head=r"(?i)spis treści|komentarz|podobne|zobacz też|powiązane")
    for r in rows:
        r["symbol_raw"] = sym
    return rows


# ------------------------------------------------------------------------ sites

RU = "russian-sonniki"
SITES: dict[str, Site] = {
    "astromeridian-ru": Site(
        source="astromeridian-ru", tradition=RU, language="ru", delay=1.0, max_pages=12000,
        rights_holder="Astromeridian.ru (operator per site imprint; per-author sections are the site's own compilations)",
        sitemaps=["https://www.astromeridian.ru/sonnik/sitemap.xml", "https://www.astromeridian.ru/sonnik/2/sitemap.xml",
                  "https://www.astromeridian.ru/sonnik/site_map_2.xml"],
        url_re=r"astromeridian\.ru/sonnik/.+\.html$", parse=parse_astro),
    "felomena-com": Site(
        source="felomena-com", tradition=RU, language="ru", delay=3.0, max_pages=3000, max_listing=80,
        rights_holder="Felomena.com (operator per site imprint)",
        seeds=["https://felomena.com/sonnik/a/"], follow_re=r"felomena\.com/sonnik/[a-z]{1,3}/$",
        url_re=r"felomena\.com/sonnik/[a-z]{1,3}/[^/?]+/$", url_exclude=r"\?|/test-|avtogen-old", parse=parse_felomena),
    "euroresidentes-com": Site(
        source="euroresidentes-com", tradition="spanish-popular", language="es", delay=1.5, max_pages=6000,
        rights_holder="Euroresidentes (euroresidentes.com, operator per site imprint)",
        seeds=["https://www.euroresidentes.com/suenos/"], follow_re=r"euroresidentes\.com/suenos/diccionario[^/]*\.htm$",
        url_re=r"euroresidentes\.com/suenos/(diccionario_significado_de/.+\.htm|diccionario[^/]*\.htm)$", parse=parse_euro,
        max_listing=60),
    "sonhos-com-br": Site(
        source="sonhos-com-br", tradition="brazilian-popular", language="pt", delay=1.5, max_pages=2500,
        rights_holder="Sonhos.com.br (operator per site imprint)",
        sitemaps=["https://www.sonhos.com.br/sitemap.xml"], url_re=r"sonhos\.com\.br/sonhar-[^/]+$",
        parse=with_opts(sym_re=r"(?i)^(sonhar|sonhos?)\s+(com\s+|que\s+)?", numbers=True,
                        stop_re=r"^(Sonhos relacionados|Comentários|Deixe seu coment)", drop_re=r"^(Publicidade|Revisado por|Resposta rápida|Em resumo)",
                        skip_head=r"(?i)coment|relacionad|instagram|buscar|publicidade")),
    "bichosnews-com": Site(
        source="bichosnews-com", tradition="brazilian-popular", language="pt", delay=1.5, max_pages=1500,
        rights_holder="BichosNews (bichosnews.com, operator per site imprint)",
        sitemaps=["https://www.bichosnews.com/sitemap_index.xml"], sitemap_child_re=r"post-sitemap",
        url_re=r"bichosnews\.com/(sonhar|sonho|sonhos)[^/]*/$",
        parse=with_opts(sym_re=r"(?i)^(sonhar|sonhos?)\s+(com\s+|que\s+)?", numbers=True, skip_head=r"(?i)^(menu|resumo|conteúdo)",
                        stop_re=r"^(Veja também|Leia também|Deixe seu coment|Posts relacionados)")),
    "traumdeutung-de": Site(
        source="traumdeutung-de", tradition="german-popular", language="de", delay=1.5, max_pages=11000,
        rights_holder="Traumdeutung.de (operator per site imprint)",
        sitemaps=["https://www.traumdeutung.de/sitemap_index.xml"], sitemap_child_re=r"lexikon-sitemap",
        url_re=r"traumdeutung\.de/lexikon/[^/]+/$",
        parse=with_opts(sym_from_title=True, sym_re=r"(?i)^Bedeutung Traumsymbol\s+|\s*-?\s*Traumdeutung\.de.*$", min_len=30,
                        stop_re=r"^(Kommentar|Ähnliche|Weitere Traum|Was bedeutet)")),
    "traum-deutung-de": Site(
        source="traum-deutung-de", tradition="german-popular", language="de", delay=1.5, max_pages=4000,
        rights_holder="Traum-Deutung.de (operator per site imprint)",
        sitemaps=["https://traum-deutung.de/sitemap_index.xml"], sitemap_child_re=r"post-sitemap",
        url_re=r"traum-deutung\.de/[^/?]+/$", url_exclude=r"/(impressum|datenschutz|kontakt|thema|category)/",
        parse=with_opts(sym_re=r"^Traumdeutung\s*", require_h1=r"^Traumdeutung\s", min_len=30,
                        stop_re=r"^(Vielen Dank|Diese Traumsymbole)", skip_head=r"(?i)inhaltsverzeichnis|feedback")),
    "beytoote-com": Site(
        source="beytoote-com", tradition="persian-popular", language="fa", delay=1.5, max_pages=6000, max_listing=80,
        rights_holder="Beytoote.com (operator per site imprint)",
        seeds=["https://www.beytoote.com/sleep/"], follow_re=r"beytoote\.com/sleep/construe\d+$",
        url_re=r"beytoote\.com/sleep/(construe\d+|dream-interpretation-[^/]+)\.html$", url_exclude=r"\?", parse=parse_beytoote),
    "setare-com": Site(
        source="setare-com", tradition="persian-popular", language="fa", delay=1.5, max_pages=6000, max_listing=300,
        rights_holder="Setare.com (operator per site imprint)",
        seeds=["https://setare.com/fa/news/10875/%d8%aa%d8%b9%d8%a8%db%8c%d8%b1-%d8%ae%d9%88%d8%a7%d8%a8-%d8%aa%d8%b9%d8%a8%db%8c%d8%b1-%d8%ae%d9%88%d8%a7%d8%a8-%d8%b4%d9%85%d8%a7-%da%86%db%8c%d8%b3%d8%aa/"],
        follow_re=r"setare\.com/c/17/\d+/(page/\d+/)?$",
        url_re=r"setare\.com/fa/news/\d+/تعبیر-خواب",
        parse=with_opts(sym_re=r"^تعبیر خواب\s*", min_len=30, stop_re=r"^(نظرات|دیدگاه|مطالب مرتبط)")),
    "tabeerinfo-com": Site(
        source="tabeerinfo-com", tradition="urdu-popular", language="ur", delay=1.0, max_pages=7000,
        rights_holder="TabeerInfo (tabeerinfo.com, operator per site imprint)",
        sitemaps=["https://tabeerinfo.com/sitemap_index.xml"], sitemap_child_re=r"post-sitemap",
        url_re=r"tabeerinfo\.com/khwab-mein-[^/]+-tabeer/$",
        parse=parse_tabeer),
    "niksalehi-com": Site(
        source="niksalehi-com", tradition="persian-popular", language="fa", delay=2.0,
        rights_holder="Niksalehi.com (operator per site imprint)",
        extra_urls=["https://www.niksalehi.com/%D8%AA%D8%B9%D8%A8%DB%8C%D8%B1-%D8%AE%D9%88%D8%A7%D8%A8"],
        parse=with_opts(sym_re=r"^$", min_len=30)),
    "dawateislami-net": Site(
        source="dawateislami-net", tradition="urdu-religious", language="ur", delay=2.0,
        rights_holder="Dawat-e-Islami (dawateislami.net)",
        sitemaps=["https://www.dawateislami.net/sitemap-books-urdu1.xml"], url_re=r"bookslibrary/ur/khwab-ki-tabeer-kon-bayan",
        parse=parse_dawat),
    "ngaydep-com": Site(
        source="ngaydep-com", tradition="vietnamese-popular", language="vi", delay=1.5, max_pages=3000, max_listing=40,
        rights_holder="NgayDep.com (operator per site imprint)",
        seeds=["https://ngaydep.com/giai-ma-giac-mo.html", "https://ngaydep.com/giai-ma-giac-mo-trung-so.html"],
        url_re=r"ngaydep\.com/[^?]*-m\d+\.html$|ngaydep\.com/giai-ma-giac-mo-trung-so\.html$",
        extra_urls=["https://ngaydep.com/giai-ma-giac-mo-trung-so.html"], parse=parse_ngaydep),
    "lichngaytot-com": Site(
        source="lichngaytot-com", tradition="vietnamese-popular", language="vi", delay=1.5, max_pages=1500, max_listing=150,
        rights_holder="LichNgayTot.com (operator per site imprint)",
        seeds=["https://lichngaytot.com/giai-ma-giac-mo.html"],
        follow_re=r"lichngaytot\.com/(giai-ma-giac-mo-p\d+|giac-mo-[a-z\-]+-c\d+-p\d+|giai-ma-giac-mo-c\d+-p\d+)\.html$",
        url_re=r"lichngaytot\.com/(giac-mo|giai-ma-giac-mo)/[^/]+\.html$",
        parse=with_opts(numbered=True, min_len=40, stop_re=r"^(Tin cùng chuyên mục|Xem thêm)")),
    "sennik-info": Site(
        source="sennik-info", tradition="polish-popular", language="pl", delay=1.5, max_pages=4000,
        rights_holder="sennik.info (operator per site imprint)",
        sitemaps=["https://www.sennik.info/sitemap_index.xml"], sitemap_child_re=r"post-sitemap",
        url_re=r"sennik\.info/sennik-[^/]+\.html$", parse=parse_sennik),
    "capsulaa-sa": Site(
        source="capsulaa-sa", tradition="arabic-popular", language="ar", delay=1.5, max_pages=3500, max_listing=260,
        rights_holder="Capsulaa / Kapsula (capsulaa.sa, operator per site imprint)",
        seeds=["https://www.capsulaa.sa/dreams/"], follow_re=r"capsulaa\.sa/dreams/\?page=\d+$",
        url_re=r"capsulaa\.sa/dreams/تفسير",
        parse=with_opts(sym_re=r"^تفسير (?:رؤية )?(?:حلم |الحلم )?", min_len=40, numbers=False,
                        stop_re=r"^(✨ أداة|اكتب ما حلمت)", skip_head=r"وصل للتفسير")),
    "onirokritis-gr": Site(
        source="onirokritis-gr", tradition="greek-popular", language="el", delay=2.0,
        rights_holder="onirokritis.gr (operator per site imprint)",
        extra_urls=[f"https://onirokritis.gr/{p}/" for p in (
            "oneira-zoa", "oneira-oikogeneia", "oneira-ergasia", "oneira-fagito", "oneira-rouxa", "oneira-taxidi",
            "oneira-gamos", "oneira-fovos", "oneira-entoma", "oneira-thalassa", "oneira-dentra-fyta", "oneira-xromata",
            "oneira-kosmimata", "diafora-oneira")],
        parse=with_opts(sym_re=r"^$", min_len=40)),
    "sanook-th": Site(
        source="sanook-th", tradition="thai-popular", language="th", delay=2.0, max_pages=600, max_listing=6,
        rights_holder="Sanook.com (Tencent / operator per site imprint)",
        seeds=["https://www.sanook.com/horoscope/dream/",
               "https://www.sanook.com/horoscope/tag/%E0%B8%97%E0%B8%B3%E0%B8%99%E0%B8%B2%E0%B8%A2%E0%B8%9D%E0%B8%B1%E0%B8%99%E0%B9%80%E0%B8%A5%E0%B8%82%E0%B9%80%E0%B8%94%E0%B9%87%E0%B8%94/",
               "https://www.sanook.com/horoscope/tag/%E0%B8%97%E0%B8%B3%E0%B8%99%E0%B8%B2%E0%B8%A2%E0%B8%9D%E0%B8%B1%E0%B8%99%E0%B8%95%E0%B8%B2%E0%B8%A1%E0%B8%95%E0%B8%B1%E0%B8%A7%E0%B8%AD%E0%B8%B1%E0%B8%81%E0%B8%A9%E0%B8%A3/"],
        url_re=r"sanook\.com/horoscope/\d+/$",
        parse=with_opts(require_h1="ฝัน", min_len=40, numbers=True, sym_re=r"\s*(ทำนายฝัน|มีคำทำนายฝัน).*$")),
    "xskt-com-vn": Site(
        source="xskt-com-vn", tradition="vietnamese-popular", language="vi", delay=2.0,
        rights_holder="XSKT.com.vn (operator per site imprint)",
        extra_urls=[f"https://xskt.com.vn/so-mo/?pg={i}" for i in range(1, 7)] + ["https://xskt.com.vn/so-mo/"],
        parse=parse_vi_table),
}


# ------------------------------------------------------------------------ runner

class R(Runner):
    """Runner with percent-decoded regex matching and incremental entries.jsonl."""

    def discover(self) -> list[str]:
        s = self.site
        urls: list[str] = []
        for sm in s.sitemaps:
            for u in self.sitemap_urls(sm):
                d = unquote(u)
                if re.search(s.url_re, d) and not re.search(s.url_exclude, d):
                    urls.append(u)
        if s.seeds:
            urls += self.crawl()
        urls += s.extra_urls
        seen, out = set(), []
        for u in urls:
            u = u.split("#")[0]
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out[: s.max_pages]

    def crawl(self) -> list[str]:
        s = self.site
        queue, seen, pages, n = list(s.seeds), set(s.seeds), [], 0
        while queue and n < s.max_listing:
            u = queue.pop(0)
            n += 1
            body = self.get(u, kind="listing")
            if body is None:
                continue
            for href in re.findall(r'href=["\']?([^"\'\s>#]+)', body):
                a = urljoin(u, htmlmod.unescape(href))
                if urlparse(a).netloc.replace("www.", "") != urlparse(u).netloc.replace("www.", ""):
                    continue
                d = unquote(a)
                if a in seen or re.search(s.url_exclude, d):
                    continue
                seen.add(a)
                if s.url_re and re.search(s.url_re, d):
                    pages.append(a)
                elif s.follow_re and re.search(s.follow_re, d):
                    queue.append(a)
        log(f"crawl: {n} listing pages, {len(pages)} item pages")
        return pages

    def run(self, fetch_only: bool = False) -> None:
        s = self.site
        log(f"[{s.source}] discovering")
        urls = self.discover()
        log(f"[{s.source}] {len(urls)} pages")
        rows: list[dict] = []
        t0 = time.time()
        for i, u in enumerate(urls):
            body = self.get(u)
            if i % 100 == 0:
                log(f"[{s.source}] {i}/{len(urls)} rows={len(rows)} {int(time.time()-t0)}s")
            if body is not None and not fetch_only and s.parse:
                try:
                    rows += self.finish(s.parse(u, body), u)
                except Exception as e:
                    log("PARSE ERR", u, repr(e)[:200])
            if i % 300 == 299 and not fetch_only:
                self.write(rows)
        if not fetch_only:
            self.write(rows)
        log(f"[{s.source}] done pages={len(urls)} blocked={self.blocked_n} errors={self.errors}")


# ------------------------------------------------------------------------ primbon

def primbon() -> None:
    src = "primbon-com"
    meta = Meta(source=src, license="unknown (all rights reserved assumed)",
                rights_holder="Primbon.com (operator per site imprint)", tradition="javanese-indonesian-primbon")
    f = Fetcher(meta, delay=1.0)
    found: dict[str, str] = {}
    queue = ["ular", "air", "gigi", "rumah", "mati", "uang", "anak", "ikan", "api", "terbang", "jatuh", "hamil", "darah",
             "laut", "pohon", "bunga", "kucing", "anjing", "burung", "emas", "mobil", "orang", "melihat", "makan", "nikah"]
    done: set[str] = set()
    n = 0
    while queue and n < 3500:
        w = queue.pop(0)
        if w in done:
            continue
        done.add(w)
        n += 1
        url = f"https://primbon.com/tafsir_mimpi.php?mimpi={w}&submit=1"
        try:
            r = f.get(url, name=f"search/{w}.html")
        except Blocked as e:
            log("BLOCKED", e)
            return
        except Exception as e:
            log("ERR", w, repr(e)[:100])
            continue
        body = decode(r.content, r.encoding)
        for m in re.finditer(r'<div class="tm-result-title">(.*?)</div><div class="tm-result-meaning">(.*?)</div>', body, re.S):
            title = clean(re.sub(r"<[^>]+>", "", m.group(1)))
            mean = clean(re.sub(r"<[^>]+>", "", m.group(2)))
            if title and title not in found:
                found[title] = mean
                for tok in re.findall(r"[a-z]{3,}", title.lower()):
                    if tok not in done and tok not in ("mimpi", "yang", "dan", "dengan", "akan"):
                        queue.append(tok)
        if n % 50 == 0:
            log(f"[primbon] queries={n} queue={len(queue)} titles={len(found)}")
            _write_primbon(src, found)
    _write_primbon(src, found)
    log(f"[primbon] done queries={n} titles={len(found)}")


def _write_primbon(src: str, found: dict[str, str]) -> None:
    p = ROOT / src / "entries.jsonl"
    if p.exists():
        p.unlink()
    rows = [{"source": src, "tradition": "javanese-indonesian-primbon", "language": "id", "symbol_raw": t,
             "condition": "", "meaning": m, "polarity": "bilinmiyor", "domain": "", "url": "https://primbon.com/tafsir_mimpi.htm",
             "locator": "tafsir_mimpi.php?mimpi= (search result)", "license": "unknown (all rights reserved assumed)",
             "rights_holder": "Primbon.com (operator per site imprint)", "attributed_author": ""} for t, m in found.items()]
    write_entries(src, rows)


# ------------------------------------------------------------------------ notes

INFO = {
    "primbon-com": "Primbon.com tafsir mimpi; yalniz ?mimpi=<kelime>&submit=1 arama sonucu (en fazla 30 sonuc). Arama sozcukleri sonuc basliklarindan kartopu ile genisletildi; site 1.246 madde diyor.",
    "astromeridian-ru": "Astromeridian sonnik: sitemap 3 dosya (sonnik/sitemap.xml, sonnik/2/sitemap.xml, sonnik/site_map_2.xml). Yazar bolumleri (Miller, Tsvetkov, Dillon...) h2 basligindan attributed_author'a, ham baslik locator'a yazildi. 'Muravyova Lyudmila' editor imzali metinlerin buyuk kismi LLM uretimi gorunumunde; Miller/Tsvetkov atiflari sitenin kendi beyanidir, dogrulanmadi.",
    "felomena-com": "Felomena sonnik /sonnik/<harf>/<slug>/; harf indekslerinden kesif. Sayfalar 270 KB, bu yuzden sayfa ustu 3000. Yazar-ozel sonnikler (/sonnik/millera/ vb.) henuz taranmadi.",
    "euroresidentes-com": "Euroresidentes suenos sozlugu: harf indeks sayfalari (kisa anlam) + az sayida ayrintili madde.",
    "sonhos-com-br": "Sonhos.com.br 'sonhar-com-*' maddeleri. Sayilar varsa 'numbers' (sayi/jogo do bicho basligi altinda).",
    "bichosnews-com": "BichosNews sonhar-com yazilari; 'numero da sorte' bolumlerindeki sayilar 'numbers' alaninda (jogo do bicho hayvan eslemesi acik bir tablo olarak bulunmadi).",
    "traumdeutung-de": "Traumdeutung.de /lexikon/<sembol>/ (9.8k madde). robots.txt yalniz sponsoren.php yollarini kapatiyor.",
    "traum-deutung-de": "Traum-Deutung.de sembol yazilari (post-sitemap). robots.txt yalniz GPTBot'u engelliyor; bizim ajan ve ClaudeBot serbest.",
    "beytoote-com": "Beytoote /sleep/ tabir sozlugu (Farsca, harf indeks -> madde; Ibn Sirin tarzi klasik metinler).",
    "setare-com": "Setare.com 'tabir-e khab' kategorisi (/c/17/...), harf sayfalari ve alt maddeler.",
    "tabeerinfo-com": "TabeerInfo (Urduca, Roman Urdu URL). Cok sayida sayfada tabir metni resim icinde; metin yoksa satir uretilmez.",
    "niksalehi-com": "Niksalehi: yalniz tek bir 'tabir khab' makalesi bulundu (sozluk yok); 1 sayfa.",
    "ngaydep-com": "NgayDep giai-ma-giac-mo: ana sayfadan erisilen ~23 makale + 'so mo' tablosu (1100+ ruya -> sayi cifti, numbers).",
    "lichngaytot-com": "LichNgayTot 'giai ma giac mo' haber/makale bolumu (kategori sayfalarindan kesif).",
    "xskt-com-vn": "XSKT so-mo tablosu (6 sayfa; ruya -> lo de sayi ciftleri, numbers).",
    "sennik-info": "Sennik.info (Lehce) 'sennik-*.html' maddeleri, 3 post-sitemap. Metinler LLM/SEO tarzi. Sembol, URL slug'indan.",
    "capsulaa-sa": "Capsulaa.sa /dreams/ (Arapca, ?page=1..249 listeleme).",
    "onirokritis-gr": "onirokritis.gr (Yunanca): harf indeksi statik liste icermiyor; yalniz kategori sayfalari (14).",
    "sanook-th": "Sanook horoscope/dream (Tayca): dream ve iki tag sayfasindan erisilen ~50 makale; 'เลข' basliklari numbers'a.",
}
SKIPPED = {
    "sonmir-ru": "sonmir.ru bir casino/bahis spam sayfasina donusmus (tek sayfa), sozluk yok. Atlandi.",
    "xoso-me": "xoso.me TLS sertifika dogrulamasi basarisiz (SSL hatasi); asilmadi, atlandi.",
    "namnak-com": "namnak.com robots serbest ama kolay bulunur ruya sozlugu bolumu yok (sitemap ~27k makale, yalniz tekil 'dream-interpretation' yazilari). Atlandi.",
    "patrika-astrosage-astroyogi": "patrika.com, astrosage.com, hindi.astroyogi.com: robots serbest ancak 'swapna phal' sozluk bolumu bulunamadi (astroyogi'de sitemap'te yalniz ~16 blog yazisi, sozluk degil; astrosage sitemap yok, tahmin edilen yollar 404). Atlandi.",
    "dawateislami-net": "dawateislami.net: ruya sozlugu degil, 'Khwab ki tabeer kon bayan kar sakta hai' adli kucuk kitapcik (29 sayfa) ve kitap kutuphanesi. Atlandi.",
    "sennik-pl": "sennik.pl ve sennik-24.pl robots.txt ile bizi engelliyor; gorusulecekler listesine: sennik.pl, sennik-24.pl. senniki.pl TLS hatasi.",
}


def notes() -> None:
    for src, info in INFO.items():
        d = ROOT / src
        if not d.exists():
            continue
        files = list((d / "files").rglob("*")) if (d / "files").exists() else []
        files = [f for f in files if f.is_file()]
        mb = sum(f.stat().st_size for f in files) / 1e6
        ent = d / "entries.jsonl"
        n = sum(1 for _ in ent.open(encoding="utf-8")) if ent.exists() else 0
        blocked = d / "blocked.jsonl"
        nb = sum(1 for _ in blocked.open(encoding="utf-8")) if blocked.exists() else 0
        lic = rights = ""
        if src in SITES:
            lic, rights = SITES[src].license, SITES[src].rights_holder
        else:
            lic, rights = "unknown (all rights reserved assumed)", "Primbon.com (operator per site imprint)"
        txt = "\n".join([
            f"# {src}", "", info, "",
            f"- Dosya: {len(files)} adet, {mb:.0f} MB (files/, manifest.jsonl)",
            f"- Satir: {n} (entries.jsonl)",
            f"- Lisans: {lic}",
            f"- Hak sahibi/isletici: {rights}; imprint ve iletisim sitenin kendi sayfalarindan teyit edilmedi, gorusme icin site iletisim formu",
            f"- Engellenen/hatali istek: {nb} (blocked.jsonl)",
            "- Not: robots.txt bizim ajan ve ClaudeBot icin kontrol edildi; hicbir koruma asilmadi.", ""])
        (d / "notes.md").write_text(txt, encoding="utf-8")
    for src, info in SKIPPED.items():
        d = ROOT / src
        d.mkdir(parents=True, exist_ok=True)
        (d / "notes.md").write_text("\n".join([f"# {src}", "", "DURUM: atlandi.", "", info, ""]), encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    names = [a for a in args if not a.startswith("--")]
    if "--notes" in args:
        notes()
        sys.exit(0)
    for n in names:
        if n == "primbon-com":
            primbon()
        else:
            R(SITES[n]).run(fetch_only="--fetch-only" in args)

