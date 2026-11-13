-- Motorun düğüm katmanı (M1, docs/motor.md): düğüm türleri, düğümler, varyant adlar, rüya → düğüm.
-- Kenarlar, vektör tablosu ve arama fonksiyonları M2'de. Embedding modeli (L4) seçilmediği için
-- entities.embedding boyutsuz; HNSW indeksi model ve boyut sabitlenince ayrı migration'la gelir.
create extension if not exists vector with schema extensions;

create table public.entity_kinds (
  key         text primary key check (key ~ '^[a-z][a-z_]{1,31}$'),
  label_tr    text not null,
  label_en    text not null,
  description text not null default ''
);

insert into public.entity_kinds (key, label_tr, label_en, description) values
  ('symbol',      'Sembol',      'Symbol',      'Rüyada görülen nesne, varlık ya da imge'),
  ('theme',       'Tema',        'Theme',       'docs/arastirma/temalar.md çekirdeği ve adaylar'),
  ('emotion',     'Duygu',       'Emotion',     'Serbest etiket; HVdC beş sınıfına da eşlenir'),
  ('place',       'Yer',         'Place',       'Somut mekân'),
  ('action',      'Eylem',       'Action',      'Rüyadaki etkinlik'),
  ('archetype',   'Arketip',     'Archetype',   'Yorum katmanı'),
  ('character',   'Karakter',    'Character',   'Rol ve tanıdıklık (HVdC)'),
  ('interaction', 'Etkileşim',   'Interaction', 'Saldırgan, dostça, cinsel (HVdC)'),
  ('setting',     'Mekân türü',  'Setting',     'İç/dış, tanıdıklık (HVdC)'),
  ('outcome',     'Sonuç',       'Outcome',     'Başarı, başarısızlık, talih (HVdC)'),
  ('motif',       'Motif',       'Motif',       'Thompson dizini; lisans teyidine kadar boş (V6)');

create table public.entities (
  id           uuid primary key default gen_random_uuid(),
  kind         text not null references public.entity_kinds (key),
  key          text not null check (key ~ '^[a-z0-9][a-z0-9_.:-]{0,95}$'),  -- kanonik anahtar, dilden bağımsız
  labels       jsonb not null default '{}',   -- {"tr": "Kovalanmak", "en": "Being chased"}
  qid          text check (qid is null or qid ~ '^Q[0-9]+$'),  -- Wikidata
  status       text not null default 'candidate' check (status in ('candidate', 'approved', 'merged')),
  merged_into  uuid references public.entities (id),
  embedding    extensions.vector,
  embed_model  text not null default '',
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (kind, key),
  check ((status = 'merged') = (merged_into is not null)),
  check (merged_into is null or merged_into <> id)
);

create index entities_kind_status_idx on public.entities (kind, status);

create table public.entity_aliases (
  alias      text not null,                 -- küçük harfe çevrilmiş, kırpılmış yazım
  lang       text not null default '',
  entity_id  uuid not null references public.entities (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (alias, lang, entity_id)
);

create index entity_aliases_entity_idx on public.entity_aliases (entity_id);

create table public.dream_entities (
  dream_id   uuid not null references public.dreams (id) on delete cascade,
  entity_id  uuid not null references public.entities (id) on delete cascade,
  weight     real not null default 1 check (weight >= 0 and weight <= 1),
  source     text not null check (source in ('model', 'user')),
  extractor  text not null default '',      -- çıkarıcı ve prompt sürümü, ör. interpret@1
  quote      text not null default '',      -- anlatımdan birebir alıntı
  created_at timestamptz not null default now(),
  primary key (dream_id, entity_id, source)
);

create index dream_entities_entity_idx on public.dream_entities (entity_id);

-- Sözlük herkese açık bilgi değil ama hassas da değil; yine de yalnız API yazar ve okur.
-- dream_entities kişisel veridir: rüyanın sahibi dışında kimse okuyamaz (erişim kuralı M2 arama fonksiyonlarında).
alter table public.entity_kinds enable row level security;
alter table public.entities enable row level security;
alter table public.entity_aliases enable row level security;
alter table public.dream_entities enable row level security;
