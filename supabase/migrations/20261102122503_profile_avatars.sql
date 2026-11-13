begin;
alter table public.profiles
  add column if not exists display_name text not null default '',
  add column if not exists avatar jsonb not null default '{}'::jsonb,
  add column if not exists avatar_path text not null default '',
  add column if not exists avatar_revision integer not null default 0;
alter table public.profiles add constraint profiles_avatar_object check(jsonb_typeof(avatar)='object');
alter table public.profiles add constraint profiles_avatar_revision_nonnegative check(avatar_revision>=0);
alter table public.profiles add constraint profiles_avatar_owner_path check(
  avatar_path='' or (length(avatar_path)<=300 and avatar_path ~ ('^'||id::text||'/[a-zA-Z0-9/_-]+\.(png|jpg|webp)$'))
);
-- Existing owner-only RLS remains unchanged; no public profile access is introduced here.
notify pgrst, 'reload schema';
commit;
