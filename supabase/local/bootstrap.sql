-- Test yığınında Supabase depolama servisinin (storage-api) açılışta kurduğu tablonun yerini tutar.
-- Migration'lar yalnız storage.buckets'a kova ekliyor; dosya yükleme ve imzalama testleri sahte
-- istemcilerle koşuyor. Canlıda bu dosya çalıştırılmaz.
create table if not exists storage.buckets (
  id         text primary key,
  name       text not null unique,
  public     boolean not null default false,
  created_at timestamptz not null default now()
);
grant all on storage.buckets to postgres;
