Env Değişkenleri

- ALLOWED_ORIGINS: CORS için virgülle ayrılmış domain listesi (örn. https://site.netlify.app,https://admin.domain.com)

Çalıştırma

source .venv/bin/activate
ALLOWED_ORIGINS="http://localhost:3000" uvicorn main:app --host 0.0.0.0 --port 8000

