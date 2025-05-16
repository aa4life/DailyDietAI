# 健康管理系統

這是一個簡易的 Web 應用程式，用於記錄每日飲食熱量、身體資訊與運動消耗，並透過 LLM API（例如 Google Gemini）提供個人化的營養建議與評分。

## 專案架構

*   **前端**: Vue.js 
*   **後端**: FastAPI (Python)
*   **資料庫**: SQLite
*   **LLM API**: Google Gemini (可替換)

## 環境需求

*   Python 3.8+
*   pip (Python 套件安裝器)
*   虛擬環境 (建議使用，例如 `venv`)
*   一個有效的 Gemini API 金鑰 (或其他 LLM API 金鑰，若您修改 `services.py` 中的串接邏輯)

## 快速開始

### 1. 後端設定與啟動

1.  **進入後端目錄**:
    ```bash
    cd backend
    ```

2.  **建立並啟用虛擬環境** (建議):
    *   macOS / Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **安裝依賴套件**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **設定環境變數**:
    *   複製範例環境變數檔案：
        ```bash
        cp .env.example .env
        ```
    *   編輯 `.env` 檔案，填入您的 `GEMINI_API_KEY`。
        ```dotenv
        # backend/.env

        # 資料庫連接字串
        # 對於 SQLite, 格式為: sqlite:///./your_database_name.db
        # 對於 PostgreSQL, 格式為: postgresql://user:password@host:port/database
        DATABASE_URL="sqlite:///./health_app.db"

        # Gemini API 金鑰
        # 前往 https://aistudio.google.com/app/apikey 取得您的 API 金鑰
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
        ```
        如果您暫時沒有 API 金鑰，LLM 建議功能將無法使用，但其他功能仍可正常運作。

5.  **啟動 FastAPI 後端伺服器**:
    在 `backend` 目錄下執行：
    ```bash
    uvicorn app.main:app --reload
    ```
    伺服器預設會在 `http://127.0.0.1:8000` 啟動。
    您可以透過瀏覽器訪問 `http://127.0.0.1:8000/docs` 來查看 API 文件並進行測試。

### 2. 前端使用

1.  **進入前端目錄**:
    從專案根目錄：
    ```bash
    cd frontend
    ```
    (如果您目前在 `backend` 目錄，請先 `cd ..` 回到專案根目錄，再 `cd frontend`)

2.  **開啟前端頁面**:
    直接在您的網頁瀏覽器中開啟 `http://127.0.0.1:8000`

3.  **操作步驟**:
    *   **輸入基本資料**:
        *   在「使用者基本資料」區塊填寫您的暱稱、身高、體重、年齡、性別和目標。
    *   **每日記錄**:
        *   基本資料儲存後，「每日記錄」區塊將會啟用。
        *   選擇日期，並填寫當日的攝取總熱量、三大營養素（蛋白質、脂肪、碳水化合物）以及額外運動消耗的熱量。
        *   點擊「提交每日記錄並獲取建議」按鈕。
    *   **查看結果與建議**:
        *   提交每日記錄後，頁面下方「分析結果與建議」區塊會顯示計算出的 BMR、建議每日熱量攝取、本日熱量平衡，以及來自 AI 營養師的建議（如果 Gemini API 金鑰已正確設定並成功呼叫）。

## 注意事項

*   前端 `frontend/app.js` 中的 `apiBaseUrl` 變數預設指向 `http://127.0.0.1:8000`。如果您的後端伺服器運行在不同的位址或埠號，請相應修改此變數。
*   目前的實作是 MVP (Minimum Viable Product) 版本，使用者登入功能被簡化（使用 `localStorage` 儲存 `userId`）。
*   資料庫 `health_app.db` 會在後端首次啟動時，於 `backend` 目錄下自動建立。

## 未來可擴展方向

*   完整的使用者認證系統。
*   更詳細的活動量等級選擇。
*   歷史數據圖表化展示。
*   食物資料庫整合，方便記錄飲食。
*   更進階的 LLM 提示工程以獲得更精準的建議。
