-- İsteğe bağlı bağlam: ruh hali (kullanıcı verdi ya da modelin tahmini) ve uyku.
alter table public.dreams add column mood text not null default '';
alter table public.dreams add column sleep text not null default '';
