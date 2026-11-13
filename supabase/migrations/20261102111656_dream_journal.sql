-- Owner-only journal data; existing dream RLS and grants remain in force.
begin;
alter table public.dreams
  add column if not exists journal jsonb not null default '{}'::jsonb,
  add column if not exists revision integer not null default 0;
alter table public.dreams add constraint dreams_journal_object check (jsonb_typeof(journal) = 'object');
alter table public.dreams add constraint dreams_revision_nonnegative check (revision >= 0);
notify pgrst, 'reload schema';
commit;
