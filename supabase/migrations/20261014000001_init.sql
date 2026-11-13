-- Dreamlib başlangıç şeması (Supabase Postgres).
-- Kullanıcılar Supabase Auth'ta (auth.users); misafirler anonim kullanıcıdır.
-- Go API service key ile yazar ve user_id'yi kendisi süzer; RLS ise tarayıcıdan
-- doğrudan erişilirse de kimsenin başkasının rüyasını görememesi için açık.

create table public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  username    text unique,
  visibility  text not null default 'private' check (visibility in ('private', 'public')),
  created_at  timestamptz not null default now()
);

create table public.dreams (
  id                  uuid primary key default gen_random_uuid(),
  user_id             uuid not null references auth.users (id) on delete cascade,
  title               text not null,
  original_text       text not null,          -- kullanıcının yazdığı hâli
  clean_text          text not null default '', -- yapay zekânın düzelttiği hâli
  interpretation_type text not null default 'universal'
                      check (interpretation_type in ('universal', 'cultural', 'psychoanalytic')),
  interpretation      text not null default '',
  tags                text[] not null default '{}',
  objects             jsonb not null default '[]',   -- [{label, meaning}]
  emotions            jsonb not null default '[]',   -- [{label, pct, note}]
  image_urls          text[] not null default '{}',
  visibility          text not null default 'private' check (visibility in ('private', 'public')),
  created_at          timestamptz not null default now()
);

create index dreams_user_created_idx on public.dreams (user_id, created_at desc);

alter table public.profiles enable row level security;
alter table public.dreams enable row level security;

create policy "profil sahibi okur" on public.profiles for select using (id = (select auth.uid()));
create policy "profil sahibi ekler" on public.profiles for insert with check (id = (select auth.uid()));
create policy "profil sahibi günceller" on public.profiles for update using (id = (select auth.uid()));

create policy "rüya sahibi okur" on public.dreams for select using (user_id = (select auth.uid()));
create policy "rüya sahibi ekler" on public.dreams for insert with check (user_id = (select auth.uid()));
create policy "rüya sahibi günceller" on public.dreams for update using (user_id = (select auth.uid()));
create policy "rüya sahibi siler" on public.dreams for delete using (user_id = (select auth.uid()));
