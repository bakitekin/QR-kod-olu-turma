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


def build_vcard(name: str, phone: str) -> str:
    phone_e164 = phone if phone.startswith("+") else "+90" + phone
    return (
        "BEGIN:VCARD\n"
        "VERSION:3.0\n"
        f"FN;CHARSET=UTF-8:{name}\n"
        f"TEL;TYPE=CELL:{phone_e164}\n"
        "END:VCARD"
    )


def generate_qr(data: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=None, error_correction=ERROR_CORRECT_H, box_size=12, border=0
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _load_bold_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "Arial Bold.ttf",
        "Arial-Bold.ttf",
        "Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
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
    # Üst siyah alan / alt sarı bant oranı
    split_y = int(H * 0.72)
    yellow_rect = (0, split_y, W - 1, H - 1)
    draw.rounded_rectangle(yellow_rect, radius=radius, fill=YELLOW)
    # Üst kenarı düzleştir (üst köşelerde eğri olmasın)
    draw.rectangle((0, split_y, W - 1, split_y + radius), fill=YELLOW)

    # Üst alana beyaz iç panel (QR için)
    inset = int(W * 0.008)
    panel = (inset, inset, W - 1 - inset, split_y - inset)
    inner_radius = max(radius - inset, 0)
    # Beyaz panel yerine siyah panel: QR etrafında beyaz görünmesin
    draw.rounded_rectangle(panel, radius=inner_radius, fill=BLACK)

    # QR üret ve panel içine yerleştir
    vcard = build_vcard(name, phone)
    qr_img = generate_qr(vcard)
    panel_w = panel[2] - panel[0]
    panel_h = panel[3] - panel[1]
    # QR etrafındaki boşluk sıfıra yakın olsun
    qr_padding = 1
    max_qr_w = panel_w - 2 * qr_padding
    max_qr_h = panel_h - 2 * qr_padding
    base_scale = min(max_qr_w / qr_img.width, max_qr_h / qr_img.height)
    # Çok az küçült (yaklaşık %3)
    scale = max(0.1, base_scale * 0.92)
    qr_img = qr_img.resize((int(qr_img.width * scale), int(qr_img.height * scale)), Image.LANCZOS)
    qr_x = panel[0] + (panel_w - qr_img.width) // 2
    qr_y = panel[1] + (panel_h - qr_img.height) // 2
    canvas_img.paste(qr_img, (qr_x, qr_y))

    # Alt sarı bant üzerindeki metin (3 satır, kalın)
    lines = ["ARAÇ SAHİBİNE", "ULAŞMAK İÇİN", "KODU OKUT"]
    usable_w = W - int(W * 0.20)
    band_h = H - split_y
    # Dinamik font boyutu: biraz daha büyük başlat ve yükseklik kısıtını gevşet
    font_size = int(H * 0.120)
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
        if max_line_w <= usable_w and total_h <= band_h - int(H * 0.04):
            break
        font_size -= 2
    # Metni dikey olarak ortala ve biraz aşağı kaydır (görseldeki gibi)
    gap = int(line_h * gap_ratio)
    total_h = len(lines) * line_h + (len(lines) - 1) * gap
    start_y = split_y + (band_h - total_h) // 2 + int(H * 0.005)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (W - line_w) // 2
        y = start_y + i * (line_h + gap)
        # İnce bir stroke ile yazı ağırlığını güçlendir
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


