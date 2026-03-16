from collections.abc import Generator

from app.db import SessionLocal
from app.core.printer_manager import printer_manager


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_printer_manager():
    return printer_manager
