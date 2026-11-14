-- M8: her mevcut rüya bir kez yeniden dizinlenir; `index` işi artık yorumun `objects` ve `features` alanlarını da
-- `dream_entities`'e açar (backend/app/pipelines/fields.py). İşler arka planda, kullanıcı işlerinin ardında
-- (priority -1) ve kimseyi kilitlemeden (exclusive false) yürür; aynı rüya için ikinci kez eklenmez.
-- Backend bu sürüme geçtikten sonra uygulanmalı, yoksa işleri eski kod alır.
insert into public.jobs (user_id, kind, input, total, dream_id, dedupe_key, priority, exclusive)
select d.user_id, 'index', jsonb_build_object('dreamId', d.id, 'revision', d.revision), 1, d.id,
       d.id::text || ':m8', -1, false
  from public.dreams d
on conflict do nothing;
