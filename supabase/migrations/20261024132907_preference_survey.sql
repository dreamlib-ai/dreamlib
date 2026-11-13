-- Anonymous preference research. Only the server can read or write responses.
create table public.preference_responses (
  id uuid primary key,
  created_at timestamptz not null default now(),
  version text not null check (version = 'dreamlib-preference-v1'),
  seed bigint not null check (seed between 0 and 4294967295),
  started_at timestamptz not null,
  duration_ms bigint not null check (duration_ms >= 0),
  answers jsonb not null check (jsonb_typeof(answers) = 'array' and jsonb_array_length(answers) = 24),
  top_four text[] not null check (cardinality(top_four) = 4),
  winner text not null check (winner = top_four[1]),
  label_results jsonb not null check (jsonb_typeof(label_results) = 'array'),
  ranking jsonb not null check (jsonb_typeof(ranking) = 'array'),
  palette_ids text[] not null check (cardinality(palette_ids) between 1 and 2)
);
alter table public.preference_responses enable row level security;
revoke all on public.preference_responses from anon, authenticated;
grant select, insert, delete on public.preference_responses to service_role;

create function public.preference_survey_summary()
returns jsonb language sql stable security invoker set search_path = '' as $$
  select jsonb_build_object(
    'completed', (select count(*) from public.preference_responses),
    'latest', (select max(created_at) from public.preference_responses),
    'winners', coalesce((select jsonb_agg(t order by votes desc, id) from (
      select winner as id, count(*) as votes from public.preference_responses group by winner
    ) t), '[]'::jsonb),
    'shortlists', coalesce((select jsonb_agg(t order by votes desc, id) from (
      select s.id, count(*) as votes from public.preference_responses r
      cross join lateral unnest(r.top_four) as s(id) group by s.id
    ) t), '[]'::jsonb),
    'palettes', coalesce((select jsonb_agg(t order by votes desc, id) from (
      select p.id, count(*) as votes from public.preference_responses r
      cross join lateral unnest(r.palette_ids) as p(id) group by p.id
    ) t), '[]'::jsonb),
    'labels', coalesce((select jsonb_agg(t order by wins desc, label) from (
      select l->>'dimension' as dimension, l->>'label' as label,
        sum((l->>'wins')::integer) as wins,
        sum((l->>'opportunities')::integer) as opportunities,
        round(sum((l->>'wins')::numeric) / nullif(sum((l->>'opportunities')::numeric), 0), 4) as rate
      from public.preference_responses r cross join lateral jsonb_array_elements(r.label_results) l
      group by l->>'dimension', l->>'label'
    ) t), '[]'::jsonb)
  );
$$;
revoke all on function public.preference_survey_summary() from public, anon, authenticated;
grant execute on function public.preference_survey_summary() to service_role;
