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


def test_stream_validation_does_not_log_dream_content(api, caplog):
    client, s = api
    marker = "synthetic-private-dream"
    s.llm.reply = json.dumps({**ANALYSIS, "tags": marker})
    res = client.post("/api/v1/analyze/stream", json={"text": marker}, headers=auth())
    kinds = [kind for kind, _ in events(res.text)]
    assert kinds[-1] == "error" and "done" not in kinds
    assert "invalid model response" in caplog.text and "list_type" in caplog.text
    assert marker not in caplog.text


RID = "5b0c1e7e-1d2f-4a8b-9c3d-2e4f6a8b0c1d"


def test_a_streamed_answer_is_read_back_by_its_request_id_without_another_use(api):
    client, s = api
    s.llm.reply = json.dumps(ANALYSIS, ensure_ascii=False)
    done = events(client.post("/api/v1/analyze/stream", json={"text": "Uçuyordum.", "requestId": RID}, headers=auth()).text)[-1]
    calls = len(s.llm.calls) if hasattr(s.llm, "calls") else None
    back = client.get(f"/api/v1/analyze/stream/{RID}", headers=auth())
    assert back.status_code == 200 and back.json() == done[1]
    assert calls is None or len(s.llm.calls) == calls  # read back, not written again
    assert client.get(f"/api/v1/analyze/stream/{RID}", headers=auth("dev-testuser-two")).status_code == 404
    assert client.get("/api/v1/analyze/stream/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404
    again = client.post("/api/v1/analyze/stream", json={"text": "Uçuyordum.", "requestId": RID}, headers=auth())
    assert again.status_code == 409  # the same id is one interpretation, never a second paid one


def test_a_failed_stream_reads_back_as_an_upstream_error(api):
    client, s = api
    s.llm.stream_fails_after = 2
    rid = "9a9a9a9a-1d2f-4a8b-9c3d-2e4f6a8b0c1d"
    kinds = [k for k, _ in events(client.post("/api/v1/analyze/stream", json={"text": "Uçuyordum.", "requestId": rid},
                                              headers=auth()).text)]
    assert kinds[-1] == "error"
    back = client.get(f"/api/v1/analyze/stream/{rid}", headers=auth())
    assert back.status_code == 502 and back.json()["code"] == "upstream_failed"


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
