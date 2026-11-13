-- Kalıcı iş kuyruğu: manga kitapçığı ve görsel üretimi bu tabloda sıraya girer.
-- API satırı 'queued' açar; worker claim_job ile alır, lease süresince işler.
-- Süreç ölürse lease dolar ve iş başka worker'a geçer; fal istek adresleri
-- state içinde durduğu için çizilmiş paneller yeniden ödenmez.

create table public.jobs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  kind        text not null check (kind in ('manga', 'image')),
  status      text not null default 'queued' check (status in ('queued', 'running', 'done', 'failed')),
  input       jsonb not null default '{}',   -- isteğin kendisi
  state       jsonb not null default '{}',   -- ara durum: taslak, paneller, fal istekleri
  error       text not null default '',
  done        int not null default 0,
  total       int not null default 1,
  attempts    int not null default 0,
  worker      text not null default '',
  lease_until timestamptz,
  cost_usd    numeric(10, 4) not null default 0,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index jobs_queue_idx on public.jobs (created_at) where status in ('queued', 'running');
create index jobs_user_created_idx on public.jobs (user_id, created_at desc);
-- Kullanıcı başına aynı anda tek iş; yarışan iki istekten biri çakışma alır.
create unique index jobs_one_active_idx on public.jobs (user_id) where status in ('queued', 'running');

-- Politika yok: tabloya yalnız service key ile API erişir.
alter table public.jobs enable row level security;

-- Sıradaki işi alır. Lease'i dolmuş ve deneme hakkı bitmiş işler önce kalıcı olarak düşer.
create function public.claim_job(p_worker text, p_lease_seconds int, p_max_attempts int)
returns setof public.jobs
language plpgsql
security definer
set search_path = public
as $$
begin
  update jobs
     set status = 'failed', error = 'iş tamamlanamadı, tekrar dene', lease_until = null, updated_at = now()
   where status = 'running' and lease_until < now() and attempts >= p_max_attempts;

  return query
  update jobs j
     set status = 'running', attempts = j.attempts + 1, worker = p_worker,
         lease_until = now() + make_interval(secs => p_lease_seconds), updated_at = now()
   where j.id = (
     select id from jobs
      where status = 'queued' or (status = 'running' and lease_until < now())
      order by created_at
      for update skip locked
      limit 1)
  returning j.*;
end;
$$;

revoke execute on function public.claim_job(text, int, int) from public, anon, authenticated;
