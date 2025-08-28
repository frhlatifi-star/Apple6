# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import os
import io
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat

# --- Optional TensorFlow (model) ---
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS / RTL ----------
def inject_css():
    st.markdown("""
    <style>
    :root {
      --accent: #2e7d32;
      --accent-2: #388e3c;
      --bg-1: #eaf9e7;
      --card: #ffffff;
    }
    .block-container {
        direction: rtl !important;
        text-align: right !important;
        padding: 1.2rem 2rem;
        background: linear-gradient(135deg, #eaf9e7, #f7fff8);
    }
    body {
        font-family: Vazirmatn, Tahoma, sans-serif;
        background: linear-gradient(135deg, #eaf9e7, #f7fff8) !important;
    }
    .app-header {
        display:flex; align-items:center; gap: 0.8rem; margin-bottom: 0.6rem;
    }
    .app-header .title {
        margin: 0;
        color: var(--accent);
    }
    .app-sub { color: #555; font-size:14px; margin-top:2px; }
    .dashboard-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 1rem;
        margin-top: 0.8rem;
    }
    .card {
        background: var(--card);
        padding: 1.1rem;
        border-radius: 14px;
        box-shadow: 0 6px 18px rgba(20,20,20,0.06);
        text-align:center;
        transition: all 0.15s ease-in-out;
        cursor: pointer;
    }
    .card:hover { transform: translateY(-6px); box-shadow: 0 10px 26px rgba(20,20,20,0.09); }
    .card-icon { font-size: 28px; color: var(--accent-2); margin-bottom: 6px; }
    .stButton>button { background-color: var(--accent-2) !important; color: white !important; border-radius: 8px !important; }
    .st-badge { direction: rtl !important; }
    table { direction: rtl !important; text-align: right !important; }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# ---------- Database (SQLite via SQLAlchemy) ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# users
users_table = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)

# measurements
measurements = Table(
    'measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)

# schedule
schedule_table = Table(
    'schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)

# predictions
predictions_table = Table(
    'predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)

# disease notes
disease_table = Table(
    'disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)

meta.create_all(engine)

# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Load TF model if present ----------
MODEL_PATH = "model/seedling_model.h5"
_model = None
_model_loaded = False
if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        @st.cache_resource
        def _load_model(path):
            return tf.keras.models.load_model(path)
        _model = _load_model(MODEL_PATH)
        _model_loaded = True
        st.experimental_set_query_params()  # noop but ensures TF imported message is acceptable
    except Exception as e:
        st.warning(f"بارگذاری مدل واقعی با خطا مواجه شد: {e}")
        _model_loaded = False

# fallback heuristic predictor
def heuristic_predict(pil_img: Image.Image):
    img = pil_img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)
    arr = np.array(img).astype(int)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_mask = ((r > g) & (g >= b)).astype(int)
    yellow_ratio = yellow_mask.mean()
    green_mask = ((g > r+10) & (g > b+10)).astype(int)
    green_ratio = green_mask.mean()
    if green_ratio > 0.12 and mean > 80:
        return "سالم", f"{min(99,int(50 + green_ratio*200))}%"
    if yellow_ratio > 0.12 or mean < 60:
        if yellow_ratio > 0.25:
            return "بیمار یا آفت‌زده", f"{min(95,int(40 + yellow_ratio*200))}%"
        else:
            return "نیاز به بررسی (کم‌آبی/کود)", f"{min(90,int(30 + (0.2 - mean/255)*200))}%"
    return "نامشخص", "50%"

def predict_with_model(pil_img: Image.Image):
    # expects model that takes 224x224 normalized images and outputs probabilities
    img = pil_img.convert("RGB").resize((224,224))
    x = np.array(img) / 255.0
    x = np.expand_dims(x, 0)
    preds = _model.predict(x)
    # user may have different class mapping — adapt if necessary
    classes = ["سالم", "بیمار", "نیاز به هرس", "کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = float(np.max(preds[0])) if preds is not None else 0.0
    label = classes[idx] if idx < len(classes) else "نامشخص"
    return label, f"{int(confidence*100)}%"

# ---------- UI: Header (logo local via base64) ----------
def app_header():
    logo_path = "logo.png"  # قرار دادن logo.png کنار app.py
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;'>"
    else:
        img_html = "<div style='font-size:36px;'>🍎</div>"

    st.markdown(f"""
    <div class="app-header">
        {img_html}
        <div>
            <h2 class="title">سیبتک</h2>
            <div class="app-sub">مدیریت و پایش نهال</div>
        </div>
    </div>
    <hr/>
    """, unsafe_allow_html=True)

app_header()

# ---------- Session defaults ----------
if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

# ---------- Authentication (simple) ----------
def auth_ui():
    st.write("")
    col1, col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود", "ثبت‌نام", "ورود مهمان"])
    with col2:
        st.write("")  # spacer

    if mode == "ثبت‌نام":
        st.subheader("ثبت‌نام")
        u = st.text_input("نام کاربری", key="signup_u")
        p = st.text_input("رمز عبور", type="password", key="signup_p")
        if st.button("ثبت‌نام"):
            if not u or not p:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    sel = sa.select(users_table).where(users_table.c.username == u)
                    r = conn.execute(sel).mappings().first()
                    if r:
                        st.error("این نام کاربری قبلاً ثبت شده.")
                    else:
                        conn.execute(users_table.insert().values(username=u, password_hash=hash_password(p)))
                        st.success("ثبت‌نام انجام شد. حالا وارد شوید.")
    elif mode == "ورود":
        st.subheader("ورود")
        u = st.text_input("نام کاربری (ورود)", key="login_u")
        p = st.text_input("رمز عبور (ورود)", type="password", key="login_p")
        if st.button("ورود به حساب"):
            with engine.connect() as conn:
                sel = sa.select(users_table).where(users_table.c.username == u)
                r = conn.execute(sel).mappings().first()
                if not r:
                    st.error("نام کاربری یافت نشد.")
                elif check_password(p, r['password_hash']):
                    st.success(f"خوش آمدی، {r['username']}")
                    st.session_state.user_id = int(r['id'])
                    st.session_state.username = r['username']
                    st.session_state.page = 'dashboard'
                    st.experimental_rerun()
                else:
                    st.error("رمز اشتباه است.")
    else:
        # guest login
        if st.button("ورود به عنوان مهمان"):
            st.session_state.user_id = 0
            st.session_state.username = "مهمان"
            st.session_state.page = 'dashboard'
            st.experimental_rerun()

# If not logged in, show auth
if st.session_state.user_id is None:
    st.info("برای ادامه وارد شوید یا ثبت‌نام کنید (یا مهمان شوید).")
    auth_ui()
    st.stop()

# ---------- Dashboard (cards) ----------
def dashboard_ui():
    st.subheader("داشبورد")
    st.markdown("""
    <div class="dashboard-grid">
    </div>
    """, unsafe_allow_html=True)

    # create cards in columns (fallback to simple columns)
    cards = [
        ("🏠 خانه", "home"),
        ("🌱 پایش نهال", "tracking"),
        ("📅 زمان‌بندی", "schedule"),
        ("📈 پیش‌بینی سلامت", "predict"),
        ("🍎 ثبت بیماری", "disease"),
        ("📥 دانلود داده‌ها", "download"),
        ("🚪 خروج", "logout")
    ]
    cols = st.columns(len(cards) if len(cards) <= 7 else 7)
    for idx, (label, key) in enumerate(cards):
        c = cols[idx % len(cols)]
        with c:
            if st.button(label):
                st.session_state.page = key
                st.experimental_rerun()

# ---------- Page: Home ----------
def page_home():
    st.header("🏠 خانه — خلاصه وضعیت")
    # last height
    try:
        with engine.connect() as conn:
            sel = sa.select(measurements).where(measurements.c.user_id == st.session_state.user_id).order_by(measurements.c.id.desc()).limit(1)
            last = conn.execute(sel).mappings().first()
            count_measure = conn.execute(sa.select(measurements).where(measurements.c.user_id == st.session_state.user_id)).rowcount
            count_sched = conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id == st.session_state.user_id)).rowcount
            count_disease = conn.execute(sa.select(disease_table).where(disease_table.c.user_id == st.session_state.user_id)).rowcount
    except Exception:
        last = None
        count_measure = count_sched = count_disease = 0

    c1, c2, c3 = st.columns(3)
    c1.metric("آخرین ارتفاع (cm)", last['height'] if last else "—")
    c2.metric("رویدادهای زمان‌بندی", count_sched)
    c3.metric("یادداشت‌های بیماری", count_disease)

    st.markdown("**آخرین پیش‌بینی‌ها (۵ مورد اخیر)**")
    try:
        with engine.connect() as conn:
            sel = sa.select(predictions_table).where(predictions_table.c.user_id == st.session_state.user_id).order_by(predictions_table.c.id.desc()).limit(5)
            rows = conn.execute(sel).mappings().all()
            if rows:
                st.dataframe(pd.DataFrame(rows))
            else:
                st.info("هنوز پیش‌بینی‌ای ثبت نشده است.")
    except Exception as e:
        st.error(f"خطا در بارگذاری پیش‌بینی‌ها: {e}")

# ---------- Page: Tracking ----------
def page_tracking():
    st.header("🌱 پایش نهال — ثبت رشد و نمودارها")
    with st.expander("➕ افزودن اندازه‌گیری جدید"):
        with st.form("add_measure"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ (اختیاری)", min_value=0, step=1, value=0)
            notes = st.text_area("یادداشت")
            prune = st.checkbox("نیاز به هرس؟")
            submitted = st.form_submit_button("ثبت اندازه‌گیری")
            if submitted:
                try:
                    with engine.connect() as conn:
                        conn.execute(measurements.insert().values(
                            user_id=st.session_state.user_id,
                            date=str(date),
                            height=int(height),
                            leaves=int(leaves),
                            notes=notes,
                            prune_needed=int(prune)
                        ))
                    st.success("اندازه‌گیری با موفقیت ثبت شد.")
                except Exception as e:
                    st.error(f"خطا در ثبت اندازه‌گیری: {e}")

    st.subheader("تاریخچه اندازه‌گیری‌ها")
    try:
        with engine.connect() as conn:
            sel = sa.select(measurements).where(measurements.c.user_id == st.session_state.user_id).order_by(measurements.c.date.desc())
            rows = conn.execute(sel).mappings().all()
            if rows:
                df = pd.DataFrame(rows)
                try:
                    df['date'] = pd.to_datetime(df['date'])
                except Exception:
                    pass
                st.dataframe(df, use_container_width=True)
                if 'height' in df.columns:
                    st.line_chart(df.set_index('date')['height'])
                if 'leaves' in df.columns:
                    st.line_chart(df.set_index('date')['leaves'])
            else:
                st.info("هیچ اندازه‌گیری‌ای ثبت نشده است.")
    except Exception as e:
        st.error(f"خطا در بارگذاری داده‌ها: {e}")

# ---------- Page: Schedule ----------
def page_schedule():
    st.header("📅 زمان‌بندی فعالیت‌ها")
    with st.expander("➕ افزودن برنامه"):
        with st.form("add_sched"):
            task = st.text_input("فعالیت")
            task_date = st.date_input("تاریخ برنامه")
            task_notes = st.text_area("یادداشت")
            sub = st.form_submit_button("ثبت برنامه")
            if sub:
                try:
                    with engine.connect() as conn:
                        conn.execute(schedule_table.insert().values(
                            user_id=st.session_state.user_id,
                            task=task,
                            date=str(task_date),
                            notes=task_notes
                        ))
                    st.success("برنامه ثبت شد.")
                except Exception as e:
                    st.error(f"خطا در ثبت برنامه: {e}")
    st.subheader("برنامه‌های ثبت‌شده")
    try:
        with engine.connect() as conn:
            sel = sa.select(schedule_table).where(schedule_table.c.user_id == st.session_state.user_id).order_by(schedule_table.c.date.desc())
            rows = conn.execute(sel).mappings().all()
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("هیچ برنامه‌ای ثبت نشده است.")
    except Exception as e:
        st.error(f"خطا در بارگذاری برنامه‌ها: {e}")

# ---------- Page: Predict ----------
def page_predict():
    st.header("📈 پیش‌بینی سلامت نهال (بارگذاری تصویر)")
    st.write("یک عکس از نهال یا برگ آپلود کنید؛ اگر مدل `model/seedling_model.h5` موجود باشد از آن استفاده می‌کنیم.")
    uploaded = st.file_uploader("انتخاب تصویر", type=["jpg","jpeg","png"])
    if uploaded:
        try:
            pil_img = Image.open(uploaded)
            st.image(pil_img, use_container_width=True)
            st.write("در حال تحلیل تصویر...")
            if _model_loaded and TF_AVAILABLE:
                try:
                    label, conf = predict_with_model(pil_img)
                except Exception as e:
                    st.warning(f"خطا در اجرای مدل واقعی، از روش جایگزین استفاده می‌شود: {e}")
                    label, conf = heuristic_predict(pil_img)
            else:
                label, conf = heuristic_predict(pil_img)
                if not _model_loaded:
                    st.info("مدل واقعی پیدا نشد؛ از پیش‌بینی آزمایشی استفاده شد.")
            st.success(f"نتیجه: {label} — اعتماد: {conf}")

            # ذخیره در DB
            try:
                with engine.connect() as conn:
                    conn.execute(predictions_table.insert().values(
                        user_id=st.session_state.user_id,
                        file_name=getattr(uploaded, "name", f"img_{datetime.now().timestamp()}"),
                        result=label,
                        confidence=conf,
                        date=str(datetime.now())
                    ))
                st.info("پیش‌بینی در تاریخچه ذخیره شد.")
            except Exception as e:
                st.error(f"خطا در ذخیره پیش‌بینی: {e}")

        except Exception as e:
            st.error(f"خطا در پردازش تصویر: {e}")

# ---------- Page: Disease Notes ----------
def page_disease():
    st.header("🍎 ثبت بیماری / یادداشت")
    with st.form("add_disease"):
        note = st.text_area("شرح مشکل یا علائم مشاهده شده")
        sub = st.form_submit_button("ثبت یادداشت")
        if sub:
            try:
                with engine.connect() as conn:
                    conn.execute(disease_table.insert().values(
                        user_id=st.session_state.user_id,
                        note=note,
                        date=str(datetime.now())
                    ))
                st.success("یادداشت ثبت شد.")
            except Exception as e:
                st.error(f"خطا در ثبت یادداشت: {e}")

    st.subheader("یادداشت‌های ثبت‌شده")
    try:
        with engine.connect() as conn:
            sel = sa.select(disease_table).where(disease_table.c.user_id == st.session_state.user_id).order_by(disease_table.c.date.desc())
            rows = conn.execute(sel).mappings().all()
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("هنوز یادداشتی ثبت نشده است.")
    except Exception as e:
        st.error(f"خطا در بارگذاری یادداشت‌ها: {e}")

# ---------- Page: Download ----------
def page_download():
    st.header("📥 دانلود داده‌ها")
    try:
        with engine.connect() as conn:
            sel = sa.select(measurements).where(measurements.c.user_id == st.session_state.user_id)
            rows = conn.execute(sel).mappings().all()
            if rows:
                df = pd.DataFrame(rows)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("دانلود اندازه‌گیری‌ها (CSV)", csv, "measurements.csv", "text/csv")
            else:
                st.info("داده‌ای برای دانلود وجود ندارد.")
            # predictions
            selp = sa.select(predictions_table).where(predictions_table.c.user_id == st.session_state.user_id)
            prow = conn.execute(selp).mappings().all()
            if prow:
                pdf = pd.DataFrame(prow).to_csv(index=False).encode('utf-8-sig')
                st.download_button("دانلود پیش‌بینی‌ها (CSV)", pdf, "predictions.csv", "text/csv")
    except Exception as e:
        st.error(f"خطا در آماده‌سازی داده‌ها: {e}")

# ---------- Router ----------
def router():
    if st.session_state.page == 'dashboard':
        dashboard_ui()
    elif st.session_state.page == 'home':
        page_home()
    elif st.session_state.page == 'tracking':
        page_tracking()
    elif st.session_state.page == 'schedule':
        page_schedule()
    elif st.session_state.page == 'predict':
        page_predict()
    elif st.session_state.page == 'disease':
        page_disease()
    elif st.session_state.page == 'download':
        page_download()
    elif st.session_state.page == 'logout':
        st.session_state.user_id = None
        st.session_state.username = None
        st.success("شما خارج شدید.")
        st.experimental_rerun()
    else:
        st.info("صفحه نامشخص — بازگشت به داشبورد")
        st.session_state.page = 'dashboard'

# Start
dashboard_ui()
router()
