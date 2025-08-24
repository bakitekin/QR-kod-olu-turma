import { NextRequest } from "next/server";

const ALLOWED_FORMATS = new Set(["png", "pdf"]);

export async function POST(
  req: NextRequest,
  { params }: { params: { format: string } }
) {
  const format = (params?.format || "").toLowerCase();
  if (!ALLOWED_FORMATS.has(format)) {
    return new Response(
      JSON.stringify({ error: "Geçersiz format" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  const apiBase = process.env.API_BASE || process.env.BACKEND_API_BASE || "";
  if (!apiBase) {
    return new Response(
      JSON.stringify({ error: "Sunucu yapılandırılmadı (API_BASE)" }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return new Response(
      JSON.stringify({ error: "Geçersiz JSON gövdesi" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  const payload = body as { name?: string; phone?: string };
  if (!payload?.name || !payload?.phone) {
    return new Response(
      JSON.stringify({ error: "'name' ve 'phone' alanları zorunlu" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  const upstream = await fetch(`${apiBase}/api/generate_sticker/${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: payload.name, phone: payload.phone }),
  });

  const contentType =
    upstream.headers.get("content-type") ||
    (format === "png" ? "image/png" : "application/pdf");

  const buffer = await upstream.arrayBuffer();
  return new Response(buffer, {
    status: upstream.status,
    headers: { "Content-Type": contentType },
  });
}


