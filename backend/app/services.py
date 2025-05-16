import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import google.generativeai as genai
from . import models_db, schemas

# 載入 .env 檔案中的環境變數
# 確保 .env 檔案位於 backend 資料夾下
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest') # 或者選擇其他適合的模型
else:
    print("警告：GEMINI_API_KEY 未設定。LLM 功能將無法使用。")
    gemini_model = None


def calculate_bmr(user: models_db.User) -> float:
    """
    使用 Mifflin-St Jeor 公式計算基礎代謝率 (BMR)
    BMR (kcal/day) = 10 * weight (kg) + 6.25 * height (cm) - 5 * age (years) + s
    s = +5 for males, -161 for females
    """
    if user.gender == models_db.GenderEnum.male:
        s = 5
    elif user.gender == models_db.GenderEnum.female:
        s = -161
    else:
        # For 'other' gender, we might use an average or a different approach.
        # For simplicity, let's use an average of male and female adjustments.
        s = (5 - 161) / 2
    
    bmr = (10 * user.weight_kg) + (6.25 * user.height_cm) - (5 * user.age) + s
    return round(bmr, 2)

def calculate_recommended_calories(bmr: float, goal: models_db.GoalEnum, activity_level: float = 1.2) -> float:
    """
    根據目標設定建議每日熱量攝取
    activity_level: 1.2 (sedentary) to 1.9 (very active)
    這裡我們先用一個固定的 activity_level (例如 1.2 代表久坐) 來計算 TDEE (Total Daily Energy Expenditure)
    TDEE = BMR * activity_level
    """
    tdee = bmr * activity_level # 假設輕度活動或久坐

    if goal == models_db.GoalEnum.lose_fat:
        # 建議每日赤字 300-500 kcal
        return round(tdee - 500, 2)
    elif goal == models_db.GoalEnum.gain_muscle:
        # 建議每日盈餘 300-500 kcal
        return round(tdee + 300, 2)
    elif goal == models_db.GoalEnum.maintain:
        return round(tdee, 2)
    else:
        return round(tdee, 2) # 預設為維持

def ensure_llm_feedback(db: Session, record: models_db.DailyRecord, summary: schemas.DailySummary):
    """若該日紀錄還沒有 llm_feedback，就呼叫 LLM，並存回 DB"""
    if record.llm_feedback:
        summary.llm_feedback = record.llm_feedback
        return summary     # 已有建議，直接回

    if not (GEMINI_API_KEY and gemini_model):
        summary.llm_feedback = "LLM 服務未配置或 API 金鑰遺失。"
        return summary

    feedback = get_llm_feedback(summary)  # 呼叫大模型
    record.llm_feedback = feedback        # 寫回 DB
    db.commit()
    summary.llm_feedback = feedback
    return summary


def get_llm_feedback(daily_summary_data: schemas.DailySummary) -> str:
    """
    將資料傳送給 LLM API (Gemini)，產生評分與建議語句
    """
    if not gemini_model:
        return "LLM 服務未配置，無法提供建議。"
    if not GEMINI_API_KEY:
        return "GEMINI_API_KEY 未設定，無法呼叫 LLM。"

    user = daily_summary_data.user_info
    record = daily_summary_data.daily_record
    
    prompt = f"""
    這是一位使用者 {user.age} 歲 {user.gender.value} 的健康數據。
    身高: {user.height_cm} cm, 體重: {user.weight_kg} kg.
    他的目標是: {user.goal.value}.
    他的基礎代謝率 (BMR) 是: {daily_summary_data.bmr:.2f} kcal.
    系統建議他每日攝取熱量為: {daily_summary_data.recommended_daily_calories:.2f} kcal.

    在 {record.record_date} 這一天，他的飲食和運動記錄如下:
    攝取總熱量: {record.calories_consumed} kcal
    蛋白質: {record.protein_g} g
    脂肪: {record.fat_g} g
    碳水化合物: {record.carbs_g} g
    額外運動消耗: {record.calories_burned_exercise} kcal
    計算出的熱量差 (攝取 - (BMR*活動因子 + 運動消耗) - 建議熱量調整): {daily_summary_data.calorie_balance:.2f} kcal.
    (熱量差的計算方式為：當日攝取總熱量 - 建議每日熱量攝取。正數代表盈餘，負數代表赤字。)

    請根據以上數據，提供今天的飲食和運動評分 (1-10分)，並給予具體的營養建議和鼓勵。
    請著重於以下幾點：
    1. 熱量攝取是否符合目標？
    2. 三大營養素的比例是否均衡？（可以給出大致的建議比例，例如蛋白質佔總熱量20-30%等）
    3. 針對他的目標 ({user.goal.value})，今天的表現如何？
    4. 提供1-2個具體的改進建議或鼓勵的話。

    請以友善、鼓勵的語氣回覆，並將回覆內容控制在150字以內。
    """

    try:
        response = gemini_model.generate_content(prompt)
        # 檢查 response.parts 是否存在以及是否有內容
        if response.parts:
            return response.text.replace("\n", "<br>")
        elif response.candidates and response.candidates[0].content.parts: # 有些 API 版本差異
             return "".join(part.text for part in response.candidates[0].content.parts)
        else:
            # 嘗試獲取錯誤訊息
            error_message = "LLM API 回應格式不符預期或無有效內容。"
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                error_message += f" Prompt Feedback: {response.prompt_feedback}"
            return error_message
    except Exception as e:
        print(f"呼叫 Gemini API 時發生錯誤: {e}")
        return f"無法從 LLM 獲取建議: {str(e)}"
