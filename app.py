import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey, Date, Float, Boolean, Text

# ============================
# Config & Theming
# ============================
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# Custom CSS background & styling (no external files)
BACKGROUND_CSS = """
<style>
/* Full-page soft gradient background */
.stApp {
  background: linear-gradient(135deg, #f5f7fa 0%, #e3eeff 50%, #fef0f0 100%) !important;
}
/* Glassmorphism cards */
.block-container {
  padding-top: 1.5rem !important;
}
div[data-testid="stExpander"] > details {
  background: rgba(255, 255, 255, 0.55) !important;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.3);
  box-shadow: 0 10px 30px rgba(0,0,0,0.06);
}
/* Sidebar polish */
.css-6qob1r, .css-9s5bis, section[data-testid="stSidebar"] {
  background: linear-gradient(180deg,#ffffffaa,#f6faffaa) !important;
  backdrop-filter: blur(8px);
}
/* Buttons */
.stButton>button {
  border-radius: 12px;
  padding: 0.5rem 1rem;
  border: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 8px 20px rgba(0,0,0,0.06);
}
/* Inputs */
.stTextInput>div>div>input, .stNumberInput input, textarea, .stDateInput input {
  border-radius: 12px !important;
}
/* Dataframe */
[data-testid="stDataFrame"] div[data-testid="stHeader"] {
  background: #ffffff55 !important;
}
</style>
"""
st.markdown(BACKGROUND_CSS, unsafe_allow_html=True)

# ============================
# Database (SQLite via SQLAlchemy)
# ============================
DB_FILE = "users_data.db"
engine = sa.create_engine(
    f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False}
)
meta = MetaData()

users_table = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False),
    Column('created_at', Date, default=date.today())
)

measurements = Table(
    'measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', Date),
    Column('height', Float),
    Column('leaves', Integer),
    Column('notes', Text),
    Column('prune_needed', Boolean)
)

meta.create_all(engine)

# ============================
# Session State
# ============================
ss = st.session_state
ss.setdefault('user_id', None)
ss.setdefault('username', None)
ss.setdefault('lang', 'فارسی')
ss.setdefault('demo_data', [])  # list of dicts

# ============================
# i18n helper
# ============================
def t(fa: str, en: str) -> str:
    return en if ss['lang'] == 'English' else fa

# Language select (kept in sync with state)
lang = st.sidebar.selectbox(
    "Language / زبان",
    ["فارسی", "English"],
    index=0 if ss.get('lang', 'فارسی') == 'فارسی' else 1
)
if ss.get('lang', 'فارسی') != lang:
    ss['lang'] = lang
    st.rerun()

# ============================
# Password helpers
# ============================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

# ============================
# DB utilities
# ============================

def get_user_by_username(username: str):
    with engine.begin() as conn:
        sel = sa.select(users_table).where(users_table.c.username == username)
        return conn.execute(sel).mappings().first()


def insert_user(username: str, password: str):
    with engine.begin() as conn:
        conn.execute(users_table.insert().values(
            username=username,
            password_hash=hash_password(password),
            created_at=date.today()
        ))


def insert_measurement(user_id: int, m_date: date, height: float, leaves: int, notes: str, prune: bool):
    with engine.begin() as conn:
        conn.execute(measurements.insert().values(
            user_id=user_id,
            date=m_date,
            height=height,
            leaves=leaves,
            notes=notes,
            prune_needed=bool(prune)
        ))


def read_measurements(user_id: int):
    with engine.begin() as conn:
        sel = sa.select(measurements).where(measurements.c.user_id == user_id).order_by(measurements.c.date.asc())
        rows = conn.execute(sel).mappings().all()
        return pd.DataFrame(rows) if rows else pd.DataFrame()

# ============================
# UI Sections
# ============================

def ui_home():
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown(
            f"""
            <div style='padding:1rem 1.25rem;background:rgba(255,255,255,0.65);border-radius:18px;border:1px solid rgba(0,0,0,0.05);box-shadow:0 10px 30px rgba(0,0,0,0.06)'>
            <h2>🍎 {t('داشبورد نهال سیب', 'Apple Seedling Dashboard')}</h2>
            <p style='font-size:1.05rem;'>
            {t('اینجا رشد نهال‌های خود را پایش کنید، اندازه‌گیری‌ها را ذخیره کنید، برنامه هفتگی مراقبت ببینید و فایل داده‌ها را دانلود کنید.',
               'Track growth, store measurements, see weekly care plans, and download your data.')}
            </p>
            <ul>
              <li>🌱 {t('پایش و ثبت ارتفاع/برگ‌ها/یادداشت', 'Track & log height/leaves/notes')}</li>
              <li>🧪 {t('پیش‌بینی روند رشد ساده', 'Simple growth trend prediction')}</li>
              <li>🍃 {t('راهنمای بیماری‌ها و پیشگیری', 'Disease guide & prevention')}</li>
              <li>📅 {t('زمان‌بندی آبیاری/کود/هرس', 'Water/Fertilizer/Pruning schedule')}</li>
              <li>⬇️ {t('دانلود CSV از اندازه‌گیری‌ها', 'Download measurements as CSV')}</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.metric(t("تعداد ثبت‌ها", "Total Logs"), f"{len(read_measurements(ss['user_id'])) if ss['user_id'] else 0}")
        st.metric(t("حالت زبان", "Language"), ss['lang'])
        st.info(t("از منوی کنار به بخش‌ها دسترسی دارید.", "Use the sidebar to navigate sections."))


def ui_tracking():
    st.header(t("پایش نهال", "Seedling Tracking"))
    with st.expander(t("➕ افزودن اندازه‌گیری", "➕ Add Measurement"), expanded=True):
        m_date = st.date_input(t("تاریخ", "Date"), value=date.today())
        c1, c2, c3 = st.columns(3)
        with c1:
            height = st.number_input(t("ارتفاع (cm)", "Height (cm)"), min_value=0.0, step=0.5)
        with c2:
            leaves = st.number_input(t("تعداد برگ‌ها", "Leaves"), min_value=0, step=1)
        with c3:
            prune = st.checkbox(t("نیاز به هرس؟", "Prune needed?"))
        notes = st.text_area(t("یادداشت", "Notes"), placeholder=t("وضعیت آبیاری، کوددهی، علائم...","
                                                       "Watering, fertilizing, symptoms..."))
        if st.button(t("ثبت", "Submit"), use_container_width=True):
            insert_measurement(ss['user_id'], m_date, float(height), int(leaves), notes, prune)
            st.success(t("اندازه‌گیری ذخیره شد.", "Measurement saved."))

    df = read_measurements(ss['user_id'])
    if not df.empty:
        st.subheader(t("داده‌های شما", "Your Data"))
        # Derived columns for charts
        df_show = df.copy()
        df_show['date'] = pd.to_datetime(df_show['date'])
        st.dataframe(df_show.sort_values('date', ascending=False), use_container_width=True)

        # Charts
        st.subheader(t("نمودار رشد", "Growth Charts"))
        st.line_chart(df_show.set_index('date')[['height']])
        st.bar_chart(df_show.set_index('date')[['leaves']])
    else:
        st.info(t("هنوز داده‌ای ثبت نشده است.", "No data yet. Add a measurement above."))


def ui_prediction():
    st.header(t("پیش‌بینی روند رشد (ساده)", "Simple Growth Trend Prediction"))
    df = read_measurements(ss['user_id'])
    if df.empty or len(df) < 2:
        st.warning(t("برای پیش‌بینی حداقل ۲ رکورد لازم است.", "At least 2 records are needed for prediction."))
        return

    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Convert dates to ordinal for simple linear regression
    x = df['date'].map(pd.Timestamp.toordinal).to_numpy()
    y = df['height'].astype(float).to_numpy()

    # Linear regression (polyfit degree=1)
    m, b = np.polyfit(x, y, 1)

    days_ahead = st.slider(t("روزهای آینده برای پیش‌بینی", "Days ahead to forecast"), 7, 60, 21)
    future_dates = [df['date'].iloc[-1] + timedelta(days=i) for i in range(1, days_ahead + 1)]
    x_future = np.array([d.toordinal() for d in future_dates])
    y_future = m * x_future + b

    # Combine for chart
    df_pred = pd.DataFrame({
        'date': list(df['date']) + future_dates,
        'height': list(df['height']) + list(y_future),
        'type': [t('واقعی', 'Actual')]*len(df) + [t('پیش‌بینی', 'Forecast')]*len(future_dates)
    })

    st.area_chart(df_pred.pivot(index='date', columns='type', values='height'))

    last_pred = y_future[-1]
    st.success(t(
        f"قد تقریبی در {days_ahead} روز آینده: {last_pred:.1f} cm",
        f"Estimated height in {days_ahead} days: {last_pred:.1f} cm"
    ))
    st.caption(t("این یک مدل ساده خطی است و صرفاً جهت نمایش است.", "This is a simple linear model for demonstration only."))


def ui_disease():
    st.header(t("راهنمای بیماری‌ها", "Disease Guide"))
    st.write(t(
        "بیماری‌های رایج سیب شامل لکه سیاه (Apple Scab)، سفیدک پودری، آتشک (Fire Blight) و پوسیدگی‌ها است.",
        "Common apple diseases include Apple Scab, Powdery Mildew, Fire Blight, and various rots."
    ))

    with st.expander(t("🔎 بررسی سریع (دمو)", "🔎 Quick Check (Demo)"), expanded=True):
        f = st.file_uploader(t("یک تصویر از برگ/میوه/ساقه بارگذاری کنید", "Upload a leaf/fruit/stem image"),
                             type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            # Demo logic: random-ish but deterministic using file name hash
            seed = abs(hash(f.name)) % 100
            classes = [
                (t("سالم", "Healthy"), 0.50 + (seed % 10)/100),
                (t("لکه سیاه", "Apple Scab"), 0.20 + ((seed//10) % 10)/100),
                (t("سفیدک پودری", "Powdery Mildew"), 0.10 + ((seed//100) % 10)/100),
                (t("آتشک", "Fire Blight"), 0.05 + ((seed//1000) % 10)/100)
            ]
            classes = classes[:4]
            # Normalize to 1
            total = sum(p for _, p in classes)
            classes = [(c, p/total) for c, p in classes]

            st.subheader(t("نتیجه دمو", "Demo Result"))
            best = max(classes, key=lambda x: x[1])
            st.success(t(f"تشخیص احتمالی: {best[0]}", f"Likely: {best[0]}"))
            st.progress(int(best[1]*100))

            st.write(t("جزئیات اعتماد (Probability)", "Confidence details (Probability)"))
            for c, p in classes:
                st.write(f"• {c}: {p*100:.1f}%")

            st.info(t(
                "توصیه عمومی: برگ‌های شدیداً آلوده را جدا کنید، تهویه را بهبود دهید، و برنامهٔ سم‌پاشی مطابق برچسب اجرا کنید.",
                "General advice: remove heavily infected leaves, improve airflow, and follow labeled spray programs."
            ))

    with st.expander(t("📚 نکات پیشگیری", "📚 Prevention Tips")):
        st.markdown(
            "\n".join([
                f"✅ {t('فاصله کاشت مناسب برای گردش هوا', 'Proper spacing for airflow')}",
                f"✅ {t('آبیاری پای بوته و پرهیز از خیس شدن برگ', 'Water at soil level; avoid wetting foliage')}",
                f"✅ {t('هرس منظم و حذف بقایای آلوده', 'Regular pruning; remove infected debris')}",
                f"✅ {t('پایش دوره‌ای و ثبت علائم در بخش پایش', 'Periodic scouting and logging in Tracking')}",
            ])
        )


def ui_schedule():
    st.header(t("زمان‌بندی نگهداری", "Care Schedule"))

    st.write(t(
        "با توجه به تاریخ کاشت، یک برنامهٔ سادهٔ آبیاری/کود/هرس تولید می‌شود.",
        "Based on planting date, generate a simple watering/fertilizer/pruning plan."
    ))
    planting = st.date_input(t("تاریخ کاشت", "Planting date"), value=date.today() - timedelta(days=30))

    # Simple rules for demo
    plan = []
    today = date.today()
    for i in range(8):  # 8 upcoming weeks
        d = today + timedelta(days=i*7)
        tasks = []
        tasks.append(t("آبیاری متوسط (بسته به اقلیم)", "Moderate watering (climate-dependent)"))
        if i % 2 == 0:
            tasks.append(t("بررسی آفات/بیماری", "Scout for pests/disease"))
        if i in (1, 5):
            tasks.append(t("کوددهی سبک NPK", "Light NPK fertilization"))
        if (d - planting).days > 60 and i in (3, 7):
            tasks.append(t("هرس سبک برای شکل‌دهی", "Light formative pruning"))
        plan.append({t("هفته", "Week"): i+1, t("تاریخ شروع", "Start Date"): d, t("کارها", "Tasks"): " • ".join(tasks)})

    df_plan = pd.DataFrame(plan)
    st.dataframe(df_plan, use_container_width=True)

    st.download_button(
        label=t("دانلود برنامه به CSV", "Download plan as CSV"),
        data=df_plan.to_csv(index=False).encode('utf-8'),
        file_name="care_plan.csv",
        mime="text/csv",
        use_container_width=True
    )


def ui_download():
    st.header(t("دانلود داده‌ها", "Download Your Data"))
    df = read_measurements(ss['user_id'])
    if df.empty:
        st.info(t("برای دانلود، ابتدا داده ثبت کنید.", "Log some data first to download."))
        return
    st.dataframe(df.sort_values('date', ascending=False), use_container_width=True)

    st.download_button(
        label=t("⬇️ دانلود CSV اندازه‌گیری‌ها", "⬇️ Download measurements CSV"),
        data=df.to_csv(index=False).encode('utf-8'),
        file_name="measurements.csv",
        mime="text/csv",
        use_container_width=True
    )

# ============================
# Authentication (Login / Sign up / Demo)
# ============================
if ss['user_id'] is None:
    st.sidebar.header(t("احراز هویت", "Authentication"))
    mode = st.sidebar.radio(t("حالت", "Mode"), [t("ورود", "Login"), t("ثبت‌نام", "Sign Up"), t("دمو", "Demo")])

    if mode == t("ثبت‌نام", "Sign Up"):
        st.header(t("ثبت‌نام", "Sign Up"))
        username = st.text_input(t("نام کاربری", "Username"))
        password = st.text_input(t("رمز عبور", "Password"), type="password")
        if st.button(t("ثبت", "Register")):
            if not username or not password:
                st.error(t("نام کاربری و رمز عبور را وارد کنید.", "Provide username & password."))
            else:
                if get_user_by_username(username):
                    st.error(t("نام کاربری تکراری است.", "Username already exists."))
                else:
                    insert_user(username, password)
                    st.success(t("ثبت شد. لطفاً وارد شوید.", "Registered. Please login."))

    elif mode == t("ورود", "Login"):
        st.header(t("ورود", "Login"))
        username = st.text_input(t("نام کاربری", "Username"))
        password = st.text_input(t("رمز عبور", "Password"), type="password")
        if st.button(t("ورود", "Login")):
            r = get_user_by_username(username)
            if not r:
                st.error(t("کاربری یافت نشد.", "Username not found."))
            elif check_password(password, r['password_hash']):
                ss['user_id'] = r['id']
                ss['username'] = r['username']
                st.rerun()
            else:
                st.error(t("رمز عبور اشتباه است.", "Wrong password."))

    else:  # Demo
        st.header(t("حالت دمو (کامل)", "Full Demo Mode"))
        st.info(t("در حالت دمو، داده‌ها فقط در حافظه موقت نگه‌داری می‌شوند و ذخیره پایدار ندارند.",
                 "In demo, data is kept in session only (not persisted)."))

        # Demo image check with details
        with st.expander(t("🔎 آزمون تصویر (دمو)", "🔎 Image Check (Demo)"), expanded=True):
            f = st.file_uploader(t("تصویر برگ/میوه/ساقه", "Leaf/Fruit/Stem image"), type=["jpg","jpeg","png"])
            if f:
                st.image(f, use_container_width=True)
                now = datetime.now()
                result = t("سالم", "Healthy")
                prob = 0.92
                ss['demo_data'].append({'file': f.name, 'result': result, 'prob': prob, 'time': now})
                st.success(t(f"نتیجه دمو: {result}", f"Demo prediction: {result}"))
                st.write(t(f"احتمال: {prob*100:.0f}%", f"Confidence: {prob*100:.0f}%"))
                st.caption(t("این فقط مثالی برای نمایش جریان کار است.", "This is for demonstration of the flow only."))

        # Demo measurement logging in-memory
        with st.expander(t("➕ افزودن اندازه‌گیری (دمو)", "➕ Add Measurement (Demo)")):
            m_date = st.date_input(t("تاریخ", "Date"), value=date.today(), key="demo_date")
            height = st.number_input(t("ارتفاع (cm)", "Height (cm)"), min_value=0.0, step=0.5, key="demo_h")
            leaves = st.number_input(t("تعداد برگ‌ها", "Leaves"), min_value=0, step=1, key="demo_l")
            notes = st.text_area(t("یادداشت", "Notes"), key="demo_n")
            prune = st.checkbox(t("نیاز به هرس؟", "Prune needed?"), key="demo_p")
            if st.button(t("ثبت دمو", "Save Demo")):
                ss['demo_data'].append({
                    'file': '-', 'result': '-', 'prob': '-', 'time': datetime.now(),
                    'date': m_date, 'height': float(height), 'leaves': int(leaves), 'notes': notes, 'prune': prune
                })
                st.success(t("ثبت شد (موقت).", "Saved (session only)."))

        if ss['demo_data']:
            st.subheader(t("تاریخچه دمو", "Demo History"))
            df_demo = pd.DataFrame(ss['demo_data'])
            st.dataframe(df_demo, use_container_width=True)

else:
    # ============ Authenticated Area ============
    st.sidebar.header(f"{t('خوش آمدید', 'Welcome')}, {ss['username']}")
    menu = st.sidebar.selectbox(
        t("منو", "Menu"),
        [t("🏠 خانه", "🏠 Home"), t("🌱 پایش", "🌱 Tracking"), t("📅 زمان‌بندی", "📅 Schedule"),
         t("📈 پیش‌بینی", "📈 Prediction"), t("🍎 بیماری", "🍎 Disease"), t("📥 دانلود", "📥 Download"),
         t("🚪 خروج", "🚪 Logout")]
    )

    if menu == t("🚪 خروج", "🚪 Logout"):
        ss['user_id'] = None
        ss['username'] = None
        st.rerun()

    elif menu == t("🏠 خانه", "🏠 Home"):
        ui_home()

    elif menu == t("🌱 پایش", "🌱 Tracking"):
        ui_tracking()

    elif menu == t("📈 پیش‌بینی", "📈 Prediction"):
        ui_prediction()

    elif menu == t("🍎 بیماری", "🍎 Disease"):
        ui_disease()

    elif menu == t("📅 زمان‌بندی", "📅 Schedule"):
        ui_schedule()

    elif menu == t("📥 دانلود", "📥 Download"):
        ui_download()

# Footer note
st.caption(t(
    "نسخه نمونه آموزشی — برای استفاده تولیدی نیاز به اعتبارسنجی و امنیت بیشتر دارید.",
    "Educational demo — for production use, add further validation and security."
))
