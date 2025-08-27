# app_seedling_pro_final_full_v3.py
import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow.keras.utils import img_to_array
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData
import bcrypt
import io
import plotly.express as px
import os

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro Full Dashboard", layout="wide")

# ---------- Language Helper ----------
lang = st.sidebar.selectbox("Language / زبان", ["English", "فارسی"])
EN = (lang == "English")
def t(fa, en): return en if EN else fa

# ---------- Styles ----------
st.markdown("""
<style>
.kpi-card{background:#ffffffdd;border-radius:14px;padding:14px;margin-bottom:16px;box-shadow:0 6px 20px rgba(0,0,0,0.15);transition:transform 0.2s;}
.kpi-card:hover{transform:scale(1.03);}
.kpi-title{font-size:16px;font-weight:bold;color:#333;}
.kpi-value{font-size:28px;font-weight:bold;color:#2d9f3f;}
.task-done{background:#d1ffd1;}
.task-pending{background:#ffe6e6;}
body{font-family: 'Vazir', sans-serif; direction: rtl;}
</style>
""", unsafe_allow_html=True)

# ---------- Database (Persistent) ----------
DB_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "users_seedling_full_v3.db")
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False),
                    Column('role', String, default='user'))
meta.create_all(engine)

# ---------- Session ----------
if 'user' not in st.session_state: st.session_state['user'] = None
if 'role' not in st.session_state: st.session_state['role'] = None
if 'tree_data' not in st.session_state: st.session_state['tree_data'] = pd.DataFrame(columns=['date','height','leaves','notes','prune'])
if 'schedule' not in st.session_state: 
    start_date = datetime.today()
    schedule_list = []
    for week in range(52):
        date = start_date + timedelta(weeks=week)
        schedule_list.append([date.date(), t("آبیاری","Watering"), False])
        if week % 4 == 0:
            schedule_list.append([date.date(), t("کوددهی","Fertilization"), False])
        if week % 12 == 0:
            schedule_list.append([date.date(), t("هرس","Pruning"), False])
        if week % 6 == 0:
            schedule_list.append([date.date(), t("بازرسی بیماری","Disease Check"), False])
    st.session_state['schedule'] = pd.DataFrame(schedule_list, columns=['date','task','task_done'])
if 'df_future' not in st.session_state: st.session_state['df_future'] = pd.DataFrame()

# ---------- Disease Metadata ----------
class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name": t("لکه سیاه ⚫️","Black Spot ⚫️"), "desc": t("لکه‌های سیاه روی برگ و میوه.","Black spots on leaves/fruit."), "treatment": t("قارچ‌کش، هرس و جمع‌آوری برگ‌ها","Fungicide, prune, remove fallen leaves")},
    "apple_powdery_mildew": {"name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"), "desc": t("سطح برگ سفید و پودری می‌شود.","White powdery surface on leaves."), "treatment": t("گوگرد، هرس و تهویه","Sulfur spray, pruning, ventilation")},
    "apple_healthy": {"name": t("برگ سالم ✅","Healthy ✅"), "desc": t("برگ سالم است.","Leaf is healthy."), "treatment": t("ادامه مراقبت‌های معمول","Continue standard care")}
}

# ---------- Load Model ----------
@st.cache_resource
def load_model_cached(path="leaf_model.h5"):
    try:
        return tf.keras.models.load_model(path)
    except:
        return None
model = load_model_cached()

# ---------- Auth Functions ----------
def register(username, password, role='user'):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        conn.execute(users_table.insert().values(username=username, password_hash=hashed, role=role))

def login(username, password):
    with engine.begin() as conn:
        r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).first()
        if r:
            stored_hash = r._mapping['password_hash']
            role = r._mapping['role']
            if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                return role
        return None

# ---------- Auth UI ----------
mode = st.sidebar.radio(t("حالت","Mode"), [t("ورود","Login"), t("ثبت نام","Sign Up"), t("دمو","Demo")])
username = st.text_input(t("نام کاربری","Username"))
password = st.text_input(t("رمز عبور","Password"), type="password")

if mode == t("ثبت نام","Sign Up") and st.button(t("ثبت نام","Register")):
    if username and password:
        register(username, password)
        st.success(t("ثبت نام انجام شد. اکنون وارد شوید.","Registered successfully. Please login."))
    else:
        st.error(t("نام کاربری و رمز را وارد کنید.","Provide username & password."))

if mode == t("ورود","Login") and st.button(t("ورود","Login")):
    role = login(username, password)
    if role:
        st.session_state['user'] = username
        st.session_state['role'] = role
        st.success(t("ورود موفق ✅","Login successful ✅"))

# ---------- Demo Mode ----------
if mode == t("دمو","Demo"):
    st.header(t("دمو","Demo"))
    st.info(t("در حالت دمو بدون ثبت نام می‌توانید تصویر آپلود کنید و مدل (در صورت وجود) را تست کنید.","In demo mode you can upload image and test model without login."))
    f = st.file_uploader(t("آپلود تصویر برگ","Upload leaf image"), type=["jpg","jpeg","png"])
    if f:
        st.image(f, use_container_width=True)
        if model is not None:
            img = Image.open(f).convert("RGB")
            img = img.resize(model.input_shape[1:3])
            arr = img_to_array(img)/255.0
            arr = np.expand_dims(arr, axis=0)
            preds = model.predict(arr)[0]
        else:
            preds = np.array([1.0, 0.0, 0.0])
        idx = int(np.argmax(preds))
        st.write(f"**{t('نتیجه','Result')}:** {disease_info[class_labels[idx]]['name']}")
        st.write(f"**{t('شدت بیماری (%)','Severity (%)')}:** {preds[idx]*100:.1f}%")
        st.write(f"**{t('توضیح','Description')}:** {disease_info[class_labels[idx]]['desc']}")
        st.write(f"**{t('درمان / راهنمایی','Treatment / Guidance')}:** {disease_info[class_labels[idx]]['treatment']}")

# ---------- Dashboard for Logged-in Users ----------
if st.session_state['user'] and mode != t("دمو","Demo"):
    st.write(f"{t('خوش آمدید','Welcome')}, {st.session_state['user']}!")
    menu = st.sidebar.selectbox(t("منو","Menu"), [t("🏠 خانه","Home"), t("🍎 تشخیص بیماری","Disease"), t("🌱 ثبت و رصد","Tracking"), t("📅 برنامه زمان‌بندی","Schedule"), t("📈 پیش‌بینی رشد","Prediction"), t("📥 دانلود گزارش","Download"), t("🚪 خروج","Logout")])

    if menu == t("🚪 خروج","Logout"):
        st.session_state['user'] = None
        st.experimental_rerun()

    # ---------- HOME ----------
    if menu == t("🏠 خانه","Home"):
        st.header(t("داشبورد","Overview"))
        df = st.session_state['tree_data']
        last = df.sort_values('date').iloc[-1] if not df.empty else None
        c1,c2,c3,c4 = st.columns([1,1,1,2])
        with c1: st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{t('ارتفاع آخرین اندازه','Last height')}</div><div class='kpi-value'>{(str(last['height'])+' cm') if last is not None else '--'}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{t('تعداد برگ‌ها','Leaves')}</div><div class='kpi-value'>{(int(last['leaves']) if last is not None else '--')}</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{t('وضعیت هرس','Prune Status')}</div><div class='kpi-value'>{t('⚠️ نیاز به هرس','⚠️ Prune needed') if (last is not None and last['prune']) else t('✅ سالم','✅ Healthy')}</div></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{t('نکته','Quick Tip')}</div>{t('برای نگهداری بهتر، هفته‌ای یکبار بررسی کنید.','Check seedlings weekly for best care.')}</div>", unsafe_allow_html=True)
