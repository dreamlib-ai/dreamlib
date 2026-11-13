# Dreamlib

Tell your dream out loud when you wake up. Dreamlib reads it back with its symbols, turns it into a small illustrated magazine, keeps it in your library, and (if you choose) shows what you share with people who dream alike.

Dreamlib is an open dream engine: the code, the symbol dictionary, the icon library and the evaluation sets are open. Your dreams are not. They never enter this repository or any public dataset unless you donate one yourself.

Türkçe: [README.tr.md](README.tr.md)

## What works today

- Voice-first dream capture, with typing as a second option
- Interpretation with symbols, emotions, genres and point of view
- Illustrated booklets drawn in the background, with a consistent character
- A private library with search, filters, dates and favorites

## What we are building

- A dream graph that links dreams through symbols, themes and emotions
- Explainable similarity: every match percentage shows the common ground behind it
- Interpretations that read a dream next to your own earlier dreams and similar ones from people who opted in
- Magazines you can page through and share, and a library that looks like a wall of covers
- A mobile app on the same backend

The plan is in [docs/vizyon.md](docs/vizyon.md) and [docs/yol-haritasi.md](docs/yol-haritasi.md). Decisions and their trade-offs are in [docs/kararlar](docs/kararlar). Product documents are in Turkish for now; translations are welcome.

## Layout

```text
frontend/  React + TypeScript + Vite
backend/   Python + FastAPI, Postgres job queue, OpenRouter and fal clients
corpus/    collectors for dream-interpretation sources (code only, no data)
docs/      architecture, engine, data, roadmap, decisions
scripts/   setup, dev, check
```

## Getting started

```powershell
npm run setup   # frontend packages and backend/.venv; creates backend/.env
npm run dev     # backend on :8080 (schema at /docs), frontend on :5173
npm run check   # pytest, type check and build
```

Set `DREAMLIB_DEV_AUTH=1` and `DREAMLIB_FAKE_AI=1` in `backend/.env` to run the whole flow locally with in-memory accounts and stand-in AI answers: no Supabase project and no paid keys. Real interpretations and pictures need your own keys; see `backend/env.example`.

## Contributing

You do not have to write backend code to help. You can draw an icon for a symbol, translate symbol labels into your language, add a public-domain dream book from your culture, or add a tricky dream to the evaluation set. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

Please read the [Code of Conduct](CODE_OF_CONDUCT.md). Report security problems privately as described in [SECURITY.md](SECURITY.md).

## License

Code is licensed under AGPL-3.0. Dictionary data, icons and evaluation sets carry their own Creative Commons licenses, listed in [docs/acik-kaynak.md](docs/acik-kaynak.md).
