import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, constr
import io
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader


app = FastAPI(title="Sticker API")

# CORS: Frontend localhost:3000 için izin ver
allowed = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [o.strip() for o in allowed.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StickerRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=2)
    phone: constr(strip_whitespace=True, min_length=10)


CM_TO_INCH = 0.3937007874
DPI = 300
# Görsel oranına yakın: 76mm x 101mm (7.6cm x 10.1cm)
WIDTH_CM, HEIGHT_CM = 7.6, 10.1
CANVAS_SIZE = (int(WIDTH_CM * CM_TO_INCH * DPI), int(HEIGHT_CM * CM_TO_INCH * DPI))


QR_PAYLOAD_MODE = os.environ.get("QR_PAYLOAD_MODE", "tel").strip().lower()


def _sanitize_phone_to_e164(raw_phone: str) -> str:
    # Sadece + ve rakamları koru
    cleaned = ".".join(raw_phone.split())  # boşlukları kaldır
    allowed = "+0123456789"
    filtered = "".join(ch for ch in cleaned if ch in allowed)
    if filtered.startswith("+"):
        return filtered
    # Türkiye varsayılanı: +90 öne ekle
    return "+90" + filtered.lstrip("0")


def build_vcard(name: str, phone: str) -> str:
    # Android için geniş uyumluluk: vCard 2.1 + CRLF + UTF-8 charset
    phone_e164 = _sanitize_phone_to_e164(phone)
    crlf = "\r\n"
    return (
        "BEGIN:VCARD" + crlf +
        "VERSION:2.1" + crlf +
        f"N;CHARSET=UTF-8:;{name};;;" + crlf +
        f"FN;CHARSET=UTF-8:{name}" + crlf +
        f"TEL;CELL:{phone_e164}" + crlf +
        "END:VCARD" + crlf
    )


def build_mecard(name: str, phone: str) -> str:
    # Basit MECARD: İsim ve telefon
    phone_e164 = _sanitize_phone_to_e164(phone)
    return f"MECARD:N:{name};TEL:{phone_e164};;"


def build_qr_payload(name: str, phone: str) -> str:
    # Varsayılan: tel: (Android kamera ile en uyumlu)
    mode = QR_PAYLOAD_MODE
    if mode == "vcard":
        return build_vcard(name, phone)
    if mode == "mecard":
        return build_mecard(name, phone)
    # tel
    phone_e164 = _sanitize_phone_to_e164(phone)
    return f"tel:{phone_e164}"


def generate_qr_fit(data: str, max_w: int, max_h: int, extra_border_px: int = 0) -> Image.Image:
    # QR'ı panel boyutuna tam uygun integer modül boyutunda üret; yeniden örnekleme yapma
    # 1) Geçici QR oluştur, modül sayısını öğren
    probe = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=1, border=2)
    probe.add_data(data)
    probe.make(fit=True)
    modules = len(probe.get_matrix())  # kenardaki modüller hariç içerik sayısı
    border_modules = 2

    # 2) Maksimum kutu boyutu (box_size) piksel olarak hesapla
    # Toplam genişlik (px) = (modules + 2*border) * box_size
    avail_w = max(0, max_w - 2 * extra_border_px)
    avail_h = max(0, max_h - 2 * extra_border_px)
    box_by_w = avail_w // (modules + 2 * border_modules)
    box_by_h = avail_h // (modules + 2 * border_modules)
    box_size = int(min(box_by_w, box_by_h))

    # Çok küçükse okunurluk riskli; minimum 6 px modül boyutunu hedefle
    if box_size < 10:
        box_size = 10

    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=box_size, border=border_modules)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _load_bold_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "Arial Bold.ttf",
        "Arial-Bold.ttf",
        "Arial.ttf",
        "Arial Black.ttf",
        "/Library/Fonts/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraBold.ttf",
        "/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def compose_sticker(name: str, phone: str) -> Image.Image:
    W, H = CANVAS_SIZE
    canvas_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas_img)

    # Renkler
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    # Sarı tonu görseldeki doygunluğa yakın
    YELLOW = (242, 195, 0)

    # Dış çerçeve: siyah, yuvarlatılmış köşeler
    radius = int(min(W, H) * 0.0999)
    outer = (0, 0, W - 1, H - 1)
    draw.rounded_rectangle(outer, radius=radius, fill=BLACK)

    # Alt bant: sarı (yalnızca alt köşeler yuvarlatılmış görünsün)
    # Üst siyah alan / alt sarı bant oranı (referans görsele yakın: üst ~%72)
    split_y = int(H * 0.72)
    yellow_rect = (0, split_y, W - 1, H - 1)
    draw.rounded_rectangle(yellow_rect, radius=radius, fill=YELLOW)
    # Üst kenarı düzleştir (üst köşelerde eğri olmasın)
    draw.rectangle((0, split_y, W - 1, split_y + radius), fill=YELLOW)

    # Üst alana beyaz iç panel (QR için) - siyah alandan belirgin bir inset ile
    inset = int(W * 0.035)
    panel = (inset, inset, W - 1 - inset, split_y - inset)
    inner_radius = max(int(radius * 0.65), 0)
    draw.rounded_rectangle(panel, radius=inner_radius, fill=WHITE)

    # QR üret ve panel içine yerleştir
    vcard = build_qr_payload(name, phone)
    panel_w = panel[2] - panel[0]
    panel_h = panel[3] - panel[1]
    # QR etrafındaki beyaz çerçeveyi biraz daha daralt (QR'ı büyüt)
    qr_padding = int(min(panel_w, panel_h) * 0.035)
    max_qr_w = max(10, panel_w - 1 * qr_padding)
    max_qr_h = max(10, panel_h - 1 * qr_padding)

    # Panel için uygun boyutta, ölçekleme yapmadan QR üret
    qr_img = generate_qr_fit(vcard, max_qr_w, max_qr_h)
    qr_x = panel[0] + (panel_w - qr_img.width) // 2
    qr_y = panel[1] + (panel_h - qr_img.height) // 2
    canvas_img.paste(qr_img, (qr_x, qr_y))

    # Alt sarı bant üzerindeki metin (2 satır, kalın)
    lines = ["ARAÇ SAHİBİNE", "ULAŞMAK İÇİN KODU OKUT"]
    usable_w = W - int(W * 0.05)
    band_h = H - split_y
    # Dinamik font boyutu: daha da büyüt, okunaklı ve şık aralık
    font_size = int(H * 0.210)
    gap_ratio = 0.22
    while font_size > 10:
        font = _load_bold_font(font_size)
        max_line_w = 0
        line_h = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            max_line_w = max(max_line_w, bbox[2] - bbox[0])
            line_h = max(line_h, bbox[3] - bbox[1])
        gap = int(line_h * gap_ratio)
        total_h = len(lines) * line_h + (len(lines) - 1) * gap
        if max_line_w <= usable_w and total_h <= band_h - int(H * 0.006):
            break
        font_size -= 2
    # Metni dikey olarak ortala ve bir miktar yukarı taşı
    gap = int(line_h * gap_ratio)
    total_h = len(lines) * line_h + (len(lines) - 1) * gap
    start_y = split_y + (band_h - total_h) // 2 - int(H * 0.012)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        y = start_y + i * (line_h + gap)
        # İnce bir stroke ile net, kaliteli görünüm
        draw.text((x, y), line, font=font, fill=BLACK, stroke_width=1.5, stroke_fill=BLACK)

    return canvas_img


@app.post("/api/generate_sticker/png")
async def generate_sticker_png(req: StickerRequest):
    img = compose_sticker(req.name, req.phone)
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(DPI, DPI))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=sticker.png"},
    )


@app.post("/api/generate_sticker/pdf")
async def generate_sticker_pdf(req: StickerRequest):
    img = compose_sticker(req.name, req.phone)
    buf_img = io.BytesIO()
    img.save(buf_img, format="PNG", dpi=(DPI, DPI))
    buf_img.seek(0)

    pdf_buf = io.BytesIO()
    c = pdf_canvas.Canvas(pdf_buf, pagesize=(WIDTH_CM * cm, HEIGHT_CM * cm))
    c.drawImage(
        ImageReader(buf_img),
        0,
        0,
        width=WIDTH_CM * cm,
        height=HEIGHT_CM * cm,
        preserveAspectRatio=True,
        mask="auto",
    )
    c.showPage()
    c.save()
    pdf_buf.seek(0)

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sticker.pdf"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


