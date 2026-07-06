from pathlib import Path
from shutil import copy2
from uuid import uuid4

from src.utils.paths import UPLOAD_DIR, ensure_directories


SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def store_part_image(source_path: str | None) -> str | None:
    if not source_path:
        return None

    source = Path(source_path)
    if not source.exists():
        raise ValueError("O arquivo de imagem selecionado não existe.")
    if source.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError("Formato de imagem não suportado.")

    ensure_directories()
    if source.parent.resolve() == UPLOAD_DIR.resolve():
        return str(source)

    destination = UPLOAD_DIR / f"{uuid4().hex}{source.suffix.lower()}"
    copy2(source, destination)
    return str(destination)
