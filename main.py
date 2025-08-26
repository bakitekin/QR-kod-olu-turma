import os

# Render 'uvicorn main:app' komutu kökteki 'main' modülünü bekliyor.
# Backend uygulamasını yeniden dışa aktaralım.
from backend.main import app  # noqa: F401


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))


