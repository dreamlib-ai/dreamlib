-- M7: kolektif toplam. Bir sembolün rızalı (collective, public) rüyalarda en çok hangi duyguyla (HVdC sınıfı,
-- index işinin duygu düğümleri) birlikte göründüğü; yalnız en az beş farklı kişinin rüyasından (karar 0007).
-- Metin, başlık ya da rüya kimliği dönmez; yalnız sayılar.
create function public.symbol_emotions(p_entities uuid[], p_min_people int default 5)
returns table (entity_id uuid, emotion text, dreams int, people int)
language sql stable security definer set search_path = public as $$
  with shared as (
    select de.entity_id, d.id as dream_id, d.user_id
      from dream_entities de join dreams d on d.id = de.dream_id
     where de.entity_id = any (p_entities) and d.visibility in ('collective', 'public')
  ), people as (
    select entity_id from shared group by entity_id having count(distinct user_id) >= greatest(p_min_people, 5)
  ), felt as (
    select s.entity_id, e.key as emotion, count(distinct s.dream_id)::int as dreams, count(distinct s.user_id)::int as people
      from shared s
      join people p on p.entity_id = s.entity_id
      join dream_entities de on de.dream_id = s.dream_id
      join entities e on e.id = de.entity_id and e.kind = 'emotion' and e.key like 'hvdc.%'
     group by s.entity_id, e.key
  )
  select distinct on (entity_id) entity_id, emotion, dreams, people
    from felt where people >= greatest(p_min_people, 5)
   order by entity_id, dreams desc, emotion;
$$;

revoke execute on function public.symbol_emotions(uuid[], int) from public, anon, authenticated;
