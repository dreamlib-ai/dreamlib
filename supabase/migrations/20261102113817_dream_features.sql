begin;
alter table public.dreams add column if not exists features jsonb not null default '{}'::jsonb;
alter table public.dreams add constraint dreams_features_object check (jsonb_typeof(features) = 'object');
notify pgrst, 'reload schema';
commit;
