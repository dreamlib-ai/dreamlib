-- G3: her kaydedilen görselin yerleşim bilgisi; kütüphane ve dergi görsel yüklenmeden düzeni kurar.
-- path depodaki dosya (panellerin `path`'i), thumb_path 480 px WebP kopyası. Yalnız service key yazar ve okur.
create table public.images (
  path        text primary key,
  user_id     uuid not null references auth.users (id) on delete cascade,
  width       int not null check (width > 0),
  height      int not null check (height > 0),
  blurhash    text not null default '',
  color       text not null default '' check (color = '' or color ~ '^#[0-9a-f]{6}$'),
  thumb_path  text not null default '',
  created_at  timestamptz not null default now()
);

create index images_user_idx on public.images (user_id);

alter table public.images enable row level security;
