"""Dream report datasets on the Hugging Face Hub.

Downloads the data files of dream-report / dream-interpretation datasets
found via the HF API search (keywords: dream, dreams, dreambank, lucid,
nightmare, oneir, ruya, tabir, sleep ...) and writes `datasets.jsonl` with
rows, languages, license, rights holder and HVdC flag per dataset.

Personal narratives: keep local, never publish.

Run: backend/.venv/Scripts/python -m corpus.sources.huggingface
"""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from urllib.parse import quote

from corpus.fetch import Blocked, Fetcher, Meta

API = "https://huggingface.co/api/datasets"
DS = "https://datasets-server.huggingface.co"
DATA_EXT = {".parquet", ".csv", ".tsv", ".json", ".jsonl", ".txt", ".md"}
MAX_BYTES = 400 * 1024 * 1024

DREAMBANK = "DreamBank (dreambank.net) — Adam Schneider & G. William Domhoff, UC Santa Cruz"
DREAMBANK_CONTACT = "https://dreams.ucsc.edu (dreamresearch.net/contact.html)"
DREAMBANK_LIC = "CC BY-NC-SA 4.0 (upstream DreamBank; HF tag differs)"

# kind: real_reports | derived_reports | interpretation | synthetic
DATASETS: list[dict] = [
    dict(id="DReAMy-lib/DreamBank-dreams-en", kind="real_reports", languages=["en"], hvdc=False,
         rights_holder=DREAMBANK, contact=DREAMBANK_CONTACT, upstream_license=DREAMBANK_LIC,
         note="DreamBank scraped by mattbierner (DreamScrape); series, description, gender, year."),
    dict(id="DReAMy-lib/DreamBank-dreams", kind="real_reports", languages=["en", "de"], hvdc=False,
         rights_holder=DREAMBANK, contact=DREAMBANK_CONTACT, upstream_license=DREAMBANK_LIC,
         note="Larger EN+DE DreamBank variant (~29k)."),
    dict(id="gustavecortal/DreamBank-annotated", kind="real_reports", languages=["en"], hvdc=True,
         rights_holder=DREAMBANK + "; annotations Gustave Cortal", contact=DREAMBANK_CONTACT,
         upstream_license=DREAMBANK_LIC,
         note="HVdC characters/emotions predicted by dream-t5 (model annotations, not manual coding)."),
    dict(id="jimmyclchu/dreambank-net", kind="real_reports", languages=["en"], hvdc=False,
         rights_holder=DREAMBANK, contact=DREAMBANK_CONTACT, upstream_license=DREAMBANK_LIC,
         note="DreamBank text lowercased with stopwords/punctuation removed; series + number."),
    dict(id="mujo-labs/sandman-dreambank-v2", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder=DREAMBANK + "; LLM annotations mujo-labs", contact=DREAMBANK_CONTACT,
         upstream_license=DREAMBANK_LIC,
         note="DreamBank reports + LLM title/summary/mood/themes/symbols/interpretation."),
    dict(id="mujo-labs/sandman-dream_multitask_v2_train", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder=DREAMBANK + "; mujo-labs", contact=DREAMBANK_CONTACT, upstream_license=DREAMBANK_LIC,
         note="Instruction data (summarize / symbols / interpret) built from sandman-dreambank-v2."),
    dict(id="mujo-labs/sandman-dream_multitask_v2_val", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder=DREAMBANK + "; mujo-labs", contact=DREAMBANK_CONTACT, upstream_license=DREAMBANK_LIC),
    dict(id="mujo-labs/sandman-dream_multitask_v2_test", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder=DREAMBANK + "; mujo-labs", contact=DREAMBANK_CONTACT, upstream_license=DREAMBANK_LIC),
    dict(id="mujo-labs/sandman-dream_multitask_train", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder="mujo-labs (source corpus not stated; card says 'broader source' than DreamBank)",
         contact="huggingface.co/mujo-labs", upstream_license="unknown",
         note="v1 multitask instructions, superseded by v2."),
    dict(id="mujo-labs/sandman-dream_multitask_val", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder="mujo-labs", contact="huggingface.co/mujo-labs", upstream_license="unknown"),
    dict(id="mujo-labs/sandman-dream_multitask_test", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder="mujo-labs", contact="huggingface.co/mujo-labs", upstream_license="unknown"),
    dict(id="kumpank/dream-observatory", kind="real_reports", languages=["en"], hvdc=False,
         rights_holder="kumpank (scraped public posts: YouTube comments etc.; authors hashed)",
         contact="huggingface.co/kumpank", upstream_license="platform ToS of source posts",
         note="1,646 public narratives + 16 LLM-scored phenomenology dimensions."),
    dict(id="Masterogon/dream-database", kind="real_reports", languages=["en"], hvdc=False,
         rights_holder="Masterogon (self-submitted ASC/dream narratives)", contact="huggingface.co/Masterogon",
         upstream_license="none stated", note="20 altered-state/dream narratives with emotion+intensity."),
    dict(id="ganashreepm/dream_model", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder="ganashreepm (origin of dream contents not stated)", contact="huggingface.co/ganashreepm",
         upstream_license="none stated",
         note="Llama-3 prompts: dream content + profession + trigger -> emotion tags, therapy suggestions."),
    dict(id="sherum/dream_dataset", kind="derived_reports", languages=["en"], hvdc=False,
         rights_holder="sherum (dream passages extracted from book chapters; book rights unknown)",
         contact="huggingface.co/sherum", upstream_license="none stated"),
    dict(id="TELEGENIX/Darkest-Dreams", kind="synthetic", languages=["en"], hvdc=False,
         rights_holder="TELEGENIX", contact="huggingface.co/TELEGENIX", upstream_license="none stated"),
    dict(id="tolgadev/ruyatabirleri", kind="interpretation", languages=["tr"], hvdc=False,
         rights_holder="tolgadev (scraped Turkish dream-interpretation sites; original site rights)",
         contact="huggingface.co/tolgadev", upstream_license="source sites unknown",
         note="8,897 Turkish 'rüyada X görmek' question -> interpretation pairs."),
    dict(id="tolgadev/ruyatabirleri_instruct", kind="interpretation", languages=["tr"], hvdc=False,
         rights_holder="tolgadev", contact="huggingface.co/tolgadev", upstream_license="source sites unknown",
         note="Same pairs in Mistral [INST] format."),
    dict(id="teragron/dream_interpretation", kind="interpretation", languages=["tr"], hvdc=False,
         rights_holder="teragron (Turkish classical tabirname text; edition unknown)",
         contact="huggingface.co/teragron", upstream_license="edition unknown",
         note="5,778 word -> meaning entries; .bin/.pt model files skipped."),
    dict(id="n3rd0/DreamBook_Guanaco_Format", kind="interpretation", languages=["en"], hvdc=False,
         rights_holder="n3rd0 (dream-book source unknown)", contact="huggingface.co/n3rd0",
         upstream_license="none stated", note="9,497 'What does it mean if I dream about X' QA."),
    dict(id="sadiaquddus/ibnsirin-dreamtext", kind="interpretation", languages=["en"], hvdc=False,
         rights_holder="Ibn Sirin dictionary, English translation (likely M. M. Al-Akili, 1992) — translator/publisher",
         contact="huggingface.co/sadiaquddus", upstream_license="translation likely in copyright"),
    dict(id="technorahmon/Interpretation-of-dreams", kind="interpretation", languages=["ar"], hvdc=False,
         rights_holder="technorahmon (Arabic 'Mawsu'at tafsir al-ahlam' pages, HTML)",
         contact="huggingface.co/technorahmon", upstream_license="source site unknown"),
    dict(id="theprint/databird-dreams", kind="synthetic", languages=["en"], hvdc=False,
         rights_holder="theprint", contact="huggingface.co/theprint", upstream_license="",
         note="974 LLM-generated dream-symbolism QA."),
    dict(id="samvlad/dream-decoder-dataset", kind="synthetic", languages=["en"], hvdc=False,
         rights_holder="samvlad", contact="huggingface.co/samvlad", upstream_license="",
         note="1,200 templated dreams + interpretations."),
]

# Listed only (not downloaded): gated, synthetic noise, or not dream reports.
LISTED: list[dict] = [
    dict(id="opsecsystems/Dream2Image", kind="real_reports", languages=["en"], hvdc=False, gated="manual",
         rights_holder="opsecsystems (Dream2Image authors)", contact="huggingface.co/opsecsystems",
         note="EEG + verbatim dream reports + images; manual-approval gate (login + terms) -> negotiation list."),
    dict(id="JesusAura999/Senik_SleepSimulationDreams_Dataset100K", kind="synthetic", languages=["en"], hvdc=False,
         rights_holder="JesusAura999", contact="", note="100k templated one-line 'dreams'; no value, skipped."),
    dict(id="TheMindExpansionNetwork/mindbot_dream_dataset", kind="synthetic", languages=["en"], hvdc=False,
         rights_holder="TheMindExpansionNetwork", contact="", note="Persona chat about 'AI dreaming', not reports."),
    dict(id="TheMindExpansionNetwork/mindbot-oneiric-v1-complete-3333", kind="synthetic", languages=["en"],
         hvdc=False, rights_holder="TheMindExpansionNetwork", contact="", note="Generated 'oneiric readings'."),
    dict(id="lemon2004/DREAMS", kind="other", languages=["en"], hvdc=False,
         rights_holder="Univ. Mons (DREAMS sleep EEG databases, Zenodo 2650142)", contact="",
         note="Sleep EEG events, no dream reports; out of scope."),
]


def file_list(f: Fetcher, ds_id: str) -> list[dict]:
    r = f.get(f"{API}/{ds_id}/tree/main?recursive=true", save=False)
    return [x for x in r.json() if x.get("type") == "file"]


def num_rows(f: Fetcher, ds_id: str) -> int | None:
    try:
        r = f.get(f"{DS}/size?dataset={quote(ds_id, safe='')}", save=False)
        return r.json().get("size", {}).get("dataset", {}).get("num_rows")
    except Exception:
        return None


def main() -> None:
    f = Fetcher(Meta(source="huggingface", license="see datasets.jsonl", rights_holder="see datasets.jsonl"),
                delay=1.0, timeout=300)
    out = []
    for spec in DATASETS:
        ds_id = spec["id"]
        info = f.get(f"{API}/{ds_id}", name=f"{ds_id.replace('/', '__')}/_api.json").json()
        tags = info.get("tags", [])
        lic = [t.split(":", 1)[1] for t in tags if t.startswith("license:")]
        saved, total = [], 0
        for item in file_list(f, ds_id):
            path = item["path"]
            ext = PurePosixPath(path).suffix.lower()
            size = item.get("lfs", {}).get("size") or item.get("size") or 0
            if (ext not in DATA_EXT and PurePosixPath(path).name != "LICENSE") or size > MAX_BYTES:
                continue
            url = f"https://huggingface.co/datasets/{ds_id}/resolve/main/{quote(path)}"
            try:
                r = f.get(url, name=f"{ds_id.replace('/', '__')}/{path}")
            except Blocked as e:
                print("blocked", url, e)
                continue
            saved.append(path)
            total += len(r.content)
        rows = num_rows(f, ds_id)
        row = dict(
            name=ds_id, source=f"https://huggingface.co/datasets/{ds_id}", kind=spec["kind"], rows=rows,
            languages=spec["languages"], license=lic[0] if lic else "none stated",
            upstream_license=spec.get("upstream_license", ""), rights_holder=spec["rights_holder"],
            contact=spec["contact"], hvdc_coded=spec["hvdc"], gated=info.get("gated") or False,
            downloaded=bool(saved), files=saved, bytes=total, note=spec.get("note", ""),
        )
        out.append(row)
        print(ds_id, rows, total, len(saved))
    for spec in LISTED:
        out.append(dict(
            name=spec["id"], source=f"https://huggingface.co/datasets/{spec['id']}", kind=spec["kind"],
            rows=None, languages=spec["languages"], license="", upstream_license="",
            rights_holder=spec["rights_holder"], contact=spec["contact"], hvdc_coded=spec["hvdc"],
            gated=spec.get("gated", False), downloaded=False, files=[], bytes=0, note=spec["note"],
        ))
    with (f.dir / "datasets.jsonl").open("w", encoding="utf-8") as fh:
        for row in out:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
