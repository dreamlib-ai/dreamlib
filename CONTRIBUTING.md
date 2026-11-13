# Contributing to Dreamlib

Thank you for being here. Dreamlib is building an open atlas of how people dream, and it needs more than code: drawings, languages, old dream books and odd dreams that confuse the model are all welcome.

## Pick a lane

| Lane | What you do | Skills |
| --- | --- | --- |
| Icons | Draw or improve the small icon of a dream symbol | Drawing |
| Dictionary | Translate symbol labels into your language, link synonyms | Your language |
| Traditions | Add a freely licensed dream book from your culture | Curiosity, a little Python |
| Evals | Add a dream the model gets wrong | Patience |
| Magazine layouts | Design a new page layout for the reader | CSS, React |
| Translations | Translate the interface | Your language |
| Engine | Write a new relation type and its scorer | Python, SQL |

Issues marked `good first issue` are sized for a first contribution. The task list lives in [docs/gorevler.md](docs/gorevler.md) (Turkish; rows marked with a seedling are good starting points). If you want something that is not listed, open an issue first so nobody works twice.

## Ground rules

- **No dreams in the repository.** Never commit a real person's dream, including your own, outside the donation flow. Examples in tests and evals must be written for the purpose or come from freely licensed sources.
- **Know where your material comes from.** Icons must be your own work. Dictionary sources must be public domain, CC0, CC BY or CC BY-SA; say which in the pull request. Text from copyrighted dream sites is not accepted, and neither is a model's rewrite of it.
- **Respect every tradition.** Dream interpretation is tied to faith and culture. We describe traditions; we do not rank or mock them.
- **Keep it simple.** One process, one database, few dependencies. Propose a new dependency in an issue before adding it.

## Setting up

```powershell
npm run setup
npm run dev
npm run check
```

`DREAMLIB_DEV_AUTH=1` and `DREAMLIB_FAKE_AI=1` in `backend/.env` run the backend with in-memory accounts and stand-in AI answers, so you need no keys. See [README.md](README.md) for the layout and [docs/mimari.md](docs/mimari.md) for the architecture.

## Making a change

1. Branch from `main`: `feat/<topic>` or `fix/<topic>`.
2. Keep the change to one topic. Small pull requests are reviewed first.
3. Run `npm run check` before you push.
4. Write commits as Conventional Commits, in English and short: `feat: add dream feed`, `fix: keep tab slots fixed`.
5. Open a pull request and fill in the template: what changed, why, how you tried it, anything to watch.

Code, variable names and file names are in English. Interface text lives in one file per language. Product documents are in Turkish for now; you may write issues and pull requests in English or Turkish.

## Review

A maintainer looks at open pull requests at least once a week. Checks must pass before a merge. Changes to prompts, models or the similarity scorer need the evaluation results in the pull request.

## Licensing of contributions

By contributing you agree that your code is licensed under AGPL-3.0, and that icons, dictionary data and evaluation examples are licensed under the Creative Commons licenses listed in [docs/acik-kaynak.md](docs/acik-kaynak.md). You keep your copyright.

## Saying thanks

Everyone who contributes appears on the contributors wall, with a small koala badge for their lane. Your first merged pull request gets a thank-you and a suggestion for what to pick up next.
