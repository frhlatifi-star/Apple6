# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageStat
import base64
import os
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# Optional: TensorFlow for real model
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- Page config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS / RTL ----------
st.markdown("""
<style>
:root { --accent: #2e7d32; --accent-2: #388e3c; --bg-1: #eaf9e7; --card: #ffffff; }
body, html { direction: rtl !important; font-family: Vazirmatn, Tahoma, sans-serif; background: linear-gradient(135deg, #eaf9e7, #f7fff8); }
.card { background: var(--card); padding: 1rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 12px; }
.stButton>button { background-color: var(--accent-2) !important; color: white !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ---------- Database setup ----------
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
    Column('task_name', String),
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
for key in ['user_id','username']:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Load model ----------
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

# ---------- Heuristic predictor ----------
def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)
    arr = np.array(img).astype(int)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_ratio = ((r>g)&(g>=b)).mean()
    green_ratio = ((g>r+10)&(g>b+10)).mean()

    # تعیین خودکار نیاز به هرس
    prune_needed = 1 if mean < 50 or yellow_ratio>0.25 else 0

    if green_ratio>0.12 and mean>80: return "سالم", f"{min(99,int(50+green_ratio*200))}%", prune_needed
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25: return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%", prune_needed
        else: return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean/255)*200))}%", prune_needed
    return "نامشخص", "50%", prune_needed

def predict_with_model(img: Image.Image):
    x = np.expand_dims(np.array(img.convert("RGB").resize((224,224)))/255.0,0)
    preds = _model.predict(x)
    classes = ["سالم","بیمار","نیاز به هرس","کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = int(float(np.max(preds[0]))*100)
    return classes[idx], f"{confidence}%", 0

# ---------- Header ----------
def app_header():
    st.markdown("""
    <div style='display:flex;align-items:center;margin-bottom:20px;'>
    <img src='logo.png' width='64' style='margin-left:12px;border-radius:12px;'>
    <div>
    <h2 style='margin:0'>سیبتک</h2>
    <small style='color:#666'>مدیریت و پایش نهال</small>
    </div>
    </div><hr/>
    """, unsafe_allow_html=True)

app_header()

# ---------- Menu ----------
menu_items = ["🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت","🍎 ثبت بیماری","📥 دانلود داده‌ها","🚪 خروج"]
menu_choice = st.selectbox("منو", menu_items, index=0)

user_id = st.session_state['user_id']

# ---------- Authentication ----------
if user_id is None:
    st.subheader("ورود / ثبت‌نام")
    auth_mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    if auth_mode=="ثبت‌نام":
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام"):
            if not username or not password: st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    sel = sa.select(users_table).where(users_table.c.username==username)
                    if conn.execute(sel).mappings().first():
                        st.error("این نام کاربری قبلاً ثبت شده است.")
                    else:
                        conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                        st.success("ثبت‌نام انجام شد. حالا وارد شوید.")
    elif auth_mode=="ورود":
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                if not r: st.error("نام کاربری یافت نشد.")
                elif check_password(password,r['password_hash']):
                    st.session_state['user_id']=r['id']
                    st.session_state['username']=r['username']
                    st.experimental_rerun = lambda: None
                else: st.error("رمز عبور اشتباه است.")
    else:  # Demo
        st.subheader("حالت دمو")
    st.stop()

# ---------- Pages ----------
def page_home():
    st.header("خانه — خلاصه وضعیت")
    with engine.connect() as conn:
        ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
        ps = conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all()
        ds = conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id)).mappings().all()
    st.markdown(f"<div class='card'><h3>تعداد اندازه‌گیری‌ها: {len(ms)}</h3></div>",unsafe_allow_html=True)
    st.markdown(f"<div class='card'><h3>تعداد پیش‌بینی‌ها: {len(ps)}</h3></div>",unsafe_allow_html=True)
    st.markdown(f"<div class='card'><h3>تعداد یادداشت‌های بیماری: {len(ds)}</h3></div>",unsafe_allow_html=True)

def page_monitor():
    st.header("🌱 پایش نهال")
    height = st.number_input("ارتفاع نهال (cm)",min_value=1,max_value=500)
    leaves = st.number_input("تعداد برگ‌ها",min_value=0,max_value=200)
    notes = st.text_area("یادداشت‌ها")
    prune_needed = 1 if (height<50 or leaves<5) else 0
    if st.button("ثبت پایش"):
        with engine.connect() as conn:
            conn.execute(measurements.insert().values(user_id=user_id,
                                                      date=str(datetime.now()),
                                                      height=height,
                                                      leaves=leaves,
                                                      notes=notes,
                                                      prune_needed=prune_needed))
        st.success(f"پایش ثبت شد. نیاز به هرس: {'بله' if prune_needed else 'خیر'}")

def page_schedule():
    st.header("📅 زمان‌بندی")
    task_name = st.text_input("کار / وظیفه")
    task_date = st.date_input("تاریخ")
    notes = st.text_area("یادداشت‌ها")
    if st.button("ثبت کار"):
        with engine.connect() as conn:
            conn.execute(schedule_table.insert().values(user_id=user_id,
                                                        task_name=task_name,
                                                        date=str(task_date),
                                                        notes=notes))
        st.success("کار ثبت شد.")
    with engine.connect() as conn:
        rows = conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id).order_by(schedule_table.c.date.desc())).mappings().all()
        df = pd.DataFrame(rows)
    st.dataframe(df)

def page_prediction():
    st.header("📈 پیش‌بینی سلامت نهال")
    uploaded_file = st.file_uploader("تصویر نهال", type=['png','jpg','jpeg'])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="تصویر بارگذاری شده", use_column_width=True)
        if st.button("پیش‌بینی"):
            if _model_loaded:
                label, conf, prune = predict_with_model(img)
            else:
                label, conf, prune = heuristic_predict(img)
            with engine.connect() as conn:
                conn.execute(predictions_table.insert().values(user_id=user_id,
                                                              file_name=uploaded_file.name,
                                                              result=label,
                                                              confidence=conf,
                                                              date=str(datetime.now())))
            st.success(f"نتیجه: {label} ({conf}) — نیاز به هرس: {'بله' if prune else 'خیر'}")

def page_disease():
    st.header("🍎 ثبت بیماری / یادداشت")
    note = st.text_area("یادداشت بیماری")
    if st.button("ثبت یادداشت"):
        with engine.connect() as conn:
            conn.execute(disease_table.insert().values(user_id=user_id,
                                                       note=note,
                                                       date=str(datetime.now())))
        st.success("یادداشت ثبت شد.")

def page_download():
    st.header("📥 دانلود داده‌ها")
    tables = ["measurements","schedule","predictions","disease"]
    for tname in tables:
        t = meta.tables[tname]
        with engine.connect() as conn:
            df = pd.DataFrame(conn.execute(sa.select(t).where(t.c.user_id==user_id)).mappings().all())
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        st.markdown(f"<a href='data:file/csv;base64,{b64}' download='{tname}.csv'>دانلود {tname}</a>", unsafe_allow_html=True)

# ---------- Render page ----------
pages = {
    "🏠 خانه": page_home,
    "🌱 پایش نهال": page_monitor,
    "📅 زمان‌بندی": page_schedule,
    "📈 پیش‌بینی سلامت": page_prediction,
    "🍎 ثبت بیماری": page_disease,
    "📥 دانلود داده‌ها": page_download
}

pages[menu_choice]()
