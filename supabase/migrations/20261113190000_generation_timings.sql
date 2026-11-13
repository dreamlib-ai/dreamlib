-- fal kuyruğu süre tahmini vermiyor (yalnız queue_position ve bitince metrics.inference_time).
-- Bu süreçte kuyruğa verilen her isteğin süresi burada tutulur; backend/app/eta.py açılışta son
-- satırları okuyup model başına cezalı regresyon eğrisini yeniden kurar.
create table public.generation_timings (
  id                bigint generated always as identity primary key,
  model             text not null,                -- fal id
  typical_seconds   numeric(8, 2) not null default 10,
  features          jsonb not null,               -- [1, görsel sayısı, referans sayısı, ilk bakıştaki sıra]
  total_seconds     numeric(8, 2) not null,       -- kuyruğa verilişten tamamlanmaya
  inference_seconds numeric(8, 2),                -- fal'ın bildirdiği çalışma süresi
  created_at        timestamptz not null default now()
);

create index generation_timings_created_idx on public.generation_timings (created_at desc);

-- Politika yok: tabloya yalnız service key ile API yazar.
alter table public.generation_timings enable row level security;
