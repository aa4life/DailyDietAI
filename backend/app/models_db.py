from sqlalchemy import Column, Integer, UniqueConstraint, Float, Date, ForeignKey, Enum as SQLAlchemyEnum , Text, String
from sqlalchemy.orm import relationship
import enum

from .database import Base

class GenderEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class GoalEnum(str, enum.Enum):
    lose_fat = "lose_fat"
    maintain = "maintain"
    gain_muscle = "gain_muscle"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String(64), nullable=True)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(SQLAlchemyEnum(GenderEnum), nullable=False)
    goal = Column(SQLAlchemyEnum(GoalEnum), nullable=False)

    # Relationship to DailyRecord
    daily_records = relationship("DailyRecord", back_populates="owner")

class DailyRecord(Base):
    __tablename__ = "daily_records"

    id = Column(Integer, primary_key=True, index=True)
    record_date = Column(Date, nullable=False, index=True)
    calories_consumed = Column(Integer, nullable=False)
    protein_g = Column(Float, nullable=False)
    fat_g = Column(Float, nullable=False)
    carbs_g = Column(Float, nullable=False)
    calories_burned_exercise = Column(Integer, nullable=True, default=0)
    llm_feedback = Column(Text, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="daily_records")

    __table_args__ = (
        UniqueConstraint("user_id", "record_date", name="ux_daily_user_date"),
    )
