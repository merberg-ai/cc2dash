from pathlib import Path
from app.settings import BASE_DIR, DATA_DIR, DB_PATH


def ensure_runtime_dirs() -> None:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
