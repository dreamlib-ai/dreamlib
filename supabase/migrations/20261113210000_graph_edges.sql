-- Motorun kenar katmanı (M2, docs/motor.md): ilişki kaydı, tipli ve kanıtlı kenarlar, rüya vektörleri
-- ve iki arama fonksiyonu. Arama bugün yalnız kişinin kendi rüyaları üzerinde; rızalı başka rüyalar
-- R1 ile (consents) aynı fonksiyonların erişim koşuluna eklenir.

create table public.relation_types (
  key            text primary key check (key ~ '^[a-z][a-z_]{1,31}$'),
  source_type    text not null check (source_type in ('dream', 'entity', 'user')),
  target_type    text not null check (target_type in ('dream', 'entity', 'user', 'event')),
  is_symmetric   boolean not null default false,  -- simetrikte kaynak < hedef tutulur, kenar bir kez yazılır
  scorer         text not null default '',        -- backend/app/engine/relations/ altındaki puanlayıcı
  scorer_version int not null default 1,
  description    text not null default ''
);

insert into public.relation_types (key, source_type, target_type, is_symmetric, description) values
  ('similar',      'dream',  'dream',  true,  'Bileşik benzerlik'),
  ('recurs',       'dream',  'dream',  false, 'Aynı kişide tekrar eden örüntü'),
  ('series',       'dream',  'dream',  false, 'Kullanıcının kendi kurduğu bağ'),
  ('co_occurs',    'entity', 'entity', true,  'Birlikte görülme (PMI)'),
  ('is_a',         'entity', 'entity', false, 'Sözlük hiyerarşisi'),
  ('same_as',      'entity', 'entity', true,  'Birleştirme'),
  ('rem',          'user',   'user',   true,  'Önbelleklenmiş kişi eşleşmesi'),
  ('evokes_motif', 'dream',  'entity', false, 'Masal ve mit motifi; alıntıyla doğrulanır'),
  ('day_residue',  'dream',  'event',  false, 'Uyanık hayattan iz');

create table public.edges (
  id           bigint generated always as identity primary key,
  relation     text not null references public.relation_types (key),
  source_id    uuid not null,
  target_id    uuid not null,
  user_id      uuid references auth.users (id) on delete cascade,  -- kişisel kenarın sahibi; sözlük kenarında boş
  weight       real not null check (weight >= 0 and weight <= 1),
  evidence     jsonb not null default '{}',   -- ortak semboller, bileşen puanları, örneklem
  algo_version int not null default 1,
  created_at   timestamptz not null default now(),
  check (source_id <> target_id),
  unique (relation, source_id, target_id, algo_version)
);

create index edges_source_idx on public.edges (source_id, relation);
create index edges_target_idx on public.edges (target_id, relation);
create index edges_user_idx on public.edges (user_id) where user_id is not null;

-- Simetrik ilişkilerde kenar tek yönde ve sıralı yazılır; ters kopya ikinci bir kenar açamaz.
create function public.edges_symmetric_order() returns trigger
language plpgsql set search_path = public as $$
begin
  if (select is_symmetric from relation_types where key = new.relation) and new.source_id > new.target_id then
    raise exception 'symmetric relation %: source_id must sort before target_id', new.relation;
  end if;
  return new;
end;
$$;

create trigger edges_symmetric_order before insert or update on public.edges
  for each row execute function public.edges_symmetric_order();

-- Rüya silinince kaynağı ya da hedefi o rüya olan kenarlar da gider.
create function public.edges_drop_dream() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  delete from edges where source_id = old.id or target_id = old.id;
  return old;
end;
$$;

create trigger dreams_drop_edges after delete on public.dreams
  for each row execute function public.edges_drop_dream();

create table public.dream_embeddings (
  dream_id   uuid not null references public.dreams (id) on delete cascade,
  kind       text not null check (kind in ('narrative', 'symbolic')),
  model      text not null,
  dims       int not null check (dims > 0),
  embedding  extensions.vector not null,
  created_at timestamptz not null default now(),
  primary key (dream_id, kind, model),
  check (extensions.vector_dims(embedding) = dims)
);

-- HNSW indeksi sabit boyut ister; embedding modeli (L4) seçilince o model için kısmi indeks eklenir:
--   create index on dream_embeddings using hnsw ((embedding::extensions.vector(N)) extensions.vector_cosine_ops)
--   where model = '<model>';

-- Kişinin kendi rüyaları arasında en yakın komşular (kosinüs uzaklığı; küçük = yakın).
create function public.dream_neighbors(p_user uuid, p_dream uuid, p_kind text, p_model text, p_limit int default 10)
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
   where d.user_id = p_user           -- erişim kuralı: R1 rızalı rüyaları buraya ekler
     and e.dream_id <> p_dream and e.kind = p_kind and e.model = p_model and e.dims = q.dims
   order by e.embedding <=> q.embedding
   limit least(greatest(p_limit, 1), 50);
$$;

-- Rüya → düğüm → başka rüya zinciri, derinlik en çok üç; yalnız kişinin kendi rüyaları.
create function public.dream_chain(p_user uuid, p_dream uuid, p_depth int default 2)
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
      join dreams d on d.id = de2.dream_id and d.user_id = p_user
     where w.depth < least(greatest(p_depth, 1), 3) and not de2.dream_id = any (w.seen)
  )
  select distinct on (dream_id) dream_id, depth, via from walk where depth > 0 order by dream_id, depth;
$$;

revoke execute on function public.dream_neighbors(uuid, uuid, text, text, int) from public, anon, authenticated;
revoke execute on function public.dream_chain(uuid, uuid, int) from public, anon, authenticated;
revoke execute on function public.edges_drop_dream() from public, anon, authenticated;

alter table public.relation_types enable row level security;
alter table public.edges enable row level security;
alter table public.dream_embeddings enable row level security;
