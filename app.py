# sebetek_dashboard_final.py
import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat
import numpy as np
import os

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS حرفه‌ای ----------
st.markdown("""
<style>
html, body, [class*="css"] { direction: rtl !important; text-align: right !important; font-family: 'Vazirmatn', sans-serif; background-color: #e6f2e6;}
.stButton>button { cursor: pointer; background-color: #4CAF50; color: white; border-radius: 12px; padding: 10px 20px; font-weight: bold; margin-top:5px;}
.stButton>button:hover { background-color: #45a049; }
.card { background-color: #ffffff; border-radius: 16px; padding: 20px; box-shadow: 0 6px 20px rgba(0,0,0,0.12); margin-bottom: 20px; }
.card h3 { margin: 0; font-size:18px;}
.card .metric { font-size: 28px; font-weight: bold; }
.card .icon { font-size: 28px; margin-left:10px; }
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)
measurements = Table('measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)
schedule_table = Table('schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)
predictions_table = Table('predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)
disease_table = Table('disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)
meta.create_all(engine)

# ---------- Session ----------
for key in ['user_id','username','demo_history']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'demo_history' else []

# ---------- Password Helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Header ----------
def app_header():
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:20px;'>
        <img src='https://i.imgur.com/4Y2E2XQ.png' width='64' style='margin-left:12px;border-radius:16px;'>
        <div>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#666'>مدیریت و پایش نهال</small>
        </div>
    </div><hr/>
    """, unsafe_allow_html=True)
app_header()

# ---------- Main ----------
if st.session_state['user_id'] is None:
    col1,col2 = st.columns([1,2])
    with col1: mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2: st.write("")
    st.info("برای مشاهده داشبورد، لطفاً وارد شوید یا ثبت‌نام کنید.")
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو",[
        "🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت نهال",
        "🍎 ثبت بیماری / یادداشت","📥 دانلود داده‌ها","🚪 خروج"])
    user_id = st.session_state['user_id']

    if menu=="🚪 خروج":
        st.session_state['user_id']=None
        st.session_state['username']=None
        st.experimental_rerun = lambda: None

    # ---------- Home ----------
    if menu=="🏠 خانه":
        st.header("🏡 داشبورد اصلی")
        with engine.connect() as conn:
            ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
            ps = conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all()
            ds = conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id)).mappings().all()
        col1,col2,col3 = st.columns(3)
        col1.markdown(f"<div class='card'><span class='icon'>🌱</span><h3>اندازه‌گیری‌ها</h3><div class='metric'>{len(ms)}</div></div>",unsafe_allow_html=True)
        col2.markdown(f"<div class='card'><span class='icon'>📈</span><h3>پیش‌بینی‌ها</h3><div class='metric'>{len(ps)}</div></div>",unsafe_allow_html=True)
        col3.markdown(f"<div class='card'><span class='icon'>🍎</span><h3>یادداشت‌ها</h3><div class='metric'>{len(ds)}</div></div>",unsafe_allow_html=True)
        if ms:
            df = pd.DataFrame(ms)
            try:
                df_plot = df.copy()
                df_plot['date'] = pd.to_datetime(df_plot['date'])
                st.subheader("📊 روند رشد نهال")
                st.line_chart(df_plot.set_index('date')['height'])
                st.line_chart(df_plot.set_index('date')['leaves'])
            except Exception as e:
                st.warning(f"خطا در رسم نمودار: {e}")

    # ---------- ادامه داشبورد مثل نسخه قبل با بلوک‌های try/except درست برای هر بخش ----------

