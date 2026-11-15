"""G8: reads string fields out of a JSON object while it is still being written.

The interpret task answers one JSON object (models.Analysis); streamed, its `title` can be shown as soon as it is
closed and its `interpretation` while it is written. Only top-level string fields are read, and only the first
time their key appears outside a string (the keys come before `objects`, so a nested key cannot shadow them).
The whole answer is still parsed and validated at the end; this only lets the reader see it sooner."""
import json
import re


class FieldReader:
    def __init__(self, fields: tuple[str, ...]):
        self.buf = ""
        self.state = {f: {"pos": -1, "done": False, "text": ""} for f in fields}

    def value(self, field: str) -> str:
        """What has been read of the field so far (all of it once closed)."""
        return self.state[field]["text"]

    def feed(self, piece: str) -> list[tuple[str, str, bool]]:
        """Adds a piece of the answer; returns (field, newly decoded text, closed) for every field that moved."""
        self.buf += piece
        out = []
        for field, st in self.state.items():
            if st["done"]:
                continue
            if st["pos"] < 0:
                m = re.search(rf'(?<!\\)"{re.escape(field)}"\s*:\s*"', self.buf)
                if not m:
                    continue
                st["pos"] = m.end()
            text, closed = self._read(st)
            st["text"] += text
            if text or closed:
                out.append((field, text, closed))
        return out

    def _read(self, st: dict) -> tuple[str, bool]:
        buf, i, chars = self.buf, st["pos"], []
        while i < len(buf):
            c = buf[i]
            if c == '"':
                st["pos"], st["done"] = i + 1, True
                return "".join(chars), True
            if c == "\\":
                if i + 1 >= len(buf):
                    break  # the escape is split across pieces: wait for the rest
                length = 6 if buf[i + 1] == "u" else 2
                if length == 6 and buf[i + 2:i + 4].lower() in ("d8", "d9", "da", "db"):
                    length = 12  # a surrogate pair's first half: decode it with the second
                if i + length > len(buf):
                    break
                try:
                    chars.append(json.loads(f'"{buf[i:i + length]}"'))
                except ValueError:
                    chars.append("�")  # a broken escape; the full parse at the end decides
                i += length
                continue
            chars.append(c)
            i += 1
        st["pos"] = i
        return "".join(chars), False
