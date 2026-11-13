"""GRETIL (Göttingen Register of Electronic Texts in Indian Languages): Sanskrit dream texts.

Downloads TEI XML of texts that contain dream (svapna) chapters or the classic
dream passages: Atharvaveda-Pariśiṣṭa 68 Svapnādhyāya, Purāṇa svapnādhyāyas,
Caraka / Aṣṭāṅgahṛdaya / Bhāvaprakāśa dream omens, Māṇḍūkya Upaniṣad (+ Gauḍapāda),
Lalitavistara (Māyā's dream), Buddhacarita, Mahāvastu etc.

Extraction: verse-level passages to passages.jsonl. A chapter counts as a dream
chapter when many of its verses mention svapna; then every verse of it is kept,
elsewhere only verses with svapna (+/- 1 verse context). Svapnacintāmaṇi and
Suśruta are not on GRETIL. Sanskrit verses are not split into symbol entries
(that needs translation; no guessing), so entries.jsonl is not written here.
License: per TEI header (mostly CC BY-NC-SA 4.0, "provided in good faith").
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

from corpus.fetch import ROOT, Blocked, Fetcher, Meta

SOURCE = "gretil"
BASE = "https://gretil.sub.uni-goettingen.de/gretil/corpustei/"
FILES = {
    "sa_atharvavedapariziSTas.xml": "Atharvaveda-Pariśiṣṭa (incl. 68 Svapnādhyāya)",
    "sa_agnipurANa.xml": "Agnipurāṇa",
    "sa_garuDapurANa.xml": "Garuḍapurāṇa",
    "sa_matsyapurANa1-176.xml": "Matsyapurāṇa 1-176",
    "sa_brahmANDapurANa.xml": "Brahmāṇḍapurāṇa",
    "sa_liGgapurANa1-108.xml": "Liṅgapurāṇa 1",
    "sa_liGgapurANa2.xml": "Liṅgapurāṇa 2",
    "sa_mArkaNDeyapurANa1-93.xml": "Mārkaṇḍeyapurāṇa 1-93",
    "sa_skandapurANa1-31.xml": "Skandapurāṇa 1-31",
    "sa_viSNudharmottarapurANa-2.xml": "Viṣṇudharmottarapurāṇa 2.127",
    "sa_viSNudharmottarapurANa3.xml": "Viṣṇudharmottarapurāṇa 3.343-353",
    "sa_zivapurANabooks-1-and-7.xml": "Śivapurāṇa 1, 7",
    "sa_harivaMza.xml": "Harivaṃśa",
    "sa_varAhamihira-bRhatsaMhitA.xml": "Varāhamihira, Bṛhatsaṃhitā",
    "sa_agniveza-carakasaMhitA-parts-comm.xml": "Caraka-Saṃhitā (selected parts, comm.)",
    "sa_vAgbhaTa-aSTAGgahRdayasUtra.xml": "Vāgbhaṭa, Aṣṭāṅgahṛdaya",
    "sa_bhAvamizra-bhAvaprakAza.xml": "Bhāvamiśra, Bhāvaprakāśa",
    "sa_mANDUkyopaniSad-comm.xml": "Māṇḍūkya Upaniṣad with Gauḍapāda's Kārikā and comm.",
    "sa_mANDUkyopaniSad-alt.xml": "Māṇḍūkya Upaniṣad (alt.)",
    "sa_mANDUkyopaniSatkArikA.xml": "Māṇḍūkyopaniṣatkārikā",
    "sa_gauDapAda-AgamazAstra.xml": "Gauḍapāda, Āgamaśāstra",
    "sa_lalitavistara.xml": "Lalitavistara",
    "sa_azvaghoSa-buddhacarita.xml": "Aśvaghoṣa, Buddhacarita",
    "sa_mahAvastu-avAdana.xml": "Mahāvastu",
    "sa_AryazUra-jAtakamAlA.xml": "Āryaśūra, Jātakamālā",
}
WHOLE = {"sa_mANDUkyopaniSad-comm.xml", "sa_mANDUkyopaniSad-alt.xml",
         "sa_mANDUkyopaniSatkArikA.xml"}  # short texts, keep entirely
TEI = "{http://www.tei-c.org/ns/1.0}"
SVAPNA = re.compile(r"svapn|svāpn|ṣvapn|duḥsvap|dauḥsvap|dauṣvap|duṣvap", re.I)
TITLE = re.compile(r"((iti|ity|atha).{0,80}|^\(?[^ ]{0,20}[ .]?)(svapnādhyāy|svapnavicār|svapnaphal|svapnaparivart)", re.I)
ID = re.compile(r"^\s*\(([^)]{2,60})\)\s*")


def text_of(el: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def header(root: ET.Element) -> dict:
    lic = root.find(f".//{TEI}availability/{TEI}licence")
    title = root.find(f".//{TEI}titleStmt/{TEI}title")
    avail = root.find(f".//{TEI}availability")
    return {
        "license": (lic.get("target") if lic is not None else "") or (text_of(avail) if avail is not None else ""),
        "license_text": text_of(lic) if lic is not None else (text_of(avail) if avail is not None else ""),
        "title": text_of(title) if title is not None else "",
    }


TRAIL = re.compile(r"([A-Z][A-Za-z]{1,12}_[0-9IVX]+(?:[,.][0-9]+)*[a-z]{0,3})\s*/*\s*$")


def verses(root: ET.Element) -> list[tuple[str, str, str]]:
    """(verse_id, chapter, text); chapter from verse ids, else from the enclosing <div>."""
    body = root.find(f".//{TEI}body")
    raw: list[tuple[str, str, str]] = []
    if body is None:
        return []
    counter = [0]

    def walk(el: ET.Element, div: str) -> None:
        for ch in el:
            if ch.tag == f"{TEI}div":
                counter[0] += 1
                head = ch.find(f"{TEI}head")
                label = (ch.get("n") or ch.get("{http://www.w3.org/XML/1998/namespace}id")
                         or (text_of(head)[:40] if head is not None else "") or f"div{counter[0]}")
                walk(ch, f"{div}/{label}" if div else label)
            elif ch.tag in (f"{TEI}p", f"{TEI}l", f"{TEI}head"):
                t = text_of(ch)
                if t:
                    raw.append((t, div, ch.tag))
            else:
                walk(ch, div)

    walk(body, "")
    ids = []
    for t, div, _ in raw:
        m = ID.match(t) or TRAIL.search(t.rstrip(" |/"))
        ids.append(m.group(1) if m else "")
    chaps = [chapter_of(i) if i else "" for i in ids]
    # verse ids stand at the end of a verse: back-fill, then forward-fill
    nxt = ""
    for k in range(len(chaps) - 1, -1, -1):
        if chaps[k]:
            nxt = chaps[k]
        elif nxt and raw[k][1] == raw[min(k + 1, len(raw) - 1)][1]:
            chaps[k] = nxt
    have_ids = sum(1 for i in ids if i) > len(ids) * 0.2
    out = []
    for (t, div, _), vid, c in zip(raw, ids, chaps):
        out.append((vid, c if have_ids else "div:" + div, t))
    return out


def chapter_of(vid: str) -> str:
    """'AP_43.022cd' -> 'AP_43'; 'GarP_1,100.1' -> 'GarP_1,100'; 'AVParis_68,1.13' -> 'AVParis_68,1'."""
    if not vid:
        return ""
    m = re.match(r"^(.*?)[.,]([0-9]+[a-z]{0,3})$", vid)
    return m.group(1) if m else vid


def main() -> None:
    f = Fetcher(Meta(SOURCE, license="see TEI header (mostly CC BY-NC-SA 4.0)",
                     rights_holder="GRETIL / SUB Göttingen and text contributors",
                     tradition="indian-sanskrit"), delay=2.0)
    out = ROOT / SOURCE / "passages.jsonl"
    summary = []
    with out.open("w", encoding="utf-8") as fh:
        for name, label in FILES.items():
            url = BASE + name
            try:
                local = ROOT / SOURCE / "files" / name
                if f.seen(url) and local.exists():
                    content = local.read_bytes()
                else:
                    content = f.get(url, name=name).content
            except Blocked as e:
                print("blocked", name, e)
                continue
            except Exception as e:  # 404 etc.
                print("error", name, e)
                continue
            try:
                root = ET.fromstring(content)
            except ET.ParseError as e:
                print("parse error", name, e)
                continue
            meta = header(root)
            vs = verses(root)
            chap_hits: dict[str, list[int]] = {}
            for vid, c, t in vs:
                chap_hits.setdefault(c, [0, 0])
                chap_hits[c][1] += 1
                if SVAPNA.search(t):
                    chap_hits[c][0] += 1
            titled = {c for _, c, t in vs if TITLE.search(t)}
            parent_hits: dict[str, list[int]] = {}
            for c, (h, n) in chap_hits.items():
                pc = chapter_of(c) if not c.startswith("div:") else c
                parent_hits.setdefault(pc, [0, 0])
                parent_hits[pc][0] += h
                parent_hits[pc][1] += n
            dense = {c for c, (h, n) in chap_hits.items() if h >= 4 and h / max(n, 1) >= 0.08}
            dense_parent = {c for c, (h, n) in parent_hits.items()
                            if h >= 8 and h / max(n, 1) >= 0.08}
            dream_chaps = {c for c in chap_hits
                           if c and c != "div:" and (c in dense or c in titled or
                                                     (chapter_of(c) in dense_parent and "," in c))}
            keep: dict[int, str] = {}
            for i, (vid, c, t) in enumerate(vs):
                if name in WHOLE:
                    keep[i] = "whole_text"
                elif c in dream_chaps:
                    keep[i] = "dream_chapter"
                elif SVAPNA.search(t):
                    keep[i] = "svapna_verse"
                    for j in (i - 1, i + 1):
                        if 0 <= j < len(vs) and j not in keep:
                            keep[j] = "context"
            for i in sorted(keep):
                vid, c, t = vs[i]
                fh.write(json.dumps({
                    "source": SOURCE, "file": name, "work": label, "title": meta["title"],
                    "locator": vid, "chapter": c, "reason": keep[i],
                    "has_svapna": bool(SVAPNA.search(t)), "language": "sa", "script": "IAST",
                    "text": t, "url": url, "license": meta["license"],
                }, ensure_ascii=False) + "\n")
            summary.append({"file": name, "work": label, "verses": len(vs),
                            "svapna_verses": sum(h for h, _ in chap_hits.values()),
                            "dream_chapters": sorted(dream_chaps), "kept": len(keep),
                            "license": meta["license"], "bytes": len(content)})
            print(name, len(vs), "svapna:", summary[-1]["svapna_verses"], "dream chapters:",
                  sorted(dream_chaps), "kept:", len(keep))
    (ROOT / SOURCE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                                encoding="utf-8")


if __name__ == "__main__":
    main()
