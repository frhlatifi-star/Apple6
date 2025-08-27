# app_seedling_pro_full_complete_final.py
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

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro Full", layout="wide")

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

# ---------- Database ----------
DB_FILE = "users_seedling_full_complete_final.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False),
                    Column('role', String, default='user'))

data_table = Table('user_data', meta,
                   Column('id', Integer, primary_key=True),
                   Column('username', String),
                   Column('date', String),
                   Column('height', Integer),
                   Column('leaves', Integer),
                   Column('notes', String),
                   Column('prune', String),
                   Column('task', String),
                   Column('task_done', String))

meta.create_all(engine)

# ---------- Model ----------
@st.cache_resource
def load_model_cached(path="leaf_model.h5"):
    try: return tf.keras.models.load_model(path)
    except: return None
model = load_model_cached("leaf_model.h5")

class_labels = ["apple_healthy", "apple_black_spot", "apple_powdery_mildew"]
disease_info = {
    "apple_black_spot": {"name": t("لکه سیاه ⚫️","Black Spot ⚫️"), "desc": t("لکه‌های سیاه روی برگ و میوه.","Black spots on leaves/fruit."), "treatment": t("قارچ‌کش، هرس و جمع‌آوری برگ‌ها","Fungicide, prune, remove fallen leaves")},
    "apple_powdery_mildew": {"name": t("سفیدک پودری ❄️","Powdery Mildew ❄️"), "desc": t("سطح برگ سفید و پودری می‌شود.","White powdery surface on leaves."), "treatment": t("گوگرد، هرس و تهویه","Sulfur spray, pruning, ventilation")},
    "apple_healthy": {"name": t("برگ سالم ✅","Healthy ✅"), "desc": t("برگ سالم است.","Leaf is healthy."), "treatment": t("ادامه مراقبت‌های معمول","Continue standard care")}
}

def predict_probs(file):
    if model is None: return np.array([1.0,0.0,0.0])
    img = Image.open(file).convert("RGB")
    target_size = model.input_shape[1:3]
    img = img.resize(target_size)
    arr = img_to_array(img)/255.0
    arr = np.expand_dims(arr, axis=0)
    preds = model.predict(arr)[0]
    return preds

# ---------- Session ----------
if 'user' not in st.session_state: st.session_state['user'] = None
if 'role' not in st.session_state: st.session_state['role'] = None
if 'tree_data' not in st.session_state: st.session_state['tree_data'] = pd.DataFrame(columns=['date','height','leaves','notes','prune'])
if 'schedule' not in st.session_state: st.session_state['schedule'] = pd.DataFrame(columns=['date','task','task_done'])
if 'df_future' not in st.session_state: st.session_state['df_future'] = pd.DataFrame()

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

def load_user_data(username):
    with engine.begin() as conn:
        rows = conn.execute(sa.select(data_table).where(data_table.c.username==username)).fetchall()
    df = pd.DataFrame([r._mapping for r in rows])
    if not df.empty:
        st.session_state['tree_data'] = df[['date','height','leaves','notes','prune']]
        st.session_state['schedule'] = df[['date','task','task_done']]
    else:
        st.session_state['tree_data'] = pd.DataFrame(columns=['date','height','leaves','notes','prune'])
        st.session_state['schedule'] = pd.DataFrame(columns=['date','task','task_done'])

# ---------- Auth UI ----------
if st.session_state['user'] is None:
    mode = st.sidebar.radio(t("حالت","Mode"), [t("ورود","Login"), t("ثبت نام","Sign Up"), t("دمو","Demo")])
    username = st.text_input(t("نام کاربری","Username"))
    password = st.text_input(t("رمز عبور","Password"), type="password")

    if mode == t("ثبت نام","Sign Up") and st.button(t("ثبت نام","Register")):
        if username and password:
            register(username, password)
            st.success(t("ثبت نام انجام شد. اکنون وارد شوید.","Registered successfully. Please login."))
        else: st.error(t("نام کاربری و رمز را وارد کنید.","Provide username & password."))

    if mode == t("ورود","Login") and st.button(t("ورود","Login")):
        role = login(username, password)
        if role:
            st.session_state['user'] = username
            st.session_state['role'] = role
            load_user_data(username)
            st.experimental_rerun()
        else: st.error(t("نام کاربری یا رمز اشتباه است.","Wrong username or password."))

    if mode == t("دمو","Demo"):
        st.header(t("دمو","Demo Mode"))
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

# ---------- Main App ----------
else:
    menu = st.sidebar.selectbox(t("منو","Menu"), [t("🏠 خانه","Home"), t("🍎 تشخیص بیماری","Disease"), t("🌱 ثبت و رصد","Tracking"), t("📅 برنامه زمان‌بندی","Schedule"), t("📈 پیش‌بینی رشد","Prediction"), t("📥 دانلود گزارش","Download"), t("🚪 خروج","Logout")])
    
    if menu == t("🚪 خروج","Logout"):
        st.session_state['user'] = None
        st.experimental_rerun()

    # ---------- Tracking ----------
    if menu == t("🌱 ثبت و رصد","Tracking"):
        st.header(t("ثبت و رصد رشد نهال","Seedling Tracking"))
        with st.expander(t("➕ ثبت اندازه‌گیری جدید","➕ Add Measurement")):
            date = st.date_input(t("تاریخ","Date"), value=datetime.today())
            height = st.number_input(t("ارتفاع (cm)","Height (cm)"), min_value=0.0, step=0.5)
            leaves = st.number_input(t("تعداد برگ‌ها","Leaves"), min_value=0, step=1)
            notes = st.text_area(t("توضیحات","Notes"))
            prune = st.checkbox(t("نیاز به هرس؟","Prune needed?"))
            if st.button(t("ثبت","Submit")):
                new_row = pd.DataFrame([[date, height, leaves, notes, prune]], columns=['date','height','leaves','notes','prune'])
                st.session_state['tree_data'] = pd.concat([st.session_state['tree_data'], new_row], ignore_index=True)
                st.success(t("ثبت شد ✅","Added ✅"))
        if not st.session_state['tree_data'].empty:
            st.dataframe(st.session_state['tree_data'])
            fig = px.line(st.session_state['tree_data'], x='date', y='height', title=t("روند ارتفاع","Height Trend"))
            st.plotly_chart(fig, use_container_width=True)
