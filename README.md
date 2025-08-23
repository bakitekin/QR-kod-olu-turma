# vCard QR Kodlu Araç Sticker Üretim Sistemi

Bu proje, ad-soyad ve telefon bilgisiyle vCard içeren QR kod üretir ve 15x10 cm (300 DPI) sticker tasarımı oluşturur. Frontend (Next.js) üzerinden önizleme yapılabilir, PNG veya PDF olarak indirilebilir.

## Teknolojiler
- Frontend: Next.js (App Router) + TailwindCSS + TypeScript
- Backend: FastAPI (Python)
- Görsel/Export: qrcode, Pillow, ReportLab

## Geliştirme Ortamı

### Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt || pip install fastapi uvicorn qrcode pillow reportlab python-multipart
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Kullanım
1. Anasayfada `Ad Soyad` ve `Telefon Numarası` girin (örn. `Ahmet Yılmaz`, `5551234567` veya `+905551234567`).
2. "Sticker Oluştur (Önizleme)" ile görseli oluşturun.
3. "PNG Olarak İndir" veya "PDF Olarak İndir" butonlarıyla çıktıyı indirin.

## Notlar
- PDF çıktısı 15x10 cm sayfa boyutunda tek sayfa olarak üretilir.
- PNG çıktısı 300 DPI meta bilgisi ile kaydedilir.
- CORS, frontend `localhost:3000` için yapılandırılmıştır.
