# Yorum karşılaştırması

Sekiz sentetik Türkçe rüya, yorum metninin anlatıya bağlı kalmasını ölçmek için sabit tutulur. Her örneğin `review` alanı elle değerlendirme ölçütüdür. Duygu etiketlerinin ve açık rüya deneyimlerinin korunmasına da bakılır.

```powershell
backend/.venv/Scripts/python.exe evals/interpret/run.py --live --output yorum-once.jsonl
```

Çalıştırmak sekiz ücretli model çağrısı yapar. OpenRouter ayarlarını çalışma ortamından alır. Aynı modelle önceki ve sonraki prompt için ayrı çıktı yolu ver. Her satır prompt sürümünü, dönen modeli, süreyi, sağlayıcının bildirdiği maliyeti ve yapılandırılmış yanıtı taşır. Birinde model değişirse metin farkını yalnız prompta atfetme.

İstatistik ve metin karşılaştırması, geçmiş rüyası olmayan yeni bir kullanıcıya yakın koşul sağlar. Sözlük, geçmiş, kayıt veya değerlendirme sonrası düzeltmeler bu deneye girmez. İlgili canlı akış ve kişisel bağlam ayrıca doğrulanır.

27 Kasım 2026 karşılaştırması, her sürüm için sekiz örnek ve aynı dönen model (`openai/gpt-6-luna`). İki sürüm de sekiz geçerli yanıt verdi. Medyan süre `interpret@2` için 5,92 sn, `interpret@3` için 5,26 sn. Tek koşu, performans iddiası için yeterli değildir.

- Merdivende önceki yorum değişim ve ilerleme varsaydı; yeni yorum ayrıntı yetersizliğini korudu.
- Denizli tren rüyasında önceki yorum, gerçek hayatta bir değişim isteği çıkardı. Yeni yorum korku ile sakin denizin aynı sahnede olmasına dayandı.
- Kâbus örneğinde kısa destek cümlesi ve birebir kâbus beyanı kaldı. Duygu belirtilmeyen bir örnekte duygu listesi boş kaldı. Defterde yazan talimat iki sürümde de uygulanmadı.
- Merdiven, kapı ve defter örneklerinde yeni yorum yer yer anlatıyı tekrar ediyor. Anlatım kalitesi için ayrıca kullanıcı değerlendirmesi gerekir.
