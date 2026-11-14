-- M3: her yorum ayrı satır. `dreams` sahibinin okuduğu geniş kayıt olarak kalır (eski alanlar okunmaya devam
-- eder); bir rüyanın her yorumu ve her indekslemesi burada sürümleriyle durur, eskisi silinmez (docs/motor.md).
-- pipeline: interpret (LLM yorumu) | lab.index (LLM'siz çıkarım, M4). Yalnız service key yazar ve okur.

create table public.analyses (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  dream_id     uuid references public.dreams (id) on delete cascade,  -- yorum kayıttan önce gelir, kayıtla bağlanır
  pipeline     text not null check (pipeline ~ '^[a-z][a-z0-9_.]{0,31}$'),
  prompt       text not null default '',   -- prompt ya da kural sürümü, ör. interpret@1, lab@1
  model        text not null default '',   -- çağrılan model; kural motorunda boş
  input_sha256 text not null default '',   -- girdinin özeti; metnin kendisi rüyada durur
  output       jsonb not null,
  created_at   timestamptz not null default now()
);

create index analyses_dream_idx on public.analyses (dream_id, created_at desc) where dream_id is not null;
create index analyses_user_idx on public.analyses (user_id, created_at desc);

alter table public.analyses enable row level security;

-- M4 arka plan işleri (index) kullanıcıyı kilitlemez: kayıt ve günlük kilidi yalnız ücretli çizim işlerini
-- (exclusive) bekler. Gövde 20261014000006_quota_locks ile aynı, tek fark `and exclusive`.
create or replace function public.lock_user(p_user uuid, p_token text, p_seconds int, p_no_jobs boolean)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_no_jobs and exists (select 1 from jobs where user_id = p_user and status in ('queued', 'running') and exclusive) then
    return false;
  end if;
  insert into user_locks (user_id, token, until)
  values (p_user, p_token, now() + make_interval(secs => p_seconds))
  on conflict (user_id) do update set token = excluded.token, until = excluded.until
   where user_locks.until < now();
  return found;
end;
$$;

revoke execute on function public.lock_user(uuid, text, int, boolean) from public, anon, authenticated;
