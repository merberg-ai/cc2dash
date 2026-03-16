from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cc2dash.db"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

APP_TITLE = "cc2dash"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8008
DEFAULT_UI_REFRESH_SECONDS = 3
