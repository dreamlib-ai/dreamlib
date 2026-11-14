-- R1: rüya başına rıza kademeleri (karar 0007). `dreams.visibility` kademenin kendisidir: private (varsayılan),
-- collective (kimse görmez, anonim toplamlara ve eşleşmeye girer), public (dergi herkese açık). `consents` defteri
-- her verilen ve geri çekilen rızayı metin sürümüyle tutar; kademe yalnız set_dream_tier ile, tek işlemde değişir.

alter table public.dreams drop constraint if exists dreams_visibility_check;
alter table public.dreams add constraint dreams_visibility_check check (visibility in ('private', 'collective', 'public'));

create table public.consents (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users (id) on delete cascade,
  dream_id      uuid not null references public.dreams (id) on delete cascade,
  scope         text not null check (scope in ('collective', 'public')),
  text_version  text not null check (text_version <> ''),
  granted_at    timestamptz not null default now(),
  withdrawn_at  timestamptz
);

create index consents_dream_idx on public.consents (dream_id) where withdrawn_at is null;
create unique index consents_one_active on public.consents (dream_id, scope) where withdrawn_at is null;
create index consents_user_idx on public.consents (user_id, granted_at desc);

alter table public.consents enable row level security;

-- Kademeyi değiştirir: üst kapsamların rızasını geri çeker, yeni kademenin kapsamlarını (public collective'i de
-- içerir) bu metin sürümüyle yazar, eski sürümle verilmiş rızayı yeniler. Kademe public'in altına inerse herkese
-- açık dergi kapanır; sahibinin ayrıca açtığı link paylaşımı (G6) ayrı bir karardır, dokunulmaz.
-- Rüya kişinin değilse null döner.
create function public.set_dream_tier(p_user uuid, p_dream uuid, p_tier text, p_version text)
returns text language plpgsql security definer set search_path = public as $$
declare
  v_old text;
  v_scopes text[];
begin
  if p_tier not in ('private', 'collective', 'public') then
    raise exception 'unknown tier %', p_tier using errcode = '22023';
  end if;
  if p_tier <> 'private' and coalesce(p_version, '') = '' then
    raise exception 'consent text version required' using errcode = '22023';
  end if;
  select visibility into v_old from dreams where id = p_dream and user_id = p_user for update;
  if not found then
    return null;
  end if;
  v_scopes := case p_tier when 'public' then array['collective', 'public'] when 'collective' then array['collective'] else array[]::text[] end;
  update consents set withdrawn_at = now()
   where dream_id = p_dream and withdrawn_at is null
     and (not scope = any (v_scopes) or text_version <> p_version);
  insert into consents (user_id, dream_id, scope, text_version)
  select p_user, p_dream, s, p_version from unnest(v_scopes) s
   where not exists (select 1 from consents c where c.dream_id = p_dream and c.scope = s and c.withdrawn_at is null);
  update dreams set visibility = p_tier where id = p_dream;
  if p_tier <> 'public' then
    update magazines set visibility = 'private' where dream_id = p_dream and visibility = 'public';
  end if;
  return p_tier;
end $$;

revoke execute on function public.set_dream_tier(uuid, uuid, text, text) from public, anon, authenticated;

-- Onboarding'de herkese açık seçilmiş eski rüyalar o ekranın rızasıyla deftere girer.
insert into public.consents (user_id, dream_id, scope, text_version)
select d.user_id, d.id, s, 'onboarding@1'
  from public.dreams d cross join unnest(array['collective', 'public']) s
 where d.visibility = 'public';

-- Erişim kuralı sorgunun içinde: p_collective açıkken başkalarının yalnız collective ve public rüyaları da aday.
drop function public.dream_neighbors(uuid, uuid, text, text, int);
create function public.dream_neighbors(p_user uuid, p_dream uuid, p_kind text, p_model text, p_limit int default 10,
                                       p_collective boolean default false)
returns table (dream_id uuid, distance double precision)
language sql stable security definer set search_path = public, extensions as $$
  with q as (
    select e.embedding, e.dims from dream_embeddings e
      join dreams d on d.id = e.dream_id
     where e.dream_id = p_dream and e.kind = p_kind and e.model = p_model and d.user_id = p_user
  )
  select e.dream_id, (e.embedding <=> q.embedding)::double precision
    from dream_embeddings e
    join dreams d on d.id = e.dream_id
    cross join q
   where (d.user_id = p_user or (p_collective and d.visibility in ('collective', 'public')))
     and e.dream_id <> p_dream and e.kind = p_kind and e.model = p_model and e.dims = q.dims
   order by e.embedding <=> q.embedding
   limit least(greatest(p_limit, 1), 50);
$$;

drop function public.dream_chain(uuid, uuid, int);
create function public.dream_chain(p_user uuid, p_dream uuid, p_depth int default 2, p_collective boolean default false)
returns table (dream_id uuid, depth int, via uuid[])
language sql stable security definer set search_path = public as $$
  with recursive walk(dream_id, depth, via, seen) as (
    select p_dream, 0, array[]::uuid[], array[p_dream]
     where exists (select 1 from dreams where id = p_dream and user_id = p_user)
    union all
    select de2.dream_id, w.depth + 1, w.via || de1.entity_id, w.seen || de2.dream_id
      from walk w
      join dream_entities de1 on de1.dream_id = w.dream_id
      join dream_entities de2 on de2.entity_id = de1.entity_id and de2.dream_id <> w.dream_id
      join dreams d on d.id = de2.dream_id
                   and (d.user_id = p_user or (p_collective and d.visibility in ('collective', 'public')))
     where w.depth < least(greatest(p_depth, 1), 3) and not de2.dream_id = any (w.seen)
  )
  select distinct on (dream_id) dream_id, depth, via from walk where depth > 0 order by dream_id, depth;
$$;

revoke execute on function public.dream_neighbors(uuid, uuid, text, text, int, boolean) from public, anon, authenticated;
revoke execute on function public.dream_chain(uuid, uuid, int, boolean) from public, anon, authenticated;
