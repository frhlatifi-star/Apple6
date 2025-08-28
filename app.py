# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageStat
import os
import base64
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# --- Optional TensorFlow ---
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
.block-container { direction: rtl !important; text-align: right !important; padding: 1.2rem 2rem; background: linear-gradient(135deg, #eaf9e7, #f7fff8); }
body { font-family: Vazirmatn, Tahoma, sans-serif; background: linear-gradient(135deg, #eaf9e7, #f7fff8) !important; }
.stButton>button { background-color: var(--accent-2) !important; color: white !important; border-radius: 8px !important; }
table { direction: rtl !important; text-align: right !important; }
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
for key in ['user_id', 'username', 'demo_history']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'demo_history' else []

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Model ----------
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
    if green_ratio>0.12 and mean>80:
        return "سالم", f"{min(99,int(50+green_ratio*200))}%"
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25:
            return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%"
        else:
            return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean/255)*200))}%"
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
            img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;margin-left:12px;'>"
    else:
        img_html = "<div style='font-size:36px;'>🍎</div>"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:20px;'>
        {img_html}
        <div>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#666'>مدیریت و پایش نهال</small>
        </div>
    </div>
    <hr/>
    """, unsafe_allow_html=True)

app_header()

# ---------- Authentication ----------
if st.session_state['user_id'] is None:
    st.write("")
    col1,col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2:
        st.write("")
    
    if mode=="ثبت‌نام":
        st.subheader("ثبت‌نام کاربر جدید")
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                try:
                    with engine.connect() as conn:
                        sel = sa.select(users_table).where(users_table.c.username==username)
                        if conn.execute(sel).mappings().first():
                            st.error("این نام کاربری قبلاً ثبت شده است.")
                        else:
                            conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                            st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
                except Exception as e:
                    st.error(f"خطا در ثبت‌نام: {e}")
    
    elif mode=="ورود":
        st.subheader("ورود به حساب کاربری")
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            try:
                with engine.connect() as conn:
                    r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                    if not r:
                        st.error("نام کاربری یافت نشد.")
                    elif check_password(password,r['password_hash']):
                        st.session_state['user_id']=int(r['id'])
                        st.session_state['username']=r['username']
                        st.experimental_rerun = lambda: None
                    else:
                        st.error("رمز عبور اشتباه است.")
            except Exception as e:
                st.error(f"خطا در ورود: {e}")
    
    else: # Demo
        st.subheader("حالت دمو — پیش‌بینی نمونه")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded:
                label,conf = predict_with_model(img)
            else:
                label,conf = heuristic_predict(img)
            color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
            st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)

# ---------- Sidebar and Dashboard ----------
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو",[
        "🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت نهال",
        "🍎 ثبت بیماری / یادداشت","📥 دانلود داده‌ها","🚪 خروج"
    ])
    user_id = st.session_state['user_id']
    if menu=="🚪 خروج":
        st.session_state['user_id']=None
        st.session_state['username']=None
        st.experimental_rerun = lambda: None

# --- ادامه بخش‌ها مانند پایش، زمان‌بندی، پیش‌بینی و بیماری می‌تواند مشابه قبل اضافه شود ---
