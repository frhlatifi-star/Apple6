# app_sidebar.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageStat
import os, base64, bcrypt, sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# CSS RTL و فونت فارسی
st.markdown("""
<style>
body {font-family: Vazirmatn, Tahoma, sans-serif;}
.block-container {direction: rtl;}
.stButton>button {background-color: #388e3c; color:white; border-radius:8px;}
</style>
""", unsafe_allow_html=True)

# ---------- DB ----------
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
    Column('date', String), Column('height', Integer), Column('leaves', Integer),
    Column('notes', String), Column('prune_needed', Integer)
)
meta.create_all(engine)

# ---------- Session ----------
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None

# ---------- Password helpers ----------
def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Authentication ----------
if st.session_state.user_id is None:
    st.sidebar.subheader("ورود / ثبت‌نام")
    mode = st.sidebar.radio("حالت:", ["ورود","ثبت‌نام","ورود مهمان"])
    if mode=="ثبت‌نام":
        u = st.sidebar.text_input("نام کاربری", key="signup_u")
        p = st.sidebar.text_input("رمز عبور", type="password", key="signup_p")
        if st.sidebar.button("ثبت‌نام"):
            if not u or not p: st.sidebar.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    if conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first():
                        st.sidebar.error("نام کاربری قبلاً ثبت شده.")
                    else:
                        conn.execute(users_table.insert().values(username=u,password_hash=hash_password(p)))
                        st.sidebar.success("ثبت‌نام انجام شد.")
    elif mode=="ورود":
        u = st.sidebar.text_input("نام کاربری", key="login_u")
        p = st.sidebar.text_input("رمز عبور", type="password", key="login_p")
        if st.sidebar.button("ورود"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first()
                if r and check_password(p,r['password_hash']):
                    st.session_state.user_id = int(r['id'])
                    st.session_state.username = r['username']
                    st.experimental_rerun()
                else: st.sidebar.error("نام کاربری یا رمز اشتباه است.")
    else:
        st.session_state.user_id = 0
        st.session_state.username = "مهمان"
        st.experimental_rerun()
    st.stop()

# ---------- Sidebar Menu ----------
st.sidebar.subheader(f"خوش آمدید {st.session_state.username}")
menu = ["🏠 خانه","🌱 پایش نهال","📈 پیش‌بینی هرس","📥 دانلود داده‌ها","🚪 خروج"]
choice = st.sidebar.radio("منو", menu)

# ---------- Dashboard ----------
if choice=="🏠 خانه":
    st.header("🏠 خانه")
    with engine.connect() as conn:
        last = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id).order_by(measurements.c.id.desc()).limit(1)).mappings().first()
        st.write("آخرین اندازه‌گیری:", last['height'] if last else "—")

elif choice=="🌱 پایش نهال":
    st.header("ثبت اندازه‌گیری نهال")
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

elif choice=="📈 پیش‌بینی هرس":
    st.header("آپلود تصویر نهال")
    uploaded = st.file_uploader("انتخاب تصویر", type=["jpg","jpeg","png"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        # ساده: میانگین روشنایی و درصد سبز
        stat = ImageStat.Stat(img)
        r,g,b = stat.mean[:3]
        green_ratio = g/(r+g+b)
        if green_ratio<0.35 or stat.mean[1]<80:
            st.warning("⚠️ به نظر می‌رسد نیاز به هرس دارد")
        else:
            st.success("✅ نیاز به هرس نیست")

elif choice=="📥 دانلود داده‌ها":
    st.header("دانلود داده‌ها")
    with engine.connect() as conn:
        ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id)).mappings().all()
        if ms:
            df = pd.DataFrame(ms)
            st.download_button("دانلود اندازه‌گیری‌ها", df.to_csv(index=False).encode(), "measurements.csv")
        else: st.info("هیچ داده‌ای برای دانلود وجود ندارد.")

elif choice=="🚪 خروج":
    st.session_state.user_id = None
    st.session_state.username = None
    st.experimental_rerun()
