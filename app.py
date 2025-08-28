# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat
import os
import base64

# ---------- Page config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
:root { --accent: #2e7d32; --accent-2: #388e3c; --bg-1: #eaf9e7; --card: #ffffff; }
body, html, [class*="css"] { direction: rtl !important; text-align: right !important; font-family: Vazirmatn, Tahoma, sans-serif; background: linear-gradient(135deg,#eaf9e7,#f7fff8) !important; }
.stTextInput>div>input { background-color: white !important; }
.stButton>button { background-color: var(--accent-2) !important; color: white !important; border-radius: 8px !important; padding: 6px 12px; }
.card { background: var(--card); padding: 1rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

# ---------- Database setup ----------
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

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Session defaults ----------
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None
if 'page' not in st.session_state: st.session_state.page = "home"

# ---------- Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;margin-left:12px;'>"
    else:
        img_html = "<div style='font-size:36px;margin-left:12px;'>🍎</div>"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:10px;'>
        {img_html}
        <div>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#555'>مدیریت و پایش نهال</small>
        </div>
    </div>
    <hr/>
    """, unsafe_allow_html=True)

app_header()

# ---------- Authentication ----------
def auth_ui():
    st.subheader("ورود یا ثبت‌نام")
    col1,col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","ورود مهمان"])
    with col2:
        st.write("")  # spacer

    if mode=="ثبت‌نام":
        username = st.text_input("نام کاربری", key="signup_u")
        password = st.text_input("رمز عبور", type="password", key="signup_p")
        if st.button("ثبت‌نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    sel = sa.select(users_table).where(users_table.c.username==username)
                    if conn.execute(sel).mappings().first():
                        st.error("این نام کاربری قبلاً ثبت شده است.")
                    else:
                        conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                        st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
    elif mode=="ورود":
        username = st.text_input("نام کاربری", key="login_u")
        password = st.text_input("رمز عبور", type="password", key="login_p")
        if st.button("ورود"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                if not r: st.error("نام کاربری یافت نشد.")
                elif check_password(password,r['password_hash']):
                    st.session_state.user_id = int(r['id'])
                    st.session_state.username = r['username']
                    st.experimental_rerun()
                else: st.error("رمز عبور اشتباه است.")
    else:
        st.session_state.user_id = 0
        st.session_state.username = "مهمان"
        st.experimental_rerun()

if st.session_state.user_id is None:
    auth_ui()
    st.stop()

# ---------- Dashboard Menu ----------
def menu_ui():
    st.markdown(f"<h4>خوش آمدید، {st.session_state.username}</h4>", unsafe_allow_html=True)
    menu_items = [
        ("🏠 خانه", "home"),
        ("🌱 پایش نهال", "tracking"),
        ("📅 زمان‌بندی", "schedule"),
        ("📈 پیش‌بینی سلامت نهال", "predict"),
        ("🍎 ثبت بیماری / یادداشت", "disease"),
        ("📥 دانلود داده‌ها", "download"),
        ("🚪 خروج", "logout")
    ]
    cols = st.columns(len(menu_items))
    for idx, (label, key) in enumerate(menu_items):
        with cols[idx]:
            if st.button(label):
                st.session_state.page = key
                st.experimental_rerun()

menu_ui()

# ---------- Router ----------
def router():
    page = st.session_state.page
    user_id = st.session_state.user_id

    if page=="home":
        st.header("خانه")
        st.write("خلاصه وضعیت و تعداد داده‌های ثبت شده را مشاهده کنید.")
    elif page=="tracking":
        st.header("پایش نهال")
        st.write("ثبت اندازه‌گیری و مشاهده نمودارها.")
    elif page=="schedule":
        st.header("زمان‌بندی فعالیت‌ها")
        st.write("ثبت و مشاهده برنامه‌های کاری.")
    elif page=="predict":
        st.header("پیش‌بینی سلامت نهال")
        st.write("بارگذاری تصویر و دریافت پیش‌بینی سلامت یا نیاز به هرس.")
    elif page=="disease":
        st.header("ثبت بیماری / یادداشت")
    elif page=="download":
        st.header("دانلود داده‌ها")
    elif page=="logout":
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.page = "home"
        st.experimental_rerun()
    else:
        st.info("صفحه نامشخص — بازگشت به خانه")
        st.session_state.page = "home"

router()
