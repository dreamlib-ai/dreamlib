-- Manga panelleri ve görsel deposu.
-- Görseller private 'dream-images' kovasında durur; Go API service key ile yazar ve
-- okurken süreli imzalı adres üretir. Dosya yolu `<user_id>/<rastgele>.<uzantı>`.

alter table public.dreams drop column image_urls;
alter table public.dreams add column style text not null default 'manga'
  check (style in ('manga', 'illustration', 'collage', 'photographic'));
alter table public.dreams add column panels jsonb not null default '[]'; -- [{caption, path}]

insert into storage.buckets (id, name, public)
values ('dream-images', 'dream-images', false)
on conflict (id) do nothing;
