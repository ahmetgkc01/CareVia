# Değişiklik Günlüğü

Carevia'daki kullanıcıya dönük önemli değişiklikler bu dosyada belgelenir.

Biçim [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/) yaklaşımını izler. Kararlı
sürümler [Semantic Versioning](https://semver.org/lang/tr/) ile etiketlenir.

## [Unreleased]

### Eklendi

- Admin, Doctor, Nurse, Secretary, Patient ve Auditor kategorileri için rol tabanlı erişim.
- Hasta, sağlık çalışanı, randevu ve kullanıcı yönetimi ekranları.
- Rol ve hasta bağlamına göre çalışan, güvenlik kuralları içeren Carevia AI Asistan.
- Yapılandırılmış alerji kayıtları ve toplu alerji sorguları.
- Sentetik demo verisi ve tarayıcı tabanlı Admin/Patient uçtan uca testleri.
- Production health endpoint'i, sürüm doğrulaması ve operasyon runbook'u.

### Değiştirildi

- Hasta araması ve AI Asistan hasta seçme akışı geliştirildi.
- Sentetik demo kullanıcı adları çeşitlendirildi.
- Kullanıcı kategorileri ve rol atama adımları README'de belgelendi.

### Güvenlik

- Rol kontrolleri yalnızca menülerde değil, Django API izin katmanında uygulanıyor.
- Oturum açma ve asistan isteklerine hız sınırı eklendi.
- Kimliği doğrulanmış API erişimleri, istek ve yanıt gövdeleri saklanmadan denetim kaydına alınıyor.
- Üretim bağımlılıkları güncellendi ve CI güvenlik taramaları eklendi.

## Sürüm yayınlama akışı

1. Gün içinde tamamlanan değişiklikleri `Unreleased` altında güncelleyin.
2. İlgili lint, test ve build kontrollerini çalıştırın.
3. Gün sonunda değişiklikleri açıklayıcı tek veya birkaç commit ile kaydedin.
4. Sunum ya da yayın için kararlı durumda `Unreleased` içeriğini tarihli bir sürüm başlığına taşıyın.
5. Aynı sürüm numarasıyla Git etiketi oluşturup etiketi GitHub'a gönderin.

İlk sunum sürümü için önerilen etiket `v0.1.0`'dır.
