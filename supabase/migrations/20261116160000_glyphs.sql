-- G1: her onaylı sembol düğümünün tek üslupta küçük ikonu; rüya başına değil, düğüm başına bir kez üretilir.
-- İkonlar kimsenin kişisel verisi değildir; herkese açık `glyphs` kovasında `<düğüm kimliği>.webp` olarak durur.
insert into storage.buckets (id, name, public)
values ('glyphs', 'glyphs', true)
on conflict (id) do nothing;

alter table public.entities add column glyph_path text not null default '';
