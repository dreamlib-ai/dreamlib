-- G2: düğüm ikonunun hangi şablon sürümüyle çizildiği; yeni sürüm (glyph@2: nesne çerçeveyi doldurur) eskileri
-- yeniden çizdirir. Onaylı her sembol için bir kez glyph@2 işi kuyruğa girer. İkonlar kimsenin kişisel verisi
-- değildir ama `jobs.user_id` zorunlu: işler en eski e-postalı (anonim olmayan) hesaba, yani bakımcıya yazılır, arka
-- planda (priority -1) ve kimseyi kilitlemeden (exclusive false) yürür, günlük haktan düşmez. Hesap yoksa iş eklenmez;
-- düğümler bir rüyada geçince index işi yine kuyruğa koyar. Backend bu sürüme geçtikten sonra uygulanmalı.
alter table public.entities add column glyph_prompt text not null default '';
update public.entities set glyph_prompt = 'glyph@1' where glyph_path <> '';

insert into public.jobs (user_id, kind, input, total, dedupe_key, priority, exclusive)
select u.id, 'glyph', jsonb_build_object('entityId', e.id), 1, 'glyph:' || e.id || ':glyph@2', -1, false
  from public.entities e
  cross join (select id from auth.users where coalesce(email, '') <> '' order by created_at limit 1) u
 where e.kind = 'symbol' and e.status = 'approved' and e.glyph_prompt <> 'glyph@2'
on conflict do nothing;
