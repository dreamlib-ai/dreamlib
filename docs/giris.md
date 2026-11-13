# Giriş

Dreamlib Supabase Auth kullanır. Ana ekrandaki tek eylem Google ile devam et. Aynı düğme yeni kullanıcı için hesap oluşturur, mevcut kullanıcıyı hesabına alır. Elle e-posta alanı veya ayrı kayıt ekranı yok. Yeni hesapta gizlilik seçilir, eski hesapta kütüphane açılır. Kullanıcı bilgisi alınmadan ve oturum doğrulanmadan uygulamaya girilmez.

## Uygulama

- `frontend/src/session.ts`: PKCE kod değişimi, sunucudan kullanıcı doğrulama, otomatik token yenileme, yerel çıkış ve hata eşleme. Callback kodu URL'den temizlenir.
- `frontend/src/profile.ts`: yalnız onboarding ve görünürlük tercihi. Supabase kullanıcısının `user_metadata.dreamlib` alanında saklanır; yetkilendirme için kullanılmaz. Eski tarayıcı profilinin `onboarded` alanı giriş kanıtı değildir.
- `frontend/src/api.ts`: backend çağrılarında güncel erişim jetonu Bearer olarak gider. Anlat ekranı kayda gizlilik tercihini de gönderir. Gerçek backend JWT'yi doğrular ve rüyaları kullanıcı kimliğiyle süzer; mevcut API sözleşmesi korunur.
- Eski anonim oturum Google `linkIdentity` ile aynı kullanıcıya bağlanır. Kimlik başka hesaba aitse otomatik birleştirme veya kayıt taşıma yapılmaz.
- `frontend/tests/session.test.mjs`: Node 22.13+ ile `npm test`; SDK sınırları taklit edilerek oturum, callback, hata ve tercih davranışı kontrol edilir. Gerçek Google hesabıyla giriş testi değildir.

## Supabase durumu

25 Ekim 2026'da Google Cloud'da Dreamlib için bir Web OAuth istemcisi oluşturuldu; Google sağlayıcısı gerçek Supabase projesinde etkinleştirildi. Gerçek Google girişi, uygulamaya dönüş ve backend kütüphane yüklemesi tarayıcıda tamamlandı. E-posta arayüzü sonraya bırakıldı. `supabase/config.toml` yalnız hesap bağlama ve kesin yerel dönüş adreslerini yönetir. Site URL ve diğer sağlayıcı ayarları bu dosyada değiştirilmez. `.env` dosyaları okunmaz veya yeniden yazılmaz.

Supabase URL Configuration'da giriş dönüşü için izin verilen adresler:

```text
http://localhost:5173/?auth=callback
http://127.0.0.1:5173/?auth=callback
http://127.0.0.1:5174/?auth=callback
https://dreamlib.cenker.dev/?auth=callback
```

2 Kasım 2026: Site URL `https://dreamlib.cenker.dev` yapıldı ve canlı callback izin listesine eklendi; eski yerel adresler korundu. Canlı Google düğmesinden hesap seçimine geçiş doğrulandı; bu yayında gerçek hesapla dönüş tamamlanmadı.

## Google kurulumu

[Google Cloud Credentials](https://console.cloud.google.com/apis/credentials) içinde Dreamlib için bir Web application OAuth istemcisi oluştur. Google Auth Platform marka ve hedef kitle ayarlarını tamamla; uygulama test modundaysa giriş yapacak Google hesabını test kullanıcısı olarak ekle. Yalnız temel giriş kapsamları yeterli; Gmail, Drive veya Calendar izni gerekmiyor.

Authorized JavaScript origins:

```text
http://localhost:5173
http://127.0.0.1:5173
http://127.0.0.1:5174
```

Authorized redirect URI, frontend adresi değil Supabase callback'idir:

```text
https://<proje-ref>.supabase.co/auth/v1/callback
```

Oluşan Client ID ve secret'ı [Supabase Google sağlayıcısına](https://supabase.com/dashboard/project/_/auth/providers?provider=Google) ekleyip Google'ı etkinleştir. Bu bilgiler koda, git'e veya sohbet mesajına konmaz. Nonce kontrolü ve e-posta doğrulaması kapatılmaz. Supabase anahtarı Google OAuth istemcisi yerine kullanılamaz.

Sağlayıcı açıldığında uygulamadaki Google düğmesi ayarı gerçek servisten kontrol eder ve PKCE yönlendirmesini başlatır. İlk giriş gizlilik ekranına; kayıtlı hesap uygulamaya döner. Canlı hesapla dönüş tamamlandı. Genel kullanıma açılmadan önce yayın alan adı, marka/mahremiyet bağlantıları ve Google yayın durumu tamamlanmalı.

## Yerel önizleme

Normal checkout kendi frontend ortamını kullanır. Tasarım worktree'si ortam dosyası kopyalamadan mevcut checkout'un frontend ayarlarını Vite'ın çalışma zamanı yükleyicisiyle alır. `frontend/` içinden:

```powershell
node --input-type=module -e "import { createServer } from 'vite'; const server = await createServer({ envDir: '<ana-checkout>/frontend', server: { host: '127.0.0.1', port: 5174, strictPort: true } }); await server.listen(); server.printUrls();"
```

Backend `127.0.0.1:8080` üzerinde; Vite `/api` isteklerini oraya yönlendirir. Gerçek kimlik bilgileri test çıktısına veya loglara yazılmaz.

[Supabase Google giriş rehberi](https://supabase.com/docs/guides/auth/social-login/auth-google), [anonim hesabı bağlama](https://supabase.com/docs/guides/auth/auth-anonymous)

## Google marka görünümü

2 Kasım 2026: Google uygulaması production durumuna alındı; test kullanıcı listesiyle sınırlı değil. Branding içinde ad Dreamlib, home `/about`, privacy `/privacy`, terms `/terms`; `cenker.dev` authorized domain olarak eklendi. Public sayfalar ve onboarding bağlantıları uygulama ile birlikte yayımlanır. Google Search Console'da `https://dreamlib.cenker.dev/` sahipliği HTML dosyasıyla doğrulandı; `frontend/public/googled0f69616c566bbdb.html` kaldırılmamalı. Marka kontrolü sahiplik doğrulamasından sonra geçti ve Publish branding tamamlandı; Google Console “Your branding has been verified and is being shown to users” durumunda. Canlı Google girişi, callback kodunun temizlenmesi ve Anlat ekranına dönüş gerçek hesapla doğrulandı.

[Google marka doğrulama gereksinimleri](https://support.google.com/cloud/answer/15549049)
