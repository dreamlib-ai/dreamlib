-- İş zinciri ve tekrar koruması. Bir iş bir rüyaya (dream_id) ve onu kuyruğa yazan işe (parent_id) bağlanır.
-- Aynı kullanıcı, tür ve dedupe_key ikinci bir iş açmaz. Öncelik büyük olan önce alınır.
-- "Kullanıcı başına tek aktif iş" kuralı yalnız exclusive türlere (ücretli çizim) uygulanır; değer kayıttan
-- (backend/app/pipelines/registry.py) gelir.
alter table public.jobs
  add column dream_id   uuid references public.dreams (id) on delete cascade,
  add column parent_id  uuid references public.jobs (id) on delete set null,
  add column dedupe_key text not null default '',
  add column priority   int not null default 0,
  add column exclusive  boolean not null default true;

create index jobs_dream_idx on public.jobs (dream_id) where dream_id is not null;
create unique index jobs_dedupe_idx on public.jobs (user_id, kind, dedupe_key) where dedupe_key <> '';

drop index if exists jobs_one_active_idx;
create unique index jobs_one_active_idx on public.jobs (user_id) where status in ('queued', 'running') and exclusive;

drop index if exists jobs_queue_idx;
create index jobs_queue_idx on public.jobs (priority desc, created_at) where status in ('queued', 'running');

create or replace function public.claim_job(p_worker text, p_lease_seconds int, p_max_attempts int)
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
      where (status = 'queued' and run_after <= now()) or (status = 'running' and lease_until < now())
      order by priority desc, created_at
      for update skip locked
      limit 1)
  returning j.*;
end;
$$;

revoke execute on function public.claim_job(text, int, int) from public, anon, authenticated;
