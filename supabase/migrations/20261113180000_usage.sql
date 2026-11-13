-- Ücretli her sağlayıcı çağrısı bir satır: kim, hangi iş, hangi model, ne kadar.
-- Fiyatlandırma ve ileride harcama freni bu tablodan okunur. Yazan: backend/app/usage.py.
create table public.usage (
  id         bigint generated always as identity primary key,
  user_id    uuid references auth.users (id) on delete set null,
  job_id     uuid references public.jobs (id) on delete set null,
  provider   text not null,               -- openrouter | fal
  model      text not null default '',
  task       text not null default '',    -- LLM görevi ya da fal işi (image, edit, speech)
  units      numeric(14, 2) not null default 0,
  unit       text not null default '',    -- tokens | images | requests
  cost_usd   numeric(12, 6) not null default 0,
  created_at timestamptz not null default now()
);

create index usage_user_created_idx on public.usage (user_id, created_at desc);
create index usage_created_idx on public.usage (created_at);

-- Politika yok: tabloya yalnız service key ile API yazar.
alter table public.usage enable row level security;
