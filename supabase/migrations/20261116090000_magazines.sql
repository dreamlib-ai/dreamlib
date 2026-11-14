-- G4: her kitapçıklı rüyanın dergisi. `magazine` işi kaydedilen panellerden `spec`'i (kapak, adlandırılmış sayfa
-- düzenleri, künye) kurar; okuyucu onu istemcide çizer. Rüya başına bir dergi, rüya silinince gider.
-- Görünürlük ve share_slug paylaşım içindir (G6); şimdilik hepsi private. Yalnız service key yazar ve okur.
create table public.magazines (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users (id) on delete cascade,
  dream_id        uuid not null unique references public.dreams (id) on delete cascade,
  status          text not null default 'ready' check (status in ('ready', 'withdrawn')),
  visibility      text not null default 'private' check (visibility in ('private', 'link', 'public')),
  spec            jsonb not null,
  cover_path      text not null default '',
  share_slug      text unique,
  dream_revision  int not null default 0,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index magazines_user_idx on public.magazines (user_id, created_at desc);

alter table public.magazines enable row level security;
