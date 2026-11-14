-- M6: A kademesi sözlük (veri.md, karar 0008). Her satır bir geleneğin bir sembole verdiği anlam; kaynak ve yer
-- bilgisiyle. Yalnız kamu malı ve açık lisanslı (A) metin girer; B ve C kaynaklardan metin, çeviri ya da yeniden
-- yazılmış anlam taşınmaz. Sembol `entities` düğümüdür (kind symbol, onaylı, anahtar Wikidata kimliği wd.Q…).
create table public.lexicon_entries (
  id                 uuid primary key default gen_random_uuid(),
  entity_id          uuid not null references public.entities (id) on delete cascade,
  tradition          text not null,
  language           text not null,
  heading            text not null default '',      -- kaynağın kendi başlığı
  meaning            text not null,                 -- kaynaktaki metnin kendisi
  meaning_tr         text not null default '',      -- Türkçe karşılığı, eklendiğinde
  source             text not null,
  locator            text not null default '',      -- bölüm, sayfa, madde
  url                text not null default '',
  license            text not null,
  rights_holder      text not null default '',
  attributed_author  text not null default '',
  tier               text not null default 'A' check (tier = 'A'),
  created_at         timestamptz not null default now(),
  unique (source, locator, entity_id)
);

create index lexicon_entries_entity_idx on public.lexicon_entries (entity_id);

alter table public.lexicon_entries enable row level security;
