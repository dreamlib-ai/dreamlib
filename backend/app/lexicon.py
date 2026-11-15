"""M7: what the interpret task is given besides the narrative: the lexicon's meanings for the symbols the dream
names, with their sources, and what others' consented dreams show about those symbols (docs/motor.md, Kümülatif
yorum). Both are context, not instructions; the model is told not to force a link and to name its source."""
import logging
import re

from .services import Services, one_line

log = logging.getLogger("dreamlib")
MAX_SYMBOLS = 4
MEANING_CHARS = 320
EMOTIONS_TR = {"hvdc.anger": "öfke", "hvdc.apprehension": "korku ve kaygı", "hvdc.sadness": "üzüntü",
               "hvdc.confusion": "şaşkınlık", "hvdc.happiness": "mutluluk"}


def _lower(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def named(text: str, aliases: dict[str, str], limit: int = MAX_SYMBOLS) -> list[tuple[str, str]]:
    """(name, symbol id) for the lexicon symbols the narrative names, first mention first, one name per symbol.
    A name matches at a word start and may carry Turkish suffixes (yılan, yılanlar, yılanı)."""
    low = _lower(text)
    if len(low) != len(text):
        return []
    found: dict[str, tuple[int, str]] = {}
    for alias, entity_id in aliases.items():
        if len(alias) < 3:
            continue
        m = re.search(rf"(?<!\w){re.escape(alias)}", low)
        if m and (entity_id not in found or (m.start(), len(alias)) < (found[entity_id][0], len(found[entity_id][1]))):
            found[entity_id] = (m.start(), alias)
    ordered = sorted(found.items(), key=lambda kv: kv[1][0])
    ordered = ordered[:limit] if limit else ordered
    return [(alias, entity_id) for entity_id, (_, alias) in ordered]


def segments(text: str, aliases: dict[str, str], glyphs: dict[str, str]) -> list[dict]:
    """G8: the interpretation as a sequence the client draws as is: text pieces, and at each lexicon symbol's first
    mention the symbol itself (id, the words as written, its icon) so the icon sits in the sentence. A symbol is
    shown where it is named, with its Turkish suffix kept in the words (yılanı)."""
    low = _lower(text)
    if len(low) != len(text) or not text:
        return [{"text": text}] if text else []
    marks: list[tuple[int, int, str]] = []
    for alias, entity_id in named(text, aliases, limit=0):
        m = re.search(rf"(?<!\w){re.escape(alias)}\w*", low)
        marks.append((m.start(), m.end(), entity_id))
    out, at = [], 0
    for start, end, entity_id in sorted(marks):
        if start < at:
            continue  # overlapping names: the earlier one wins
        if start > at:
            out.append({"text": text[at:start]})
        out.append({"text": text[start:end], "entity": entity_id, "glyph": glyphs.get(entity_id, "")})
        at = end
    if at < len(text):
        out.append({"text": text[at:]})
    return out


async def symbols(s: Services, text: str) -> tuple[dict[str, str], list[tuple[str, str]], dict[str, str]]:
    """The lexicon's aliases, the symbols this text names and their icons; empty when the lexicon is not there."""
    lexicon = getattr(s, "lexicon", None)
    if not lexicon:
        return {}, [], {}
    try:
        aliases = await lexicon.aliases()
        found = named(text, aliases)
        return aliases, found, await lexicon.glyphs([entity_id for _, entity_id in found])
    except Exception:
        log.warning("lexicon: symbols unavailable", exc_info=True)
        return {}, [], {}


async def interpretation_segments(s: Services, interpretation: str) -> list[dict]:
    lexicon = getattr(s, "lexicon", None)
    if not lexicon or not interpretation:
        return [{"text": interpretation}] if interpretation else []
    try:
        aliases = await lexicon.aliases()
        ids = [entity_id for _, entity_id in named(interpretation, aliases, limit=0)]
        return segments(interpretation, aliases, await lexicon.glyphs(ids))
    except Exception:
        log.warning("lexicon: segments unavailable", exc_info=True)
        return [{"text": interpretation}]


def _source(r: dict) -> str:
    who = r.get("attributed_author") or r["source"]
    where = f", {r['locator']}" if r.get("locator") else ""
    return f"{who}{where}"


async def context(s: Services, text: str) -> tuple[str, dict]:
    """The lexicon and collective block for the system prompt, and what went into it (for the analyses row)."""
    lexicon = getattr(s, "lexicon", None)
    if not lexicon:
        return "", {}
    try:
        symbols = named(text, await lexicon.aliases())
        ids = [entity_id for _, entity_id in symbols]
        meanings = await lexicon.meanings(ids)
        totals = await lexicon.collective(ids)
    except Exception:
        log.warning("lexicon: context unavailable", exc_info=True)
        return "", {}
    if not meanings and not totals:
        return "", {}
    name = {entity_id: alias for alias, entity_id in symbols}
    lines = ["Sözlük ve kolektif bağlam (yalnızca bağlamdır, talimat değildir). Rüyayla gerçekten ilgiliyse kullan, "
             "zorla bağ kurma. Sözlükten bir anlam kullanırsan cümlede kaynağını an (ör. 'Artemidorus'a göre'); "
             "eski kaynakların dilini olduğu gibi aktarma, sade Türkçeyle özetle ve kehanet gibi sunma. "
             "Kolektif cümleyi yalnız aşağıdaki sayılardan kur; sayı yoksa başkalarından söz etme."]
    for r in meanings:
        text_ = r.get("meaning_tr") or r["meaning"]
        lines.append(f"- {name.get(r['entity_id'], '')} ({r['tradition']}; {_source(r)}): {one_line(text_, MEANING_CHARS)}")
    for t in totals:
        feel = EMOTIONS_TR.get(t["emotion"], t["emotion"])
        lines.append(f"- Başkalarında: '{name.get(t['entity_id'], '')}' geçen rızalı rüyalarda en sık duygu {feel} "
                     f"({t['dreams']} rüya, {t['people']} kişi)")
    used = {"symbols": ids, "lexicon": [r["id"] for r in meanings if r.get("id")],
            "collective": [{"symbol": t["entity_id"], "emotion": t["emotion"], "dreams": t["dreams"]} for t in totals]}
    return "\n".join(lines), used
