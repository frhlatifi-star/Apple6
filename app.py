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

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
/* راست چین و فونت فارسی */
html, body, [class*="css"] {direction: rtl !important; text-align: right !important; font-family: 'Vazirmatn', Tahoma, sans-serif; background-color: #e6f2e6;}
/* دکمه‌ها */
.stButton>button {cursor: pointer; background-color: #4CAF50; color: white; border-radius: 8px; padding: 8px 16px; font-weight: bold;}
.stButton>button:hover {background-color: #45a049;}
/* کارت‌ها */
.card {background-color: #ffffff; border-radius: 12px; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 15px;}
.card h3 {margin: 0;}
.card .metric {font-size: 24px; font-weight: bold;}
/* تکست‌باکس‌ها سفید */
div.stTextInput > div > input {background-color: white !important; color: black !important;}
textarea {background-color: white !important; color: black !important;}
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

meta.create_all(engine)

# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Session defaults ----------
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# ---------- UI Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
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
    st.subheader("ورود / ثبت‌نام")
    col1, col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2:
        st.write("")

    if mode == "ثبت‌نام":
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
    elif mode == "ورود":
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            try:
                with engine.connect() as conn:
                    r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                    if not r:
                        st.error("نام کاربری یافت نشد.")
                    elif check_password(password,r['password_hash']):
                        st.session_state['user_id'] = int(r['id'])
                        st.session_state['username'] = r['username']
                        st.experimental_rerun()
                    else:
                        st.error("رمز عبور اشتباه است.")
            except Exception as e:
                st.error(f"خطا در ورود: {e}")
    else:
        st.info("حالت دمو: پیش‌بینی نمونه بدون ثبت نام")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img, use_container_width=True)
            st.info("در این نسخه دمو، تحلیل تصویر انجام نمی‌شود.")

# ---------- Main Menu ----------
if st.session_state['user_id'] is not None:
    st.subheader(f"خوش آمدید، {st.session_state['username']}")
    menu = st.radio("منو:", ["🏠 خانه","🌱 پایش نهال","🚪 خروج"], index=0, horizontal=True)

    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    elif menu == "🏠 خانه":
        st.header("خانه")
        with engine.connect() as conn:
            m_sel = sa.select(measurements).where(measurements.c.user_id==user_id)
            ms = conn.execute(m_sel).mappings().all()
        st.markdown(f"<div class='card'><h3>تعداد اندازه‌گیری‌ها: {len(ms)}</h3></div>", unsafe_allow_html=True)

    elif menu == "🌱 پایش نهال":
        st.header("پایش نهال — ثبت رشد")
        with st.form("add_measure"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع (cm)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            prune = st.checkbox("نیاز به هرس؟")
            notes = st.text_area("یادداشت")
            submitted = st.form_submit_button("ثبت اندازه‌گیری")
            if submitted:
                try:
                    with engine.connect() as conn:
                        conn.execute(measurements.insert().values(
                            user_id=user_id,
                            date=str(date),
                            height=int(height),
                            leaves=int(leaves),
                            prune_needed=int(prune),
                            notes=notes
                        ))
                    st.success("اندازه‌گیری ثبت شد.")
                except Exception as e:
                    st.error(f"خطا در ثبت: {e}")
        st.subheader("تاریخچه اندازه‌گیری‌ها")
        try:
            with engine.connect() as conn:
                sel = sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())
                rows = conn.execute(sel).mappings().all()
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"خطا در بارگذاری: {e}")
