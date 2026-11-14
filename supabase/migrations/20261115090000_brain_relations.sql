-- BG1: rüya ↔ rüya ilişkileri, kişinin kendi rüyaları arasında, LLM'siz (backend/app/engine/relations.py).
-- Her tür beyin grafiğinde ayrı renkli bağdır; eşiğin altı yazılmaz, bağı olmayan rüya grafikte serbest süzülür.
insert into public.relation_types (key, source_type, target_type, is_symmetric, scorer, description) values
  ('shares_content', 'dream', 'dream', true, 'relations.content', 'Ortak sembol, karakter, yer ya da eylem; kişinin rüyalarında az görülen daha ağır'),
  ('shares_concept', 'dream', 'dream', true, 'relations.concept', 'Ortak tema, tür ya da deneyim'),
  ('shares_emotion', 'dream', 'dream', true, 'relations.emotion', 'Anlatımda aynı duygular (HVdC)'),
  ('near_in_time',   'dream', 'dream', true, 'relations.time', 'Birkaç gün arayla görülmüş')
on conflict (key) do nothing;

-- Kişinin bütün rüyaları, tarihleri ve düğüm bağları tek sorguda; bağı olmayan rüya da bir satırla gelir.
create function public.brain_links(p_user uuid)
returns table (dream_id uuid, dated date, entity_id uuid, kind text, key text, label text)
language sql stable security definer set search_path = public as $$
  select d.id,
         coalesce(nullif(d.journal->>'dreamedOn', '')::date, (d.created_at at time zone 'UTC')::date),
         e.id, e.kind, e.key, coalesce(e.labels->>'tr', e.labels->>'en', e.key)
    from dreams d
    left join dream_entities de on de.dream_id = d.id
    left join entities e on e.id = de.entity_id
   where d.user_id = p_user;
$$;

revoke execute on function public.brain_links(uuid) from public, anon, authenticated;

-- Mevcut rüyalar bir kez yeniden dizinlenir; `index` işi artık ilişkileri de yazar. Backend bu sürüme geçtikten
-- sonra uygulanmalı.
insert into public.jobs (user_id, kind, input, total, dream_id, dedupe_key, priority, exclusive)
select d.user_id, 'index', jsonb_build_object('dreamId', d.id, 'revision', d.revision), 1, d.id,
       d.id::text || ':bg1', -1, false
  from public.dreams d
on conflict do nothing;
