# Carevia AWS RDS ve pgAdmin bağlantısı

## RDS geliştirme veritabanı

- Sunucu: `carevia-development.cpqeqouycqzp.eu-central-1.rds.amazonaws.com`
- Port: `5432`
- Veritabanı: `carevia`
- Kullanıcı: `carevia_admin`
- SSL modu: `require`

Parola repository'de veya `.env` dosyasında tutulmaz. AWS Console'da RDS içindeki
`carevia-development` instance'ını açın, **Configuration** bölümündeki master credentials secret
bağlantısını izleyin ve parolayı AWS Secrets Manager üzerinden görüntüleyin.

## pgAdmin'e ekleme

1. pgAdmin 4'ü açın.
2. **Servers > Register > Server** seçin.
3. **General > Name** alanına `Carevia AWS RDS Development` yazın.
4. **Connection** sekmesinde yukarıdaki sunucu, port, veritabanı ve kullanıcıyı girin.
5. **Parameters** veya **SSL** sekmesinde SSL modunu `require` seçin.
6. Secrets Manager'dan alınan parolayı girip kaydedin.

Tablolar **Databases > carevia > Schemas > public > Tables** altında görünür.

pgvector ve kayıtları doğrulamak için:

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';

SELECT
    id,
    source_key,
    embedding_model,
    embedding_dimensions,
    vector_dims(embedding) AS stored_vector_dimensions,
    created_at
FROM assistant_knowledgechunk;
```

Bağlantı zaman aşımına uğrarsa evin genel IP adresi değişmiş olabilir. Yeni adresi
`infra/terraform/terraform.tfvars` içindeki `allowed_postgres_cidrs` listesine `/32` olarak yazıp
Terraform plan/apply çalıştırın. PostgreSQL portunu hiçbir zaman `0.0.0.0/0` adresine açmayın.
