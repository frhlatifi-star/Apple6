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

# ---------- Config ----------
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
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None
if 'page' not in st.session_state: st.session_state.page = 'dashboard'

# ---------- Password helpers ----------
def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- App Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path,"rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;'>"
    else: img_html = "🍎"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:10px;'>
        {img_html}<h2 style='margin:0 10px;'>سیبتک</h2>
    </div>
    """, unsafe_allow_html=True)
app_header()

# ---------- Authentication ----------
def auth_ui():
    st.subheader("ورود / ثبت‌نام")
    mode = st.radio("حالت:", ["ورود","ثبت‌نام","ورود مهمان"])
    if mode=="ثبت‌نام":
        u = st.text_input("نام کاربری", key="signup_u")
        p = st.text_input("رمز عبور", type="password", key="signup_p")
        if st.button("ثبت‌نام"):
            if not u or not p: st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    if conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first():
                        st.error("این نام کاربری قبلاً ثبت شده.")
                    else:
                        conn.execute(users_table.insert().values(username=u,password_hash=hash_password(p)))
                        st.success("ثبت‌نام انجام شد. حالا وارد شوید.")
    elif mode=="ورود":
        u = st.text_input("نام کاربری (ورود)", key="login_u")
        p = st.text_input("رمز عبور (ورود)", type="password", key="login_p")
        if st.button("ورود"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first()
                if not r: st.error("نام کاربری یافت نشد.")
                elif check_password(p,r['password_hash']):
                    st.session_state.user_id = int(r['id'])
                    st.session_state.username = r['username']
                    st.session_state.page = 'dashboard'
                    st.experimental_rerun()
                else: st.error("رمز اشتباه است.")
    else:
        st.session_state.user_id = 0
        st.session_state.username = "مهمان"
        st.session_state.page = 'dashboard'
        st.experimental_rerun()

if st.session_state.user_id is None:
    auth_ui()
    st.stop()

# ---------- Dashboard ----------
def dashboard_ui():
    st.subheader(f"خوش آمدید، {st.session_state.username}")
    menu = ["🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت","🍎 ثبت بیماری","📥 دانلود داده‌ها","🚪 خروج"]
    choice = st.selectbox("منو", menu)
    if choice=="🏠 خانه":
        st.write("🏠 خانه")
        with engine.connect() as conn:
            last = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id).order_by(measurements.c.id.desc()).limit(1)).mappings().first()
            st.write("آخرین اندازه‌گیری:", last['height'] if last else "—")
    elif choice=="🌱 پایش نهال":
        st.header("ثبت اندازه‌گیری")
        with st.form("measure_form"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت")
            prune = st.checkbox("نیاز به هرس؟")
            if st.form_submit_button("ثبت"):
                with engine.connect() as conn:
                    conn.execute(measurements.insert().values(
                        user_id=st.session_state.user_id,date=str(date),
                        height=int(height),leaves=int(leaves),
                        notes=notes,prune_needed=int(prune)
                    ))
                    st.success("ثبت شد.")
    elif choice=="📅 زمان‌بندی":
        st.header("زمان‌بندی")
        with st.form("sched_form"):
            task = st.text_input("فعالیت")
            task_date = st.date_input("تاریخ")
            task_notes = st.text_area("یادداشت")
            if st.form_submit_button("ثبت برنامه"):
                with engine.connect() as conn:
                    conn.execute(schedule_table.insert().values(
                        user_id=st.session_state.user_id,
                        task=task,date=str(task_date),notes=task_notes
                    ))
                    st.success("برنامه ثبت شد.")
    elif choice=="📈 پیش‌بینی سلامت":
        st.header("پیش‌بینی سلامت نهال")
        uploaded = st.file_uploader("آپلود تصویر", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            st.info("پیش‌بینی آزمایشی: سالم / نیاز هرس / کم‌آبی")
    elif choice=="🍎 ثبت بیماری":
        st.header("ثبت یادداشت بیماری")
        with st.form("disease_form"):
            note = st.text_area("شرح مشکل")
            if st.form_submit_button("ثبت"):
                with engine.connect() as conn:
                    conn.execute(disease_table.insert().values(
                        user_id=st.session_state.user_id,note=note,date=str(datetime.now())
                    ))
                    st.success("ثبت شد.")
    elif choice=="📥 دانلود داده‌ها":
        st.header("دانلود داده‌ها")
        with engine.connect() as conn:
            ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id)).mappings().all()
            if ms: df = pd.DataFrame(ms); st.download_button("دانلود اندازه‌گیری‌ها",df.to_csv(index=False).encode(), "measurements.csv")
    elif choice=="🚪 خروج":
        st.session_state.user_id = None
        st.session_state.username = None
        st.experimental_rerun()

dashboard_ui()
