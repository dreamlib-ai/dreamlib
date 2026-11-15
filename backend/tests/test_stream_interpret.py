"""G8: the interpretation written while the user waits, and drawn with its symbols in place."""
import json

from app.jsonstream import FieldReader
from app.lexicon import segments
from app.store.lexicon import MemoryLexicon

from .conftest import ANALYSIS, auth

ALIASES = {"yılan": "s-yilan", "kapı": "s-kapi"}


def events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        kind = block.split("\n")[0].removeprefix("event: ")
        out.append((kind, json.loads(block.split("\n")[1].removeprefix("data: "))))
    return out


def test_the_reader_gives_fields_as_they_are_written_across_split_escapes():
    answer = json.dumps({"title": 'Kapı "eski"', "cleanText": "x", "interpretation": "Yılan\nsüzüldü ç é 🐍."},
                        ensure_ascii=True)
    reader, got = FieldReader(("title", "interpretation")), {"title": "", "interpretation": ""}
    closed = set()
    for i in range(len(answer)):  # one character at a time: every escape is split somewhere
        for field, text, done in reader.feed(answer[i]):
            got[field] += text
            if done:
                closed.add(field)
    assert got == {"title": 'Kapı "eski"', "interpretation": "Yılan\nsüzüldü ç é 🐍."} and closed == {"title", "interpretation"}
    assert reader.value("title") == 'Kapı "eski"'


def test_a_key_inside_a_string_is_not_a_field():
    reader = FieldReader(("interpretation",))
    reader.feed(json.dumps({"cleanText": 'dedi ki "interpretation": "yok"', "interpretation": "var"}))
    assert reader.value("interpretation") == "var"


def test_segments_put_each_symbol_in_its_sentence_once():
    parts = segments("Yılanı görmek bir kapı açar; yılan yine döner.", ALIASES, {"s-yilan": "https://x/y.webp"})
    assert parts == [{"text": "Yılanı", "entity": "s-yilan", "glyph": "https://x/y.webp"}, {"text": " görmek bir "},
                     {"text": "kapı", "entity": "s-kapi", "glyph": ""}, {"text": " açar; yılan yine döner."}]
    assert "".join(p["text"] for p in parts) == "Yılanı görmek bir kapı açar; yılan yine döner."
    assert segments("Uçuyordum.", ALIASES, {}) == [{"text": "Uçuyordum."}]


def test_the_stream_sends_symbols_title_text_and_the_whole_answer(api):
    client, s = api
    s.lexicon = MemoryLexicon(ALIASES, icons={"s-yilan": "https://x/y.webp"})
    s.llm.reply = json.dumps({**ANALYSIS, "interpretation": "Yılan bir değişimi anlatıyor olabilir."}, ensure_ascii=False)
    res = client.post("/api/v1/analyze/stream", json={"text": "Bir yılan kovaladı."}, headers=auth())
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/event-stream")
    got = events(res.text)
    kinds = [k for k, _ in got]
    assert kinds[:3] == ["section", "entity", "title"] and kinds[-1] == "done" and kinds.count("done") == 1
    assert got[1][1] == {"id": "s-yilan", "text": "yılan", "glyph": "https://x/y.webp"}
    assert "".join(d["text"] for k, d in got if k == "text") == "Yılan bir değişimi anlatıyor olabilir."
    done = got[-1][1]
    assert done["title"] == ANALYSIS["title"] and done["segments"][0] == {"text": "Yılan", "entity": "s-yilan", "glyph": "https://x/y.webp"}


def test_a_broken_stream_ends_with_an_error_event(api):
    client, s = api
    s.llm.stream_fails_after = 3
    res = client.post("/api/v1/analyze/stream", json={"text": "Uçuyordum."}, headers=auth())
    kinds = [k for k, _ in events(res.text)]
    assert res.status_code == 200 and kinds[-1] == "error" and "done" not in kinds


def test_errors_before_the_stream_are_http_errors(api):
    client, _ = api
    assert client.post("/api/v1/analyze/stream", json={"text": " "}, headers=auth()).status_code == 400
    assert client.post("/api/v1/analyze/stream", json={"text": "x"}).status_code == 401


def test_the_plain_answer_carries_segments_too(api):
    client, s = api
    s.lexicon = MemoryLexicon(ALIASES)
    s.llm.reply = json.dumps({**ANALYSIS, "interpretation": "Kapı yeni bir yol."}, ensure_ascii=False)
    body = client.post("/api/v1/analyze", json={"text": "Bir kapı."}, headers=auth()).json()
    assert body["segments"] == [{"text": "Kapı", "entity": "s-kapi", "glyph": ""}, {"text": " yeni bir yol."}]
