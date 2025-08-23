"use client";

import React from "react";
import toast from "react-hot-toast";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

type FormState = {
  name: string;
  phone: string;
  errors: Partial<Record<"name" | "phone", string>>;
  loading: boolean;
  previewUrl?: string | null;
};

const validate = (values: { name: string; phone: string }) => {
  const errors: Partial<Record<"name" | "phone", string>> = {};
  if (!values.name || values.name.trim().length < 2) {
    errors.name = "Ad Soyad en az 2 karakter olmalı";
  }
  const phoneDigits = values.phone.replace(/\D/g, "");
  if (phoneDigits.length < 10) {
    errors.phone = "Telefon numarası en az 10 haneli olmalı";
  }
  return errors;
};

export default function Home() {
  const [state, setState] = React.useState<FormState>({
    name: "",
    phone: "",
    errors: {},
    loading: false,
    previewUrl: null,
  });

  const handleChange = (field: "name" | "phone") => (e: React.ChangeEvent<HTMLInputElement>) => {
    setState((s) => ({ ...s, [field]: e.target.value }));
  };

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const generatePreview = async () => {
    const errors = validate({ name: state.name, phone: state.phone });
    if (Object.keys(errors).length) {
      setState((s) => ({ ...s, errors }));
      toast.error("Lütfen formdaki hataları düzeltin.");
      return;
    }
    setState((s) => ({ ...s, loading: true, errors: {} }));
    try {
      const resp = await fetch(`${API_BASE}/api/generate_sticker/png`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: state.name, phone: state.phone }),
      });
      if (!resp.ok) throw new Error("İstek başarısız");
      const blob = await resp.blob();
      const objectUrl = URL.createObjectURL(blob);
      setState((s) => ({ ...s, previewUrl: objectUrl }));
      toast.success("Önizleme hazır");
    } catch (e) {
      toast.error("Sticker oluşturulamadı");
    } finally {
      setState((s) => ({ ...s, loading: false }));
    }
  };

  const download = async (format: "png" | "pdf") => {
    const errors = validate({ name: state.name, phone: state.phone });
    if (Object.keys(errors).length) {
      setState((s) => ({ ...s, errors }));
      toast.error("Lütfen formdaki hataları düzeltin.");
      return;
    }
    setState((s) => ({ ...s, loading: true }));
    try {
      const resp = await fetch(`${API_BASE}/api/generate_sticker/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: state.name, phone: state.phone }),
      });
      if (!resp.ok) throw new Error("İstek başarısız");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sticker.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error("İndirme başarısız");
    } finally {
      setState((s) => ({ ...s, loading: false }));
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">vCard QR Kodlu Araç Sticker Üretimi</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-300">Ad Soyad ve Telefon numaranızı girerek QR kodlu sticker oluşturun.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Input
          label="Ad Soyad"
          placeholder="Örn: Baki Tekin"
          value={state.name}
          onChange={handleChange("name")}
          error={state.errors.name}
        />
        <Input
          label="Telefon Numarası"
          placeholder="Örn: 5551234567 veya +905551234567"
          value={state.phone}
          onChange={handleChange("phone")}
          error={state.errors.phone}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={generatePreview} isLoading={state.loading}>
          Sticker Oluştur (Önizleme)
        </Button>
        <Button variant="secondary" onClick={() => download("png")} disabled={state.loading}>
          PNG Olarak İndir
        </Button>
        <Button variant="secondary" onClick={() => download("pdf")} disabled={state.loading}>
          PDF Olarak İndir
        </Button>
      </div>

      {state.previewUrl ? (
        <div>
          <h2 className="mb-2 text-lg font-medium">Önizleme</h2>
          <div className="rounded-lg border border-neutral-200 bg-black p-4 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
            {/* 15x10 cm oranı => 3:2 oran. Görsel alanını bu orana yakın gösteriyoruz */}
            <img src={state.previewUrl} alt="Sticker Önizleme" className="mx-auto h-auto max-h-[500px] w-full max-w-[750px] object-contain" />
          </div>
        </div>
      ) : null}
    </div>
  );
}
