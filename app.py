import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 پایش نهال", page_icon="🍎", layout="wide")

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))

measurements = Table('measurements', meta,
                     Column('id', Integer, primary_key=True),
                     Column('user_id', Integer, ForeignKey('users.id')),
                     Column('date', String),
                     Column('height', Integer),
                     Column('leaves', Integer),
                     Column('notes', String),
                     Column('prune_needed', Integer))

meta.create_all(engine)
conn = engine.connect()

# ---------- Session ----------
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Login / SignUp ----------
if st.session_state['user_id'] is None:
    # نمایش لوگو و عنوان
    st.markdown("""
        <div style='display:flex; align-items:center;'>
            <img src='https://i.imgur.com/4Y2E2XQ.png' width='60' style='margin-right:15px;'/>
            <h2>سیبتک 🍎 پایش نهال</h2>
        </div>
    """, unsafe_allow_html=True)

    mode = st.radio("حالت:", ["ورود", "ثبت‌نام", "دمو"])

    if mode == "ثبت‌نام":
        st.subheader("ثبت‌نام")
        username = st.text_input("نام کاربری", key="signup_user")
        password = st.text_input("رمز عبور", type="password", key="signup_pass")
        if st.button("ثبت"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                sel = sa.select(users_table).where(users_table.c.username == username)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error("نام کاربری موجود است.")
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success("ثبت‌نام انجام شد. لطفاً وارد شوید.")

    elif mode == "ورود":
        st.subheader("ورود")
        username = st.text_input("نام کاربری", key="login_user")
        password = st.text_input("رمز عبور", type="password", key="login_pass")
        if st.button("ورود"):
            sel = sa.select(users_table).where(users_table.c.username == username)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error("نام کاربری یافت نشد.")
            elif check_password(password, r['password_hash']):
                # بروزرسانی session_state بدون استفاده از experimental_rerun
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.success(f"خوش آمدید، {r['username']}!")
            else:
                st.error("رمز عبور اشتباه است.")

    else:  # Demo
        st.subheader("دمو")
        st.info("در حالت دمو داده ذخیره نمی‌شود.")
        f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success("پیش‌بینی دمو: سالم")
            st.write("یادداشت: این نتیجه آزمایشی است.")
else:
    # ---------- Logged-in Menu ----------
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", ["🏠 خانه", "🌱 پایش", "📅 زمان‌بندی", "📈 پیش‌بینی", "🍎 بیماری", "📥 دانلود", "🚪 خروج"])
    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun = None  # حذف experimental_rerun
        st.info("شما از سیستم خارج شدید.")
