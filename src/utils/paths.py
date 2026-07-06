from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RESOURCE_DIR = PROJECT_ROOT / "resources"
UPLOAD_DIR = RESOURCE_DIR / "uploads"
DATABASE_PATH = DATA_DIR / "scom.db"


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def resource_path(*parts: str) -> Path:
    return RESOURCE_DIR.joinpath(*parts)
