# Carevia AWS altyapısı

Bu Terraform paketi geliştirme ortamı için şunları oluşturur:

- Frankfurt (`eu-central-1`) bölgesinde ayrı bir VPC ve iki RDS alt ağı
- Yalnızca izin verilen `/32` adreslerine PostgreSQL erişimi veren güvenlik grubu
- Şifreli, tek AZ, 20 GiB gp3 diskli PostgreSQL 17 RDS instance'ı
- AWS Secrets Manager tarafından üretilen RDS yönetici parolası
- Varsayılan 7 günlük otomatik yedek, son snapshot ve silme koruması
- Aylık AWS bütçesi ve e-posta bildirimleri

Mevcut Lightsail instance'ı bilinçli olarak Terraform kapsamına alınmamıştır; böylece yanlışlıkla
yeniden oluşturulmaz veya silinmez. Lightsail erişimi gerekiyorsa statik genel IP adresi
`allowed_postgres_cidrs` listesine `/32` olarak eklenir.

## Kimlik doğrulama

AWS anahtarlarını repository'ye veya `terraform.tfvars` dosyasına yazmayın. `aws login` ile
tarayıcı tabanlı, geçici bir AWS CLI oturumu kullanın.

## Kullanım

1. `terraform.tfvars.example` dosyasını `terraform.tfvars` adıyla kopyalayın.
2. Bütçe e-postasını ve yalnızca güvenilen `/32` genel IP adreslerini girin.
3. `terraform init` çalıştırın.
4. `terraform plan` çıktısını inceleyin.
5. Yalnızca plan doğruysa `terraform apply` çalıştırın.
6. RDS oluşturulduktan sonra Django migration'larını çalıştırarak `vector` eklentisini ve tabloları
   oluşturun.

RDS genel bir DNS adresine sahip olsa da güvenlik grubu tüm internete açık değildir. Geliştirme
erişimi yalnızca `allowed_postgres_cidrs` listesindeki adreslerden sağlanır. Production ortamında
RDS private subnet'e taşınmalı ve uygulama katmanından erişilmelidir.

RDS'yi silmek bilinçli olarak iki aşamalıdır: önce `database_deletion_protection=false` uygulanır,
ardından silme planı ayrıca incelenir. `database_skip_final_snapshot=true` yalnızca tamamen
atılabilir ortamlarda kullanılmalıdır. Canlı altyapıya uygulanmadan önce her zaman `terraform plan`
çıktısını kontrol edin.

Terraform state dosyaları ve gerçek `*.tfvars` dosyaları Git dışında tutulur. State dosyasını
paylaşmayın; AWS kaynak kimliklerini ve hassas metadata'yı içerebilir.
