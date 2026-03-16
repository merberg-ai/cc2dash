from sqlalchemy.orm import Session

from app.models.db_models import AppSetting


class SettingsService:
    @staticmethod
    def get_value(db: Session, key: str, default: str | None = None) -> str | None:
        row = db.get(AppSetting, key)
        return row.value if row else default

    @staticmethod
    def set_value(db: Session, key: str, value: str | None) -> None:
        row = db.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=value)
            db.add(row)
        else:
            row.value = value
        db.flush()
