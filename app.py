import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat
import numpy as np
import os
import base64

# Optional ML imports
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- Global CSS ----------
st.markdown("""
<style>
/* بک‌گراند سبز ملایم */
.stApp {
    background-color: #e6f4ea;
    color: #333;
    font-family: Vazir, Tahoma, sans-serif;
}

/* راست چین */
html, body, [class*="css"]  {
    direction: rtl !important;
    text-align: right !important;
}

/* هدر و لوگو */
.app-header {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding: 10px 0;
    border-bottom: 2px solid #a3d9a5;
}
.app-header img {
    width: 64px;
    height: 64px;
    border-radius: 12px;
    margin-left: 12px;
}
.app-header h2 {
    margin: 0;
    color: #2e7d32;
}
.app-header .subtitle {
    color: #4a4a4a;
    font-size: 14px;
}

/* دکمه‌ها */
.stButton>button {
    background-color: #4CAF50;
    color: white;
    border-radius: 8px;
    padding: 0.5em 1em;
    font-weight: bold;
    cursor: pointer;
    transition: 0.3s;
}
.stButton>button:hover {
    background-color: #45a049;
}

/* اینپوت‌ها */
.stTextInput>div>input, .stNumberInput>div>input, textarea {
    border-radius: 8px;
    border: 1px solid #a3d9a5;
    padding: 6px;
}

/* جدول‌ها */
.stDataFrame table {
    border-radius: 8px;
    border: 1px solid #a3d9a5;
}
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)

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

schedule_table = Table(
    'schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)

predictions_table = Table(
    'predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)

disease_table = Table(
    'disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)

meta.create_all(engine)

# ---------- Session defaults ----------
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'demo_history' not in st.session_state:
    st.session_state['demo_history'] = []

# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Model load
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
    except Exception as e:
        st.warning(f"بارگذاری مدل با خطا مواجه شد: {e}")
        _model_loaded = False

# Heuristic prediction
def heuristic_predict_potted_seedling(pil_img: Image.Image):
    img = pil_img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)
    arr = np.array(img).astype(int)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
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
    return "نامشخص — نیاز به تصاویر بیشتر", "50%"

def predict_with_model(pil_img: Image.Image):
    img = pil_img.convert("RGB").resize((224,224))
    x = np.array(img)/255.0
    x = np.expand_dims(x, 0)
    preds = _model.predict(x)
    classes = ["سالم", "بیمار", "نیاز به هرس", "کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = float(np.max(preds[0])) if preds is not None else 0.0
    return classes[idx] if idx < len(classes) else "نامشخص", f"{int(confidence*100)}%"

# ---------- UI: Header with local logo ----------
def app_header():
    logo_path = "logo.png"  # لوگوی شما باید در کنار app.py باشد
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode()
        img_tag = f'data:image/png;base64,{encoded_logo}'
    else:
        img_tag = ""  # اگر لوگو پیدا نشد، خالی بماند

    st.markdown(
        f"""
        <div class="app-header">
            <img src="{img_tag}" width="64" style="border-radius:12px; margin-left:12px;">
            <div>
                <h2>سیبتک</h2>
                <div class='subtitle'>سیبتک — مدیریت و پایش نهال</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

app_header()

# ---------- Auth screens ----------
if st.session_state['user_id'] is None:
    col1, col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود", "ثبت‌نام", "دمو"])
    if mode == "ثبت‌نام":
        st.subheader("ثبت‌نام کاربر جدید")
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    sel = sa.select(users_table).where(users_table.c.username == username)
                    r = conn.execute(sel).mappings().first()
                    if r:
                        st.error("این نام کاربری قبلاً ثبت شده است.")
                    else:
                        hashed = hash_password(password)
                        conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                        st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
    elif mode == "ورود":
        st.subheader("ورود به حساب کاربری")
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            with engine.connect() as conn:
                sel = sa.select(users_table).where(users_table.c.username == username)
                r = conn.execute(sel).mappings().first()
                if not r:
                    st.error("نام کاربری یافت نشد.")
                elif check_password(password, r['password_hash']):
                    st.session_state['user_id'] = int(r['id'])
                    st.session_state['username'] = r['username']
                    st.success(f"خوش آمدید، {r['username']} — منو در سمت چپ فعال می‌شود.")
                    st.experimental_rerun = lambda: None
                else:
                    st.error("رمز عبور اشتباه است.")
    else:  # Demo
        st.subheader("حالت دمو — پیش‌بینی نمونه")
        st.info("در حالت دمو داده‌ها در سرور ذخیره نمی‌شوند.")
        f = st.file_uploader("یک تصویر از نهال یا بخشی از آن آپلود کنید", type=["jpg","jpeg","png"])
        if f:
            img = Image.open(f)
            st.image(img, use_container_width=True)
            if _model_loaded:
                label, conf = predict_with_model(img)
            else:
                label, conf = heuristic_predict_potted_seedling(img)
            st.success(f"نتیجه (دمو): {label} — اعتماد: {conf}")

# ---------- Main App ----------
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", [
        "🏠 خانه",
        "🌱 پایش نهال",
        "📅 زمان‌بندی",
        "📈 پیش‌بینی سلامت نهال (تصویر)",
        "🍎 ثبت بیماری / یادداشت",
        "📥 دانلود داده‌ها",
        "🚪 خروج"
    ])
    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.success("شما از حساب کاربری خارج شدید.")
        st.experimental_rerun = lambda: None

# بخش‌های دیگر اپلیکیشن همان بخش‌های قبلی شما هستند، فقط استایل‌ها اعمال شده‌اند
