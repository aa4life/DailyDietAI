from sqlalchemy.orm import Session
from . import models_db, schemas
from datetime import date

# --- User CRUD ---
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models_db.User).offset(skip).limit(limit).all()

def get_user(db: Session, user_id: int) -> models_db.User | None:
    return db.query(models_db.User).filter(models_db.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate) -> models_db.User:
    data = user.model_dump(exclude_unset=True)
    if "nickname" in data and (data["nickname"] is None or not data["nickname"].strip()):
        data["nickname"] = None

    db_user = models_db.User(**data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if not db_user.nickname:
        db_user.nickname = f"User{db_user.id:03d}"
        db.commit()
        db.refresh(db_user)

    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> models_db.User | None:
    db_user = get_user(db, user_id)
    if db_user:
        update_data = user_update.model_dump(exclude_unset=True) # Pydantic v2: user_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

# --- Daily Record CRUD ---
def create_daily_record(db: Session, daily_record: schemas.DailyRecordCreate, user_id: int) -> models_db.DailyRecord:
    db_daily_record = models_db.DailyRecord(**daily_record.model_dump(), user_id=user_id) # Pydantic v2: daily_record.model_dump()
    db.add(db_daily_record)
    db.commit()
    db.refresh(db_daily_record)
    return db_daily_record

def get_daily_records_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[models_db.DailyRecord]:
    return db.query(models_db.DailyRecord).filter(models_db.DailyRecord.user_id == user_id).order_by(models_db.DailyRecord.record_date.desc()).offset(skip).limit(limit).all()

def get_daily_record_by_date(db: Session, user_id: int, record_date: date) -> models_db.DailyRecord | None:
    return db.query(models_db.DailyRecord).filter(models_db.DailyRecord.user_id == user_id, models_db.DailyRecord.record_date == record_date).first()

def get_or_create_daily_record(db: Session, user_id: int, record_data: schemas.DailyRecordCreate) -> models_db.DailyRecord:
    db_record = get_daily_record_by_date(db, user_id, record_data.record_date)
    if db_record:
        # Update existing record
        update_data = record_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_record, key, value)
        db.commit()
        db.refresh(db_record)
        return db_record
    else:
        # Create new record
        return create_daily_record(db, record_data, user_id)

