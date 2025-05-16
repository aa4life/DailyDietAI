/* eslint-disable no-console */
const { createApp, ref, reactive, onMounted } = Vue;

// ────────────────────────────────────────────────────────────
// 1. 建立 Vue App
// ────────────────────────────────────────────────────────────
const app = createApp({
  setup () {
    /* -------------------------------------------------------
       A. 基本常數
    ------------------------------------------------------- */
    const API_BASE = 'http://127.0.0.1:8000';      // FastAPI URL
    const userId   = ref(localStorage.getItem('healthAppUserId') || null);

    /* -------------------------------------------------------
       B. 狀態：表單 / 結果
    ------------------------------------------------------- */
    const userForm = reactive({
      nickname:  null,
      height_cm: null,
      weight_kg: null,
      age:       null,
      gender:    'male',
      goal:      'maintain'
    });

    const dailyRecordForm = reactive({
      record_date: new Date().toISOString().slice(0, 10),   // YYYY-MM-DD
      calories_consumed:            null,
      protein_g:                    null,
      fat_g:                        null,
      carbs_g:                      null,
      calories_burned_exercise:     0
    });

    const dailySummary = reactive({
      bmr:                        null,
      recommended_daily_calories: null,
      calorie_balance:            null,
      llm_feedback:               null
    });

    /* -------------------------------------------------------
       C. UI 狀態
    ------------------------------------------------------- */
    const users          = ref([]);
    const messageText      = ref('');
    const messageType      = ref('success');
    const isLoadingUser    = ref(false);
    const isLoadingRecord  = ref(false);
    const isLoadingSummary = ref(false);
    const selectedUserId = ref(null); 
    const showProfileForm = ref(true);

    /* -------------------------------------------------------
       D. 📅 v-calendar
    ------------------------------------------------------- */
    const filledDates   = ref([]);   // ["2025-05-14", ...]
    const calendarAttrs = ref([]);   // v-calendar highlight 設定

    async function loadFilledDates () {
      if (!userId.value) return;
      try {
        const r = await fetch(`${API_BASE}/users/${userId.value}/daily_records/dates/`);
        if (!r.ok) throw new Error(await r.text());
        filledDates.value = await r.json();

        calendarAttrs.value = [{
            key: 'done',
            dates: filledDates.value,          // ISO 字串陣列
            highlight: {
                fillMode: 'solid',
                class: 'has-record'
            }
        }];
      } catch (err) {
        console.error('loadFilledDates', err);
      }
    }

    function onDayClick ({ id }) {          // id = YYYY-MM-DD
      dailyRecordForm.record_date = id;

      if (filledDates.value.includes(id)) {
        fetchDailySummary(id);
        fetchDailyRecord(id);               // 預填當日資料
      } else {
        resetFormFor(id);
        Object.assign(dailySummary, { bmr:null, recommended_daily_calories:null,
                                      calorie_balance:null, llm_feedback:null });
      }
    }

    function resetFormFor (dateStr) {
      Object.assign(dailyRecordForm, {
        record_date:               dateStr,
        calories_consumed:         null,
        protein_g:                 null,
        fat_g:                     null,
        carbs_g:                   null,
        calories_burned_exercise:  0
      });
    }

    async function fetchDailyRecord (dateStr) {
        try {
            const r = await fetch(`${API_BASE}/users/${userId.value}/daily_records/${dateStr}`);
            if (!r.ok) {
                console.warn('單日紀錄不存在');
                return;
            }
            Object.assign(dailyRecordForm, await r.json());
        } catch (e) { console.error('fetchDailyRecord', e); }
    }

    /* -------------------------------------------------------
       E. 通用提示
    ------------------------------------------------------- */
    function showMessage (msg, type='success', ms=3000) {
      messageText.value = msg;
      messageType.value = type;
      if (ms) setTimeout(() => (messageText.value=''), ms);
    }

    /* -------------------------------------------------------
       F. 使用者
    ------------------------------------------------------- */
    function toggleProfileForm () {
      showProfileForm.value = !showProfileForm.value;
    }

    async function loadUsers () {
        const r = await fetch(`${API_BASE}/users/`);
        if (r.ok) users.value = await r.json();
    }

    async function onUserSelect () {
        if (!selectedUserId.value) {
            // 選「新增使用者」→ 清空表單、userId 置 null
            userId.value = null;
            Object.assign(userForm, { 
                height_cm:null, weight_kg:null, age:null, gender:'male', goal:'maintain' 
            });
            Object.assign(dailySummary, {
                bmr:null, recommended_daily_calories:null,
                calorie_balance:null, llm_feedback:null
            });
            calendarAttrs.value = [];
        } else {
            // 選現有 → userId 設定＆載入資料
            userId.value = selectedUserId.value;
            await fetchUserData();
            await loadFilledDates();
        }
    }

    async function fetchUserData () {
      if (!userId.value) return;
      isLoadingUser.value = true;
      try {
        const r = await fetch(`${API_BASE}/users/${userId.value}/`);
        if (!r.ok) throw new Error(await r.text());
        Object.assign(userForm, await r.json());
        showMessage('使用者資料已載入');
      } catch (e) {
        console.error(e);
        localStorage.removeItem('healthAppUserId');
        userId.value = null;
        showMessage(`載入失敗: ${e.message}`, 'error');
      } finally {
        isLoadingUser.value = false;
      }
    }

    async function saveUserProfile () {
      isLoadingUser.value = true;
      const isUpdate = Boolean(userId.value);
      const url      = isUpdate
        ? `${API_BASE}/users/${userId.value}/`
        : `${API_BASE}/users/`;
      const method   = isUpdate ? 'PUT' : 'POST';

      try {
        const r = await fetch(url, {
          method,
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(userForm)
        });
        if (!r.ok) throw new Error(await r.text());
        const data = await r.json();

        if (!isUpdate) {
            userId.value = data.id;
            localStorage.setItem('healthAppUserId', data.id);
            await loadUsers();
            selectedUserId.value = userId.value;
        }
        Object.assign(userForm, data);
        showMessage(isUpdate ? '更新完成' : '儲存完成');
        await loadFilledDates();
      } catch (e) {
        console.error(e);
        showMessage(`儲存失敗: ${e.message}`, 'error');
      } finally {
        isLoadingUser.value = false;
      }
    }

    /* -------------------------------------------------------
       G. 每日記錄 API
    ------------------------------------------------------- */
    async function submitDailyRecord () {
      if (!userId.value) { showMessage('請先儲存基本資料', 'error'); return; }

      //同日重覆檢查
      if (filledDates.value.includes(dailyRecordForm.record_date)) {
        if (!confirm(`日期 ${dailyRecordForm.record_date} 已有紀錄，確定要覆寫？`)) {
                return;        // 使用者取消
        }
      }
      isLoadingRecord.value = true;
      try {
        const r = await fetch(`${API_BASE}/users/${userId.value}/daily_records/`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(dailyRecordForm)
        });
        if (!r.ok) throw new Error(await r.text());
        showMessage('已提交，正在分析...');
        await fetchDailySummary(dailyRecordForm.record_date);
        await loadFilledDates();
      } catch (e) {
        console.error(e);
        showMessage(`提交失敗: ${e.message}`, 'error');
      } finally {
        isLoadingRecord.value = false;
      }
    }

    async function fetchDailySummary (dateStr) {
      if (!userId.value) return;
      isLoadingSummary.value = true;
      try {
        const r = await fetch(`${API_BASE}/users/${userId.value}/daily_summary/${dateStr}/`);
        if (!r.ok) throw new Error(await r.text());
        Object.assign(dailySummary, await r.json());
      } catch (e) {
        console.error(e);
        showMessage(`分析失敗: ${e.message}`, 'error');
      } finally {
        isLoadingSummary.value = false;
      }
    }

    /* -------------------------------------------------------
       H. 首次載入
    ------------------------------------------------------- */
    onMounted(async () => {
        await loadUsers();
        if (userId.value) {
            selectedUserId.value = parseInt(userId.value);
            await fetchUserData();
            await loadFilledDates();
        }
    });

    /* -------------------------------------------------------
       I. 暴露給模板
    ------------------------------------------------------- */
    return {
      // 資料
      userId, users, selectedUserId,
      userForm, dailyRecordForm, dailySummary,
      // UI
      messageText, messageType, showProfileForm,
      isLoadingUser, isLoadingRecord, isLoadingSummary,
      // 日曆
      calendarAttrs, onDayClick,
      // 方法
      onUserSelect, saveUserProfile, submitDailyRecord, toggleProfileForm
    };
  }
});

/* 2. 安裝 v-calendar plugin */
const VCPlugin = window.VCalendar?.default || window.VCalendar;
app.use(VCPlugin, {});

/* 3. 掛載 */
app.mount('#app');
