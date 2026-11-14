-- BG4: beyin grafiğinde kişinin kendi kararları. `series` (mevcut) iki rüyayı elle bağlar; `hidden` puanlayıcının
-- kurduğu bir bağı o kişi için gizler. İkisi de kenar olarak user_id ile yazılır, uçlar sıralı tutulur.
insert into public.relation_types (key, source_type, target_type, is_symmetric, scorer, description) values
  ('hidden', 'dream', 'dream', true, '', 'Kişinin beyin grafiğinde gizlediği bağ')
on conflict (key) do nothing;
