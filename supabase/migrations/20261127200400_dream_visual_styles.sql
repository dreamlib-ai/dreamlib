-- Keep the existing styles and allow the two new persisted booklets.
begin;
alter table public.dreams
  drop constraint dreams_style_check,
  add constraint dreams_style_check
    check (style in ('manga', 'illustration', 'collage', 'photographic', 'watercolor', 'stop_motion'));
commit;
