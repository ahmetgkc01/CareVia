# Carevia sunum akışı

Bu akış, Carevia'nın sentetik verilerle hazırlanan `v0.1.0` demo sürümünü yaklaşık 6–8 dakikada
anlatmak için kullanılabilir.

## Sunumdan önce

1. Veritabanını başlatın: `docker compose up -d database`
2. Backend'i başlatın: `cd backend && python manage.py runserver`
3. Frontend'i başlatın: `cd frontend && npm run dev`
4. Gerekirse demo hesaplarını yenileyin:

   ```bash
   cd backend
   python manage.py seed_roles
   python manage.py seed_e2e --password "sunum-icin-yerel-parola"
   ```

5. Admin hesabıyla giriş yapın ve yalnızca sentetik kayıtların bulunduğunu doğrulayın.
6. Tarayıcı yakınlaştırmasını `%100`, dili Türkçe ve pencereyi masaüstü boyutunda tutun.

## Anlatım sırası

### 1. Ürün özeti — 30 saniye

“Carevia; hasta, sağlık çalışanı, randevu ve kullanıcı süreçlerini rol tabanlı yetkilendirmeyle
yöneten çift dilli bir sağlık yönetimi portföy uygulamasıdır. Bu demoda yalnızca sentetik veri
kullanıyorum.”

Giriş ekranında uygulamanın sade yapısını gösterin ve `e2e_admin` hesabıyla oturum açın.

### 2. Genel Bakış — 90 saniye

- Hasta, yaklaşan randevu, doktor ve hemşire sayılarını gösterin.
- Sentetik veri uyarısını özellikle belirtin.
- **Geliştirme ve sürüm geçmişi** kartında kalite kontrolü → changelog → commit → GitHub push
  zincirini anlatın.
- Güncel sürüm kodunun hem kartta hem sağ alt köşede göründüğünü gösterin.
- Commit kodlarından birinin GitHub'daki ilgili kayda bağlandığını belirtin.

Kısa açıklama: “Commit, projenin o andaki değişikliklerini açıklamasıyla birlikte kaydeden bir
kontrol noktasıdır. Böylece neyin ne zaman değiştiğini gösterebiliyorum.”

### 3. Hasta ve randevu yönetimi — 90 saniye

- **Hastalar** ekranında `E2E Patient` araması yapın.
- Kayıt görüntüleme ve düzenleme aksiyonlarını gösterin; sunum sırasında veriyi değiştirmeyin.
- **Randevular** ekranında tarih ve durum bazlı kayıtları gösterin.
- Yetkilerin yalnızca menüde değil, backend API katmanında da uygulandığını söyleyin.

### 4. Carevia AI Asistan — 2 dakika

- **AI Asistan** ekranını açın ve tıbbi güvenlik uyarısını gösterin.
- “Alerjisi olan hastaları listele” sorusunu gönderin.
- Yanıtın sentetik, yetkili kayıtlarla sınırlı ve kaynak bilgili olduğunu belirtin.
- Hasta bağlamı seçildiğinde yalnızca seçilen hastanın yetkili bilgilerinin sorgulandığını anlatın.
- Asistanın teşhis koymadığını, ilaç/doz veya tedavi değişikliği önermediğini vurgulayın.

### 5. Rol tabanlı erişim — 60 saniye

README'deki kullanıcı kategorileri tablosunu açın. Admin, Doctor, Nurse, Secretary, Patient ve
Auditor rollerinin farklı erişim seviyelerini kısaca karşılaştırın. Patient rolünün yalnızca kendi
bağlı hasta kaydını ve randevularını gördüğünü söyleyin.

### 6. Versiyon kontrolü ve kapanış — 60 saniye

- GitHub'da `v0.1.0` sürümünü ve `CHANGELOG.md` dosyasını gösterin.
- Gün sonu otomasyonunun her gün 21.00'de test ve build başarılıysa commit oluşturup `main`
  dalına gönderdiğini anlatın.
- “Bu yapı hem çalışan ürünü hem de geliştirme disiplinini aynı sunumda görünür kılıyor” diyerek
sunumu tamamlayın.

## Sorulabilecek kısa sorular

- **Gerçek hasta verisi var mı?** Hayır; repository ve demo yalnızca sentetik veri kullanır.
- **Commit ne işe yarıyor?** Değişikliklerin açıklamalı ve geri izlenebilir bir kontrol noktasıdır.
- **Versiyon nerede görülüyor?** Genel Bakış kartında, uygulamanın sağ alt köşesinde ve GitHub
  Releases bölümünde.
- **Otomasyon hata alırsa ne olur?** Commit veya push yapmaz; hata kaydını `automation/logs/`
  altında bırakır.
- **AI tıbbi karar veriyor mu?** Hayır; asistan bilgi erişimini kolaylaştırır, teşhis veya tedavi
  önerisi üretmez.

## Görselleri yenileme

Backend ve frontend çalışırken, sentetik E2E verisi hazırlandıktan sonra:

```bash
cd frontend
CAREVIA_E2E_PASSWORD="sunum-icin-yerel-parola" npm run capture:screenshots
```

Komut giriş, Genel Bakış, hasta yönetimi ve AI Asistan görsellerini `docs/images/` klasöründe
yeniler.
