"""
Converte imagens JPEG para WebP no diretório static/img.
Executar na VPS após deploy: python convert_images.py
Requer: Pillow (pip install Pillow)
"""
from pathlib import Path
from PIL import Image

IMG_DIR = Path("app/static/img")
TARGETS = ["logo-crystal-presentes.jpeg", "logo-crystalzinha.jpeg", "frente-loja.jpeg"]

for name in TARGETS:
    src = IMG_DIR / name
    if not src.exists():
        print(f"[SKIP] {name} não encontrado")
        continue
    dest = src.with_suffix(".webp")
    with Image.open(src) as img:
        img.save(dest, "WEBP", quality=85, method=6)
    print(f"[OK] {name} → {dest.name} ({dest.stat().st_size // 1024} KB)")

print("Concluído.")
