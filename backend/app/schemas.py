from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from .models_db import GenderEnum, GoalEnum # Import enums from models

# --- User Schemas ---
class UserBase(BaseModel):
    nickname: Optional[str] = Field(None, max_length=64, description="暱稱")
    height_cm: float = Field(..., gt=0, description="身高 (cm)")
    weight_kg: float = Field(..., gt=0, description="體重 (kg)")
    age: int = Field(..., gt=0, description="年齡 (歲)")
    gender: GenderEnum = Field(..., description="性別")
    goal: GoalEnum = Field(..., description="目標 (增肌／減脂／維持)")

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    pass

class User(UserBase):
    id: int
    model_config = {
        "from_attributes": True
    }

# --- Daily Record Schemas ---
class DailyRecordBase(BaseModel):
    record_date: date = Field(..., description="記錄日期")
    calories_consumed: int = Field(..., ge=0, description="當日攝取總熱量 (kcal)")
    protein_g: float = Field(..., ge=0, description="蛋白質 (g)")
    fat_g: float = Field(..., ge=0, description="脂肪 (g)")
    carbs_g: float = Field(..., ge=0, description="碳水化合物 (g)")
    calories_burned_exercise: Optional[int] = Field(0, ge=0, description="額外運動消耗熱量 (kcal)")

class DailyRecordCreate(DailyRecordBase):
    pass

class DailyRecord(DailyRecordBase):
    id: int
    user_id: int

    model_config = {
        "from_attributes": True
    }

# --- Calculation and Summary Schemas ---
class BMRCalculationResult(BaseModel):
    bmr: float = Field(..., description="基礎代謝率 (BMR)")
    recommended_daily_calories: float = Field(..., description="建議每日熱量攝取")

class DailySummary(BaseModel):
    date: date
    user_info: User
    daily_record: DailyRecord
    bmr: float
    recommended_daily_calories: float
    calorie_balance: float # 熱量盈餘／赤字
    llm_feedback: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
