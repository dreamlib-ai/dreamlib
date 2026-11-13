-- İş türleri artık kodda (backend/app/pipelines/registry.py) doğrulanır; yeni tür migration istemez.
-- Sütun yalnız biçimi korur: küçük harf, rakam ve alt çizgi.
alter table public.jobs drop constraint if exists jobs_kind_check;
alter table public.jobs add constraint jobs_kind_format check (kind ~ '^[a-z][a-z0-9_]{0,31}$');
