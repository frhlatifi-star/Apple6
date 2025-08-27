# app.py (FINAL, FULL + SQLite persistent + default schedule)
import streamlit as st
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from PIL import Image
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData
import bcrypt
import os

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Styles ----------
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
:root{--accent:#2d9f3f;--card-bg:rgba(255,255,255,0.95)}
body{font-family:'Vazir',sans-serif;direction:rtl;
background-image: linear-gradient(180deg, #e6f2ea 0%, #d9eef0 40%, #cfeef0 100%), url('https://images.unsplash.com/photo-1506806732259-39c2d0268443?auto=format&fit=crop&w=1470&q=80');
background-size:cover;background-attachment:fixed;color:#0f172a;}
.kpi-card{background:var(--card-bg);border-radius:12px;padding:12px;box-shadow:0 8px 24px rgba(7,10,25,0.08);margin-bottom:8px}
.section{background:linear-gradient(180deg, rgba(255,255,255,0.86), rgba(255,255,255,0.78));border-radius:12px;padding:12px}
.logo-row{display:flex;align-items:center;gap:10px}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers & Translations ----------
lang = st.sidebar.selectbox("🌐 Language / زبان", ["فارسی", "English"])
EN = (lang == "English")
def t(fa, en): return en if EN else fa

# ---------- Logo display ----------
logo_path = "logo.svg"
if os.path.exists(logo_path):
    with open(logo_path, 'r', encoding='utf-8') as f:
        svg = f.read()
    st.markdown(f"<div class='logo-row'>{svg}</div>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1>🍎 Seedling Pro — {t('داشبورد نهال سیب','Apple Seedling Dashboard')}</h1>")

# ---------- Model loading ----------
@st.cache_resource
def load_model_cached(path="leaf_model.h5"):
    try:
        return tf.keras.models.load_model(path)
    except:
        return None

model = load_model_cached("leaf_model.h5")

# ---------- disease metadata ----------
class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name": t("لکه سیاه ⚫️","Black Spot ⚫️"), "desc": t("لکه‌های سیاه روی برگ و میوه.","Black spots on leaves/fruit."), "treatment": t("قارچ‌کش، هرس و جمع‌آوری برگ‌ها","Fungicide, prune, remove fallen leaves")},
    "apple_powdery_mildew": {"name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"), "desc": t("سطح برگ سفید و پودری می‌شود.","White powdery surface on leaves."), "treatment": t("گوگرد، هرس و تهویه","Sulfur spray, pruning, ventilation")},
    "apple_healthy": {"name": t("برگ سالم ✅","Healthy ✅"), "desc": t("برگ سالم است.","Leaf is healthy."), "treatment": t("ادامه مراقبت‌های معمول","Continue standard care")}
}

def predict_probs(file):
    if model is None:
        return np.array([1.0,0.0,0.0])
    img = Image.open(file).convert("RGB")
    target_size = model.input_shape[1:3]
    img = img.resize(target_size)
    arr = img_to_array(img)/255.0
    arr = np.expand_dims(arr, axis=0)
    preds = model.predict(arr)[0]
    return preds

# ---------- SQLite ----------
DB_FILE = "users.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# tables
users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))

tree_table = Table('tree_data', meta,
                   Column('id', Integer, primary_key=True),
                   Column('username', String, nullable=False),
                   Column('date', String),
                   Column('height', Integer),
                   Column('leaves', Integer),
                   Column('notes', String),
                   Column('prune', String))

schedule_table = Table('schedule', meta,
                       Column('id', Integer, primary_key=True),
                       Column('username', String, nullable=False),
                       Column('date', String),
                       Column('task', String),
                       Column('desc', String),
                       Column('done', String))

meta.create_all(engine)
conn = engine.connect()

# ---------- Session state ----------
if 'user' not in st.session_state: st.session_state['user'] = None
if 'tree_data' not in st.session_state: st.session_state['tree_data'] = pd.DataFrame(columns=['id','username','date','height','leaves','notes','prune'])
if 'schedule' not in st.session_state: st.session_state['schedule'] = pd.DataFrame(columns=['id','username','date','task','desc','done'])

# ---------- Default schedule ----------
def create_default_schedule(username):
    start_date = datetime.today()
    schedule_list = []
    for week in range(52):
        date = start_date + timedelta(weeks=week)
        schedule_list.append({
            'username': username,
            'date': str(date.date()),
            'task': t("آبیاری","Watering"),
            'desc': t("آبیاری منظم","Regular watering"),
            'done': "False"
        })
        if week % 4 == 0:
            schedule_list.append({
                'username': username,
                'date': str(date.date()),
                'task': t("کوددهی","Fertilization"),
                'desc': t("تغذیه متعادل","Balanced feeding"),
                'done': "False"
            })
        if week % 12 == 0:
            schedule_list.append({
                'username': username,
                'date': str(date.date()),
                'task': t("هرس","Pruning"),
                'desc': t("هرس شاخه‌های اضافه یا خشک","Prune extra/dry branches"),
                'done': "False"
            })
        if week % 6 == 0:
            schedule_list.append({
                'username': username,
                'date': str(date.date()),
                'task': t("بازرسی بیماری","Disease Check"),
                'desc': t("بررسی برگ‌ها","Check leaves for disease"),
                'done': "False"
            })
    for item in schedule_list:
        conn.execute(schedule_table.insert().values(**item))

# ---------- Load user data ----------
def load_user_data(username):
    sel_tree = sa.select(tree_table).where(tree_table.c.username==username)
    rows = conn.execute(sel_tree).fetchall()
    st.session_state['tree_data'] = pd.DataFrame(rows, columns=['id','username','date','height','leaves','notes','prune'])

    sel_sched = sa.select(schedule_table).where(schedule_table.c.username==username)
    rows = conn.execute(sel_sched).fetchall()
    st.session_state['schedule'] = pd.DataFrame(rows, columns=['id','username','date','task','desc','done'])

# ---------- Auth ----------
if st.session_state['user'] is None:
    mode = st.sidebar.radio(t("حالت","Mode"), (t("ورود","Login"), t("ثبت نام","Sign Up"), t("دمو","Demo")))
    if mode == t("ثبت نام","Sign Up"):
        st.header(t("ثبت نام","Sign Up"))
        username = st.text_input(t("نام کاربری","Username"))
        password = st.text_input(t("رمز عبور","Password"), type="password")
        if st.button(t("ثبت نام","Register")):
            if not username or not password:
                st.error(t("نام کاربری و رمز را وارد کنید.","Provide username & password."))
            else:
                sel = sa.select(users_table).where(users_table.c.username==username)
                r = conn.execute(sel).first()
                if r:
                    st.error(t("نام کاربری قبلا ثبت شده است.","Username already exists."))
                else:
                    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    create_default_schedule(username)
                    load_user_data(username)
                    st.success(t("ثبت نام انجام شد. اکنون وارد شوید.","Registered. Please login."))

    elif mode == t("ورود","Login"):
        st.header(t("ورود","Login"))
        username = st.text_input(t("نام کاربری","Username"))
        password = st.text_input(t("رمز عبور","Password"), type="password")
        if st.button(t("ورود","Login")):
            sel = sa.select(users_table).where(users_table.c.username == username)
            r = conn.execute(sel).first()
            if not r:
                st.error(t("نام کاربری وجود ندارد.","Username not found."))
            else:
                stored = r['password_hash']
                if bcrypt.checkpw(password.encode(), stored.encode()):
                    st.session_state['user'] = username
                    st.success(t("ورود موفق ✅","Login successful ✅"))
                    load_user_data(username)
                    # اگر کاربر اولین بار است و schedule خالی است
                    if st.session_state['schedule'].empty:
                        create_default_schedule(username)
                        load_user_data(username)
                else:
                    st.error(t("رمز صحیح نیست.","Wrong password."))

    else:
        # Demo
        st.header(t("دمو","Demo"))
        st.info(t("در حالت دمو بدون ثبت نام می‌توانید تصویر آپلود کنید و مدل (در صورت وجود) را تست کنید.","In demo you can upload image and test the model."))
        f = st.file_uploader(t("آپلود تصویر برگ","Upload leaf image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_column_width=True)
            preds = predict_probs(f)
            idx = int(np.argmax(preds))
            for i, cls in enumerate(class_labels):
                pct = preds[i]*100
                color = "#2d9f3f" if cls=="apple_healthy" else "#e53935"
                st.markdown(f"<div style='margin-top:8px'><div style='background:#f1f5f9;border-radius:10px;padding:6px'><div style='background:{color};color:#fff;padding:6px;border-radius:6px;width:{int(pct)}%'>{pct:.1f}% {disease_info[cls]['name']}</div></div></div>", unsafe_allow_html=True)
            info = disease_info[class_labels[idx]]
            st.success(f"{t('نتیجه','Result')}: {info['name']}")
            st.write(f"**{t('توضیح','Description')}:** {info['desc']}")
            st.write(f"**{t('درمان','Treatment')}:** {info['treatment']}")
