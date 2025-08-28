import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Custom CSS ----------
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e0f7fa, #ffffff);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.rtl {
    direction: rtl;
    text-align: right;
}
.section-card {
    background-color: #ffffff;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
h1, h2, h3 {
    color: #00796b;
}
.logo {
    width: 120px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

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
for key, default in [('user_id', None), ('username', None), ('demo_data', [])]:
    if key not in st.session_state:
        st.session_state[key] = default

text_class = 'rtl'

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Auth ----------
st.markdown(f"<div class='{text_class}'><img src='logo.png' class='logo'><h1>سیستم مدیریت نهال سیب</h1></div>", unsafe_allow_html=True)
st.sidebar.header("احراز هویت")
mode = st.sidebar.radio("حالت", ["ورود", "ثبت‌نام", "دمو"])

if mode == "ثبت‌نام":
    st.subheader("ثبت‌نام")
    username_input = st.text_input("نام کاربری", key="signup_username")
    password_input = st.text_input("رمز عبور", type="password", key="signup_password")
    if st.button("ثبت"):
        if not username_input or not password_input:
            st.error("نام کاربری و رمز عبور را وارد کنید.")
        else:
            sel = sa.select(users_table).where(users_table.c.username==username_input)
            r = conn.execute(sel).mappings().first()
            if r:
                st.error("نام کاربری وجود دارد.")
            else:
                hashed = hash_password(password_input)
                conn.execute(users_table.insert().values(username=username_input, password_hash=hashed))
                st.success("ثبت شد. لطفا وارد شوید.")

elif mode == "ورود":
    st.subheader("ورود")
    username_input = st.text_input("نام کاربری", key="login_username")
    password_input = st.text_input("رمز عبور", type="password", key="login_password")
    if st.button("ورود"):
        sel = sa.select(users_table).where(users_table.c.username==username_input)
        r = conn.execute(sel).mappings().first()
        if not r:
            st.error("نام کاربری یافت نشد.")
        elif check_password(password_input, r['password_hash']):
            st.session_state['user_id'] = r['id']
            st.session_state['username'] = r['username']
            st.experimental_rerun()
        else:
            st.error("رمز عبور اشتباه است.")

else:
    st.subheader("حالت دمو")
    st.info("در حالت دمو داده ذخیره نمی‌شود.")
    f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
    if f:
        st.image(f, use_container_width=True)
        st.success("پیش‌بینی دمو: سالم")
        st.write("یادداشت: این نتیجه آزمایشی است.")
        st.session_state['demo_data'].append({'file': f.name, 'result': 'Healthy', 'time': datetime.now()})
        if st.session_state['demo_data']:
            st.subheader("تاریخچه دمو")
            df_demo = pd.DataFrame(st.session_state['demo_data'])
            st.dataframe(df_demo)
