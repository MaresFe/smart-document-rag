# Smart Document RAG

Smart Document RAG; belgeleri yerel olarak indeksleyen, seçilen kaynaklar üzerinden Türkçe soru-cevap yapan ve cevap dayanaklarını kullanıcıya gösteren self-hosted bir RAG uygulamasıdır. Uygulama veriyi dış bir LLM hizmetine göndermeden PostgreSQL/pgvector, Ollama, FastAPI ve React ile çalışır.

## Özellikler

- PDF, DOCX, TXT, CSV, XLSX, PNG, JPG ve JPEG yükleme
- Taranmış PDF ve görseller için Türkçe/İngilizce OCR
- Çok dilli embedding ve pgvector ile anlamsal arama
- Seçili belgelere bağlı, kaynak gösteren Türkçe yanıtlar
- Sohbet ve belge bazında kullanıcı veri izolasyonu
- Davetle üyelik, parola sıfırlama ve güvenli oturum çerezi
- Yönetici panelinden davet ve hesap etkinleştirme/pasifleştirme
- Hız sınırlama, güvenlik başlıkları, trusted-host ve CORS kontrolleri
- Backend, frontend, güvenlik ve RAG kalite regresyon testleri

## Mimari

| Servis | Görev |
|---|---|
| Frontend / Nginx | React arayüzünü sunar, API isteklerini backend'e iletir |
| FastAPI | Kimlik doğrulama, belge işleme, retrieval ve sohbet API'si |
| PostgreSQL + pgvector | Kullanıcı, belge, sohbet ve embedding verileri |
| Ollama | `qwen3.5:2b` yanıt modeli |
| Tesseract | Görsel ve taranmış PDF OCR işlemleri |

## Gereksinimler

- 64 bit Linux, macOS veya Windows üzerinde Docker Desktop/Engine
- Docker Compose v2 veya daha yeni sürüm
- En az 8 GB RAM; 12-16 GB daha rahat kullanım sağlar
- İlk kurulum indirmeleri için yaklaşık 10 GB boş disk ve internet bağlantısı

İlk açılışta Docker imajları, Ollama modeli ve embedding modeli indirilir. Bu nedenle ilk başlangıç sonraki açılışlardan belirgin biçimde uzun sürebilir.

## Hızlı başlangıç

### 1. Ortam dosyasını oluştur

```bash
cp .env.example .env
```

Güvenli bir uygulama anahtarı üret:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Çıktıyı `.env` içindeki `AUTH_SECRET_KEY` değerine yaz. `POSTGRES_PASSWORD` değerini de değiştir. Veritabanı bağlantı adresinde kullanılacağı için yalnızca harf, rakam, `_` ve `-` içeren uzun bir parola seç.

Başka bir bilgisayardan sunucu IP'siyle erişilecekse aşağıdaki değerleri sunucunun IP'sine göre düzenle:

```dotenv
PUBLIC_HOST=192.168.1.50
PUBLIC_BASE_URL=http://192.168.1.50:8080
```

### 2. Sistemi başlat

```bash
docker compose up --build -d
docker compose ps
```

İlk model indirmelerini takip etmek için:

```bash
docker compose logs -f ollama-model backend
```

`backend` ve `frontend` servisleri healthy/started olduğunda arayüzü aç:

- Uygulama: <http://localhost:8080>
- API dokümanı: <http://localhost:8080/docs>

### 3. İlk yöneticiyi oluştur

Temiz kurulum invite-only modda başladığından ilk yönetici terminalden bir kez oluşturulur:

```bash
docker compose exec backend \
  python scripts/manage_users.py \
  bootstrap-admin admin@example.com \
  --full-name "Sistem Yöneticisi"
```

Parola terminalde görünmeden iki kez sorulur. Yönetici hesabıyla giriş yaptıktan sonra üst menüdeki kullanıcı yönetimi ekranından diğer kullanıcıları davet edebilirsin.

`EMAIL_DELIVERY_MODE=console` kullanıldığında davet ve parola sıfırlama bağlantıları backend loguna yazılır:

```bash
docker compose logs backend | grep -E 'invite|reset|http'
```

### 4. Kurulumu doğrula

```bash
python3 scripts/self_hosted_check.py
```

Beklenen sonuç dört kontrolün de `GECTI` olmasıdır.

## Günlük kullanım

```bash
# Durum
docker compose ps

# Loglar
docker compose logs -f backend frontend

# Durdur
docker compose down

# Yeniden başlat
docker compose up -d

# Yeni kodu aldıktan sonra güncelle
git pull --ff-only
docker compose up --build -d
```

`docker compose down` verileri silmez. Bütün kalıcı verileri de kaldırmak için `docker compose down -v` kullanılır; bu işlem belgeleri, hesapları, sohbetleri ve indirilen modelleri geri alınamayacak biçimde siler.

## Yedekleme

Veritabanı yedeği:

```bash
docker compose exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > smart-document-rag.sql
```

Yüklenen belgeler `uploads_data`, veritabanı `postgres_data`, Ollama modeli `ollama_data` adlı Docker volume'larında tutulur. Sunucu yedeğine bu volume'lar da dahil edilmelidir.

## Geliştirme ve test

Backend:

```bash
cd backend
source .venv/bin/activate
python -m pytest -v --cov=app --cov-report=term-missing
```

Frontend:

```bash
cd frontend
npm ci
npm run test:coverage
npm run lint
npm run build
npm audit --audit-level=high
```

RAG kalite değerlendirmesi:

```bash
docker compose exec backend \
  python evaluation/run_rag_quality.py \
  --base-url http://127.0.0.1:8000 \
  --email admin@example.com \
  --model-label qwen3.5-2b-release
```

## İnternete açık sunucu

Varsayılan yapı yerel ağ ve değerlendirme kurulumu içindir. İnternete açmadan önce bir HTTPS reverse proxy ve gerçek SMTP hesabı yapılandırılmalıdır. Ardından en az şu değerler değiştirilmelidir:

```dotenv
APP_ENVIRONMENT=production
PUBLIC_HOST=rag.example.com
PUBLIC_BASE_URL=https://rag.example.com
AUTH_COOKIE_SECURE=true
SECURITY_HSTS_ENABLED=true
EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=smtp.example.com
SMTP_USERNAME=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=noreply@example.com
```

Backend portu ve PostgreSQL portu dış dünyaya yayınlanmaz; dış erişim yalnızca frontend/Nginx portundan yapılır.

## Lisans ve dağıtım notu

Bu depo self-hosted kullanım için hazırlanmıştır. Üretim ortamında işletim sistemi güncellemeleri, HTTPS sertifikası, SMTP hesabı, yedekleme ve sunucu erişim politikaları kurulumu yapan kurumun sorumluluğundadır.
