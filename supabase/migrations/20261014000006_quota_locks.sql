-- Günlük hak sayaçları ve kullanıcı kilitleri. Önceden API sürecinin belleğindeydi;
-- birden çok API kopyası aynı sayacı ve aynı kilidi görsün diye Postgres'e taşındı.

-- Yorum, ses ve panel yenileme çağrıları: kullanıcı ve tür başına son 24 saatin kaydı.
create table public.call_log (
  user_id    uuid not null references auth.users (id) on delete cascade,
  kind       text not null,
  created_at timestamptz not null default now()
);
create index call_log_user_kind_idx on public.call_log (user_id, kind, created_at);
alter table public.call_log enable row level security;

-- Bir hak kullanır. Hak dolmuşsa false döner. Aynı kullanıcı ve türün çağrıları
-- advisory lock ile sıraya girer: yarışan iki istek aynı son hakkı alamaz.
create function public.take_call(p_user uuid, p_kind text, p_limit int, p_window_seconds int)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  perform pg_advisory_xact_lock(hashtextextended(p_user::text || ':' || p_kind, 0));
  delete from call_log
   where user_id = p_user and kind = p_kind and created_at < now() - make_interval(secs => p_window_seconds);
  if (select count(*) from call_log where user_id = p_user and kind = p_kind) >= p_limit then
    return false;
  end if;
  insert into call_log (user_id, kind) values (p_user, p_kind);
  return true;
end;
$$;

-- Kullanıcı başına tek panel ya da kaydetme işlemi. Süresi dolan kilit (çöken süreç) yenisine yer açar.
create table public.user_locks (
  user_id uuid primary key references auth.users (id) on delete cascade,
  token   text not null,
  until   timestamptz not null
);
alter table public.user_locks enable row level security;

-- Kilidi alır; başkası tutuyorsa ya da p_no_jobs ile kullanıcının aktif işi varsa false döner.
create function public.lock_user(p_user uuid, p_token text, p_seconds int, p_no_jobs boolean)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_no_jobs and exists (select 1 from jobs where user_id = p_user and status in ('queued', 'running')) then
    return false;
  end if;
  insert into user_locks (user_id, token, until)
  values (p_user, p_token, now() + make_interval(secs => p_seconds))
  on conflict (user_id) do update set token = excluded.token, until = excluded.until
   where user_locks.until < now();
  return found;
end;
$$;

revoke execute on function public.take_call(uuid, text, int, int) from public, anon, authenticated;
revoke execute on function public.lock_user(uuid, text, int, boolean) from public, anon, authenticated;
