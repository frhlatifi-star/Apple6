# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import os
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat

# ---------- TensorFlow (optional) ----------
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
:root {
  --accent: #2e7d32;
  --accent-2: #388e3c;
  --bg-1: #eaf9e7;
  --card: #ffffff;
}
html, body, [class*="css"] {direction: rtl !important; text-align: right !important;}
body {font-family: Vazirmatn, Tahoma, sans-serif; background: linear-gradient(135deg,#eaf9e7,#f7fff8);}
.stButton>button {background-color: var(--accent-2) !important; color:white !important; border-radius:8px !important;}
.card {background: var(--card); padding:1.1rem; border-radius:14px; box-shadow:0 6px 18px rgba(20,20,20,0.06); text-align:center;}
.card:hover {transform: translateY(-6px); box-shadow:0 10px 26px rgba(20,20,20,0.09);}
.card-icon {font-size:28px; color: var(--accent-2); margin-bottom:6px;}
</style>
""", unsafe_allow_html=True)

# ---------- Database setup ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# Users table
users_table = Table('users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)
# Measurements table
measurements = Table('measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)
# Schedule table
schedule_table = Table('schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)
# Predictions table
predictions_table = Table('predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)
# Disease table
disease_table = Table('disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)
meta.create_all(engine)

# ---------- Session defaults ----------
for key in ['user_id','username','page']:
    if key not in st.session_state:
        st.session_state[key] = None
if 'demo_history' not in st.session_state:
    st.session_state.demo_history = []

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Model setup ----------
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

# ---------- Heuristic prediction ----------
def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)
    arr = np.array(img).astype(int)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_ratio = ((r>g)&(g>=b)).mean()
    green_ratio = ((g>r+10)&(g>b+10)).mean()
    if green_ratio>0.12 and mean>80: return "سالم", f"{min(99,int(50+green_ratio*200))}%"
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25: return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%"
        else: return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean/255)*200))}%"
    return "نامشخص", "50%"

def predict_with_model(img: Image.Image):
    x = np.expand_dims(np.array(img.convert("RGB").resize((224,224)))/255.0,0)
    preds = _model.predict(x)
    classes = ["سالم","بیمار","نیاز به هرس","کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = int(float(np.max(preds[0]))*100)
    return classes[idx], f"{confidence}%"

# ---------- UI Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path,"rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;'>"
    else:
        img_html = "<div style='font-size:36px;'>🍎</div>"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:12px;'>{img_html}
        <div style='margin-right:8px;'>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#666'>مدیریت و پایش نهال</small>
        </div>
    </div><hr/>
    """, unsafe_allow_html=True)

app_header()

# ---------- Authentication ----------
def auth_ui():
    st.write("")
    col1,col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"], key="auth_mode")
    with col2: st.write("")
    
    if mode=="ثبت‌نام":
        st.subheader("ثبت‌نام کاربر جدید")
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام", key="signup_btn"):
            if not username or not password: st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    sel = sa.select(users_table).where(users_table.c.username==username)
                    if conn.execute(sel).mappings().first():
                        st.error("این نام کاربری قبلاً ثبت شده است.")
                    else:
                        conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                        st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
                        
    elif mode=="ورود":
        st.subheader("ورود به حساب کاربری")
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود", key="login_btn"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                if not r: st.error("نام کاربری یافت نشد.")
                elif check_password(password,r['password_hash']):
                    st.session_state.user_id = int(r['id'])
                    st.session_state.username = r['username']
                    st.experimental_rerun()
                else: st.error("رمز عبور اشتباه است.")
    else:
        # Demo mode
        st.subheader("دمو — پیش‌بینی نمونه")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"], key="demo_upload")
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded:
                result,conf = predict_with_model(img)
            else:
                result,conf = heuristic_predict(img)
            st.success(f"نتیجه: {result} ({conf})")

# ---------- Dashboard ----------
def dashboard_ui():
    st.subheader(f"سلام {st.session_state.username} 👋")
    cards = [
        {"label":"ثبت اندازه‌گیری","icon":"📏","func":measure_ui},
        {"label":"برنامه زمان‌بندی","icon":"🗓️","func":schedule_ui},
        {"label":"پیش‌بینی بیماری","icon":"🔬","func":predict_ui},
        {"label":"ثبت یادداشت بیماری","icon":"📝","func":disease_ui},
        {"label":"خروج","icon":"🚪","func":logout_ui}
    ]
    
    col_count = len(cards)
    cols = st.columns(col_count)
    for idx,card in enumerate(cards):
        with cols[idx]:
            if st.button(f"{card['icon']} {card['label']}", key=f"dashboard_btn_{idx}"):
                card['func']()

# ---------- Logout ----------
def logout_ui():
    for key in ['user_id','username','page']:
        st.session_state[key]=None
    st.experimental_rerun()

# ---------- Measurement ----------
def measure_ui():
    st.subheader("ثبت اندازه‌گیری نهال")
    with st.form("add_measure"):
        date = st.date_input("تاریخ", value=datetime.today(), key="measure_date")
        height = st.number_input("ارتفاع (cm)", min_value=0, step=1, key="measure_height")
        leaves = st.number_input("تعداد برگ", min_value=0, step=1, value=0, key="measure_leaves")
        notes = st.text_area("یادداشت", key="measure_notes")
        prune = st.checkbox("نیاز به هرس؟", key="measure_prune")
        submitted = st.form_submit_button("ثبت اندازه‌گیری", key="measure_submit")
        if submitted:
            with engine.connect() as conn:
                conn.execute(measurements.insert().values(
                    user_id=st.session_state.user_id,
                    date=str(date),
                    height=int(height),
                    leaves=int(leaves),
                    notes=notes,
                    prune_needed=int(prune)
                ))
            st.success("اندازه‌گیری ثبت شد.")

# ---------- Schedule ----------
def schedule_ui():
    st.subheader("برنامه زمان‌بندی نهال")
    with st.form("add_sched"):
        task = st.text_input("فعالیت", key="sched_task")
        task_date = st.date_input("تاریخ برنامه", key="sched_date")
        task_notes = st.text_area("یادداشت", key="sched_notes")
        sub = st.form_submit_button("ثبت برنامه", key="sched_submit")
        if sub:
            with engine.connect() as conn:
                conn.execute(schedule_table.insert().values(
                    user_id=st.session_state.user_id,
                    task=task,date=str(task_date),notes=task_notes
                ))
            st.success("برنامه ثبت شد.")

# ---------- Disease ----------
def disease_ui():
    st.subheader("ثبت یادداشت بیماری نهال")
    with st.form("add_disease"):
        note = st.text_area("شرح مشکل یا علائم", key="disease_note")
        sub = st.form_submit_button("ثبت یادداشت", key="disease_submit")
        if sub:
            with engine.connect() as conn:
                conn.execute(disease_table.insert().values(
                    user_id=st.session_state.user_id,
                    note=note,
                    date=str(datetime.today())
                ))
            st.success("یادداشت ثبت شد.")

# ---------- Predict ----------
def predict_ui():
    st.subheader("پیش‌بینی سلامت نهال")
    uploaded = st.file_uploader("انتخاب تصویر", type=["jpg","jpeg","png"], key="predict_upload")
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        if _model_loaded:
            result,conf = predict_with_model(img)
        else:
            result,conf = heuristic_predict(img)
        st.success(f"نتیجه: {result} ({conf})")
        with engine.connect() as conn:
            conn.execute(predictions_table.insert().values(
                user_id=st.session_state.user_id,
                file_name=uploaded.name,
                result=result,
                confidence=conf,
                date=str(datetime.today())
            ))

# ---------- Router ----------
def router():
    if st.session_state.user_id is None:
        auth_ui()
    else:
        dashboard_ui()

# ---------- Run ----------
router()
