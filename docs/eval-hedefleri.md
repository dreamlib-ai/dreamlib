# Eval hedefleri

Eval yalnız "duygu doğru mu" sorusu değildir: motorun çıkardığı her alan ayrı bir parametre olarak ölçülür ve her birinin bir hedefi vardır. Makine okunur liste [`evals/targets.toml`](../evals/targets.toml); L6 eval iskeleti onu okur ve sonuç tablosunda her satırı hedefiyle yan yana koyar. Setler ve CI kuralı: [LLM](llm.md#eval).

## Hedef nasıl konur

- **İnsan tavanı olan alanlar:** HVdC'nin kendi kodlayıcıları aynı anlatıları bağımsız kodlayıp tam uyumu ölçmüştü (Domhoff 1996, Tablo 2.1; [kart](arastirma/notlar/olcum-llm-kodlama.md)). Modelden insanların kendi aralarındaki uyumu aşması beklenmez; hedef **insan uyumunun %90'ı**dır (`rule = "human_ratio"`). Eval seti de iki kişiyle kodlanır ve kendi insan uyumumuz ölçülünce bu tavan onunla değiştirilir.
- **Yayımlanmış model sonucu olan alanlar:** referans yazılır (ör. ince ayarlı BERT), hedef onun biraz altındadır çünkü biz ince ayar değil prompt kullanıyoruz.
- **Yalnız bize özgü alanlar:** tema, tür, bakış açısı gibi; ilk elle kodlamadan sonra gözden geçirilecek başlangıç hedefi konur.
- **Güvenlik ve dürüstlük:** yanlış pozitifin ya da kaçırmanın bedeli yüksek olan yerde hedef 0,95 ya da 1,00'dır.

## Parametreler

| Grup | Parametre | İnsan / referans | Hedef |
| --- | --- | --- | --- |
| Duygu | Beş duygu var/yok, makro F1 | BERT 0,85 | ≥ 0,80 |
| Duygu | Üzüntü F1 | BERT 0,77 | ≥ 0,70 |
| Duygu | Olumlu duygu (mutluluk) F1 | Hazır model 0,52 | ≥ 0,80 |
| Duygu | Tam uyum (kim, hangi duygu) | İnsan %63 | ≥ %57 |
| Duygu | Türkçe ile İngilizce farkı | — | ≤ 0,05 |
| Karakter | Varlık / cinsiyet / yaş / kimlik | İnsan %93 / %89 / %92 / %81 | İnsanın %90'ı |
| Karakter | Tüm alanlar birden | İnsan %76 | ≥ %68 |
| Etkileşim | Saldırganlık / dostluk / cinsellik | İnsan %54 / %61 / %64 (esnek: %72 / %70 / %71) | İnsanın %90'ı |
| Talih | Kötü talih / iyi talih | İnsan %71 / %83 | İnsanın %90'ı |
| Başarı | Başarı / başarısızlık | İnsan %56 / %100 | İnsanın %90'ı |
| Sahne | Mekân / nesne / etkinlik | İnsan %73 / %83 / %85 | İnsanın %90'ı |
| Betimleme | Değiştirici / zaman / olumsuzlama / yeme-içme | İnsan %81 / %75 / %96 / %82 | İnsanın %90'ı |
| Dreamlib | Tema çoklu etiket, makro F1 | — | ≥ 0,70 |
| Dreamlib | Tür, makro F1 | — | ≥ 0,75 |
| Dreamlib | Bakış açısı doğruluğu | — | ≥ 0,85 |
| Beyan | Lucid, tekrar, kâbus kesinliği | — | ≥ 0,95 |
| Beyan | Alıntının birebir geçmesi | — | %100 |
| Motif | Motif eşleşmesi kesinliği | — | ≥ 0,90 |
| Güvenlik | Hassas içerik duyarlılığı | — | ≥ 0,95 |
| Güvenlik | Talimat sızdırmaya direnç | — | %100 |
| Yorum | Her bağın dayanağı olması | — | ≥ %95 |
| Üretim | fal süre tahmini, ortalama mutlak yüzde hata | — | ≤ %25 |

## Kurallar

- Yeni bir alan çıkarıma girerse hedefi de buraya ve `targets.toml`'a girer; hedefsiz alan ürüne çıkmaz.
- Bir hedef düşürülecekse nedeni bu belgeye yazılır; sessizce gevşetilmez.
- Sonuç tablosu model, prompt sürümü ve tarihle saklanır; bir prompt ya da model değişikliği hiçbir parametrede hedefin altına düşürmüyorsa kabul edilir.
- İnsan uyumunun düşük olduğu alanlarda (saldırganlık, başarı) model sonucu tek başına "yanlış" sayılmaz; anlaşmazlık örnekleri elle incelenir.
