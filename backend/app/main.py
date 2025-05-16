from fastapi import FastAPI, Depends, HTTPException, Path, Body, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import logging
import os # <--- 新增這一行

from . import crud, models_db, schemas, services
from .database import SessionLocal, engine, get_db

# 創建資料庫表 (如果不存在)
# 在生產環境中，您可能希望使用 Alembic 進行資料庫遷移管理
models_db.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- User Endpoints ---
@app.post("/users/", response_model=schemas.User, tags=["Users"], summary="創建新使用者")
def create_user(user: schemas.UserCreate = Body(...), db: Session = Depends(get_db)):
    # MVP 階段，我們可以假設只有一個使用者，或者每次都創建一個新的。
    # 為了簡化，這裡允許創建多個使用者，前端可以選擇記住 user_id。
    # 檢查是否有重複的邏輯可以後續添加 (例如基於 email 或 username，但目前模型沒有這些欄位)
    logger.info(f"Attempting to create user with data: {user.model_dump()}")
    db_user = crud.create_user(db=db, user=user)
    logger.info(f"User created with ID: {db_user.id}")
    return db_user

@app.get("/")
def index():
    return FileResponse("../frontend/index.html")

@app.get("/users/", response_model=List[schemas.User], tags=["Users"], summary="列出所有使用者")
def list_users(
    skip: int = Query(0, ge=0, description="略過筆數 (分頁)"),
    limit: int = Query(100, gt=0, description="最多回傳筆數"),
    db: Session = Depends(get_db)
):
    return crud.get_users(db, skip=skip, limit=limit)


@app.get("/users/{user_id}/", response_model=schemas.User, tags=["Users"], summary="獲取使用者資訊")
def read_user(
    user_id: int = Path(..., description="使用者 ID", ge=1), db: Session = Depends(get_db)
):
    logger.info(f"Fetching user with ID: {user_id}")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found.")
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.put("/users/{user_id}/", response_model=schemas.User, tags=["Users"], summary="更新使用者資訊")
def update_user_info(
    user_id: int = Path(..., description="使用者 ID", ge=1),
    user_update: schemas.UserUpdate = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"Attempting to update user with ID: {user_id}, data: {user_update.model_dump()}")
    db_user = crud.update_user(db=db, user_id=user_id, user_update=user_update)
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found for update.")
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"User with ID {user_id} updated successfully.")
    return db_user

# --- Daily Record Endpoints ---
@app.post("/users/{user_id}/daily_records/", response_model=schemas.DailyRecord, tags=["Daily Records"], summary="新增或更新每日記錄")
def create_or_update_daily_record_for_user(
    user_id: int = Path(..., description="使用者 ID", ge=1),
    daily_record: schemas.DailyRecordCreate = Body(...),
    db: Session = Depends(get_db)
):
    logger.info(f"Attempting to create/update daily record for user ID: {user_id}, date: {daily_record.record_date}")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found when creating daily record.")
        raise HTTPException(status_code=404, detail="User not found")
    
    # 使用 get_or_create_daily_record 來處理新增或更新
    db_daily_record = crud.get_or_create_daily_record(db=db, user_id=user_id, record_data=daily_record)
    logger.info(f"Daily record for user ID: {user_id}, date: {daily_record.record_date} processed. Record ID: {db_daily_record.id}")
    return db_daily_record

@app.get("/users/{user_id}/daily_records/dates/", response_model=list[date], tags=["Daily Records"], summary="列出使用者已填寫日期")
def list_filled_dates_for_user(
    user_id: int = Path(..., ge=1, description="使用者 ID"),
    # ⬇ 可選：僅查詢某段期間，預防資料量暴衝
    start: Optional[date] = Query(None, description="起始日 (YYYY-MM-DD)"),
    end:   Optional[date] = Query(None, description="結束日 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(404, "User not found")

    q = db.query(models_db.DailyRecord.record_date).filter_by(user_id=user_id)
    if start:
        q = q.filter(models_db.DailyRecord.record_date >= start)
    if end:
        q = q.filter(models_db.DailyRecord.record_date <= end)

    # SQLAlchemy 會傳回 list[(date,)]，展平成純 date
    return [d[0] for d in q.all()]

@app.get("/users/{user_id}/daily_records/", response_model=List[schemas.DailyRecord], tags=["Daily Records"], summary="獲取使用者所有每日記錄")
def read_daily_records_for_user(
    user_id: int = Path(..., description="使用者 ID", ge=1),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    logger.info(f"Fetching daily records for user ID: {user_id}, skip: {skip}, limit: {limit}")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found when fetching daily records.")
        raise HTTPException(status_code=404, detail="User not found")
    
    records = crud.get_daily_records_by_user(db, user_id=user_id, skip=skip, limit=limit)
    return records

@app.get("/users/{user_id}/daily_records/{record_date}/", response_model=schemas.DailyRecord, tags=["Daily Records"], summary="取得使用者單日完整紀錄")
def read_daily_record_by_date(
    user_id: int = Path(..., ge=1, description="使用者 ID"),
    record_date: date = Path(..., description="記錄日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    if crud.get_user(db, user_id) is None:
        raise HTTPException(404, "User not found")

    record = crud.get_daily_record_by_date(db, user_id, record_date)
    if record is None:
        raise HTTPException(404, "Record not found")
    return record

@app.get("/users/{user_id}/daily_summary/{record_date}/", response_model=schemas.DailySummary, tags=["Summary & LLM"], summary="獲取每日總結與 LLM 建議")
def get_daily_summary_with_llm(
    user_id: int = Path(..., description="使用者 ID", ge=1),
    record_date: date = Path(..., description="記錄日期 (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    logger.info(f"Fetching daily summary for user ID: {user_id}, date: {record_date}")
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        logger.warning(f"User with ID {user_id} not found for daily summary.")
        raise HTTPException(status_code=404, detail="User not found")

    db_daily_record = crud.get_daily_record_by_date(db, user_id=user_id, record_date=record_date)
    if db_daily_record is None:
        logger.warning(f"Daily record for user ID {user_id} on date {record_date} not found.")
        raise HTTPException(status_code=404, detail=f"Daily record for date {record_date} not found")

    # 1. 計算 BMR
    bmr = services.calculate_bmr(db_user)
    logger.info(f"Calculated BMR for user ID {user_id}: {bmr}")

    # 2. 根據目標設定建議每日熱量攝取 (假設活動係數為 1.2)
    # TODO: 未來可以讓使用者輸入活動係數
    recommended_calories = services.calculate_recommended_calories(bmr, db_user.goal, activity_level=1.2)
    logger.info(f"Calculated recommended calories for user ID {user_id}: {recommended_calories}")
    
    # 3. 計算熱量差
    # 熱量差 = 當日攝取總熱量 - 建議每日熱量攝取
    # (更精確的可能是 攝取 - (TDEE - 目標調整值 + 運動消耗))
    # 這裡簡化為：攝取 - 建議攝取 (建議攝取已包含目標調整)
    calorie_balance = db_daily_record.calories_consumed - recommended_calories + db_daily_record.calories_burned_exercise
    logger.info(f"Calculated calorie balance for user ID {user_id}, date {record_date}: {calorie_balance}")

    summary_data = schemas.DailySummary(
        date=record_date,
        user_info=schemas.User.from_orm(db_user), 
        daily_record=schemas.DailyRecord.from_orm(db_daily_record), 
        bmr=bmr,
        recommended_daily_calories=recommended_calories,
        calorie_balance=calorie_balance,
        llm_feedback=None # 先初始化
    )

    # 4. 呼叫Service層LLM相關函數獲取建議
    summary_data = services.ensure_llm_feedback(db, db_daily_record, summary_data)
    return summary_data

# 根路徑，用於健康檢查或基本資訊
#@app.get("/", tags=["Root"])
#async def root():
#    return {"message": "歡迎使用健康管理系統 API"}

# 可以在這裡加入一個簡單的 on_event("startup") 來印出環境變數狀態
@app.on_event("startup")
async def startup_event():
    logger.info("應用程式啟動...")
    db_url = os.getenv("DATABASE_URL", "未設定 DATABASE_URL")
    gemini_key_status = "已設定" if os.getenv("GEMINI_API_KEY") else "未設定"
    logger.info(f"資料庫 URL: {db_url}")
    logger.info(f"Gemini API Key 狀態: {gemini_key_status}")
    if not os.getenv("GEMINI_API_KEY"):
        logger.warning("警告：GEMINI_API_KEY 環境變數未設定。LLM 功能將受限。")

