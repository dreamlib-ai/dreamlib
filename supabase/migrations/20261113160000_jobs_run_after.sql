-- Geçici hatadan sonra iş hemen değil, üstel bekleme ve jitter'la (5, 20, 80 sn) kuyruğa döner.
-- Worker 'run_after' zamanı gelmemiş işi almaz. Hata sınıfı: backend/app/providers/errors.py.
alter table public.jobs add column run_after timestamptz not null default now();

drop index if exists jobs_queue_idx;
create index jobs_queue_idx on public.jobs (run_after, created_at) where status in ('queued', 'running');

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
      order by created_at
      for update skip locked
      limit 1)
  returning j.*;
end;
$$;

revoke execute on function public.claim_job(text, int, int) from public, anon, authenticated;
