"""Shared HTML helpers for the Turkish dream-interpretation sources (stdlib only).

`main_block(html)` finds the element whose direct <p>/<h*>/<ul> children carry the
most text (a tiny readability heuristic); `sections(block)` splits it into
(heading, paragraphs) pairs on <h2>-<h5> or on paragraphs that are a single
bold run ("<p><strong>Rüyada X Görmek</strong></p>").
"""

from __future__ import annotations

import html as htmllib
import json
import re
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP = {"script", "style", "noscript", "svg", "iframe", "form", "button", "template"}
HEAD = {"h2", "h3", "h4", "h5"}
BLOCK = {"p", "ul", "ol", "blockquote"} | HEAD


class Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict, parent: "Node | None") -> None:
        self.tag, self.attrs, self.children, self.parent = tag, attrs, [], parent

    def text(self) -> str:
        out: list[str] = []
        self._text(out)
        s = "".join(out)
        s = re.sub(r"[ \t\r\f\v ]+", " ", s)
        s = re.sub(r" *\n *", "\n", s)
        s = re.sub(r" +([,.;:!?)])", r"\1", s)
        return s.strip()

    def _text(self, out: list[str]) -> None:
        for c in self.children:
            if isinstance(c, str):
                out.append(c)
            elif c.tag in SKIP:
                continue
            elif c.tag == "br":
                out.append("\n")
            else:
                if c.tag in BLOCK or c.tag in ("li", "div"):
                    out.append("\n")
                c._text(out)
                if c.tag in BLOCK or c.tag in ("li", "div"):
                    out.append("\n")

    def iter(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.iter()

    def cls(self) -> str:
        return self.attrs.get("class") or ""


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {k: (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            # implicit close of unclosed <p> etc.
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def parse(doc: str) -> Node:
    b = _Builder()
    b.feed(doc)
    b.close()
    return b.root


def find(root: Node, tag: str | None = None, cls: str | None = None, attr: tuple[str, str] | None = None) -> Node | None:
    for n in root.iter():
        if tag and n.tag != tag:
            continue
        if cls and cls not in n.cls().split():
            continue
        if attr and n.attrs.get(attr[0]) != attr[1]:
            continue
        return n
    return None


def find_all(root: Node, tag: str | None = None, cls: str | None = None) -> list[Node]:
    return [n for n in root.iter() if (not tag or n.tag == tag) and (not cls or cls in n.cls().split())]


def _iter_content(n: Node):
    yield n
    for c in n.children:
        if isinstance(c, Node) and c.tag not in SKIP and c.tag not in ("nav", "header", "footer", "aside"):
            yield from _iter_content(c)


def main_block(root: Node, min_chars: int = 200) -> Node | None:
    best, score = None, 0
    for n in _iter_content(root):
        if n.tag in ("p", "li", "a"):
            continue
        s = 0
        for c in n.children:
            if isinstance(c, Node) and c.tag in ("p", "blockquote"):
                s += len(c.text())
        if s > score:
            best, score = n, s
    return best if score >= min_chars else None


def _bold_heading(n: Node) -> str:
    """'<p><strong>Heading</strong></p>' -> 'Heading' (short, single bold run)."""
    if n.tag != "p":
        return ""
    kids = [c for c in n.children if not (isinstance(c, str) and not c.strip())]
    if len(kids) == 1 and isinstance(kids[0], Node) and kids[0].tag in ("strong", "b"):
        t = kids[0].text()
        if 3 <= len(t) <= 120 and not t.endswith((".", ",", ";")) and len(t.split()) <= 14:
            return t
    return ""


def _lead_heading(n: Node) -> tuple[str, str] | None:
    """'<p><strong>Heading</strong><br> text...</p>' -> (Heading, text)."""
    kids = [c for c in n.children if not (isinstance(c, str) and not c.strip())]
    if len(kids) >= 3 and isinstance(kids[0], Node) and kids[0].tag in ("strong", "b")             and isinstance(kids[1], Node) and kids[1].tag == "br":
        h = kids[0].text()
        if 3 <= len(h) <= 140:
            rest = Node("p", {}, None)
            rest.children = kids[2:]
            return h, rest.text()
    return None


def sections(block: Node, bold_heads: bool = True) -> list[tuple[str, str, list[str]]]:
    """-> [(heading, anchor, [paragraphs])]; heading '' for the intro."""
    out: list[tuple[str, str, list[str]]] = []
    head, anchor, buf = "", "", []

    def flush():
        paras = [p for p in buf if p]
        if paras:
            out.append((head, anchor, paras))

    def walk(children):
        nonlocal head, anchor, buf
        for c in children:
            if isinstance(c, str):
                t = c.strip()
                if len(t) > 40:
                    buf.append(re.sub(r"\s+", " ", t))
                continue
            if c.tag in SKIP or "ad" in c.cls().split() or c.tag in ("aside", "figure", "figcaption", "nav"):
                continue
            bh = _bold_heading(c) if bold_heads else ""
            if c.tag in HEAD or bh:
                flush()
                head = bh or c.text()
                anchor = c.attrs.get("id", "") if not bh else ""
                buf = []
            elif c.tag in ("p", "blockquote"):
                lead = _lead_heading(c) if bold_heads else None
                if lead:
                    flush()
                    head, anchor, buf = lead[0], "", [lead[1]]
                else:
                    buf.append(c.text())
            elif c.tag in ("ul", "ol"):
                items = [li.text() for li in c.children if isinstance(li, Node) and li.tag == "li"]
                buf.append("\n".join(i for i in items if i))
            elif c.tag in ("div", "section", "span", "article"):
                walk(c.children)

    walk(block.children)
    flush()
    return out


def jsonld(doc: str) -> list[dict]:
    out = []
    for blob in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', doc, re.S | re.I):
        try:
            data = json.loads(blob.strip())
        except ValueError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                out.append(d)
                if isinstance(d.get("@graph"), list):
                    stack.extend(d["@graph"])
            elif isinstance(d, list):
                stack.extend(d)
    return out


def meta(doc: str, prop: str) -> str:
    m = re.search(r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]+content=["\']([^"\']*)' % re.escape(prop), doc, re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']%s["\']' % re.escape(prop), doc, re.I)
    return htmllib.unescape(m.group(1)).strip() if m else ""


def h1(root: Node) -> str:
    n = find(root, "h1")
    return n.text() if n else ""


def symbol_from_title(title: str) -> str:
    """'Rüyada Geyik Görmek Ne Anlama Gelir? ...' -> 'Geyik Görmek' (site's own words, trimmed)."""
    t = re.split(r"\s+(?:ne\s+anlama\s+gelir|ne\s+demek|nedir|ne\s+anlam)|[?|:]", title, maxsplit=1, flags=re.I)[0]
    t = re.sub(r"^\s*rüyada\s+", "", t, flags=re.I)
    return t.strip(" -–,")


def row(source: str, tradition: str, symbol: str, condition: str, meaning: str, url: str, locator: str,
        license: str, rights_holder: str, **extra) -> dict:
    r = {
        "source": source, "tradition": tradition, "language": "tr", "symbol_raw": symbol,
        "condition": condition, "meaning": meaning, "polarity": "", "domain": "", "url": url,
        "locator": locator, "license": license, "rights_holder": rights_holder, "attributed_author": "",
    }
    r.update(extra)
    return r
