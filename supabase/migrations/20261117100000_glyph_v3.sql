-- G2, ikinci tur: glyph@2 ikonlarının yarısı renkli çerçeve içinde kart üstüne çizildi, bazılarına "Dream journal"
-- yazıldı, iki anlamlı adlar yanlış çizildi (demir ütü olarak). glyph@3 somut tasvir ve tek krem zeminle çizer;
-- onaylı her sembol için bir kez yeniden çizim işi açılır (20261117090000 ile aynı kural: en eski e-postalı hesap,
-- priority -1, exclusive false). Backend bu sürüme geçtikten sonra uygulanmalı.
delete from public.jobs where kind = 'glyph' and status = 'queued';

insert into public.jobs (user_id, kind, input, total, dedupe_key, priority, exclusive)
select u.id, 'glyph', jsonb_build_object('entityId', e.id), 1, 'glyph:' || e.id || ':glyph@3', -1, false
  from public.entities e
  cross join (select id from auth.users where coalesce(email, '') <> '' order by created_at limit 1) u
 where e.kind = 'symbol' and e.status = 'approved' and e.glyph_prompt <> 'glyph@3'
on conflict do nothing;
