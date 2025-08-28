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
.ltr {
    direction: ltr;
    text-align: left;
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
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'username' not in st.session_state: st.session_state['username'] = None
if 'lang' not in st.session_state: st.session_state['lang'] = 'فارسی'
if 'demo_data' not in st.session_state: st.session_state['demo_data'] = []

# ---------- Language ----------
def t(fa, en):
    return en if st.session_state['lang'] == 'English' else fa

# Sidebar language selection
with st.sidebar:
    lang_selection = st.selectbox("Language / زبان", ["فارسی", "English"],
                                  index=0 if st.session_state['lang'] == 'فارسی' else 1)

if lang_selection != st.session_state['lang']:
    st.session_state['lang'] = lang_selection
    st.experimental_rerun()

text_class = 'rtl' if st.session_state['lang'] == 'فارسی' else 'ltr'

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Auth ----------
if st.session_state['user_id'] is None:
    st.markdown(f"<div class='{text_class}'><img src='logo.png' class='logo'><h1>{t('سیستم مدیریت نهال سیب', 'Seedling Pro')}</h1></div>", unsafe_allow_html=True)
    st.sidebar.header(t("احراز هویت", "Authentication"))
    mode = st.sidebar.radio(t("حالت", "Mode"), [t("ورود", "Login"), t("ثبت‌نام", "Sign Up"), t("دمو", "Demo")])

    if mode == t("ثبت‌نام", "Sign Up"):
        st.subheader(t("ثبت‌نام", "Sign Up"))
        username_input = st.text_input(t("نام کاربری", "Username"), key="signup_username")
        password_input = st.text_input(t("رمز عبور", "Password"), type="password", key="signup_password")
        if st.button(t("ثبت", "Register")):
            if not username_input or not password_input:
                st.error(t("نام کاربری و رمز عبور را وارد کنید.", "Provide username & password."))
            else:
                sel = sa.select(users_table).where(users_table.c.username==username_input)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error(t("نام کاربری وجود دارد.", "Username already exists."))
                else:
                    hashed = hash_password(password_input)
                    conn.execute(users_table.insert().values(username=username_input, password_hash=hashed))
                    st.success(t("ثبت شد. لطفا وارد شوید.", "Registered. Please login."))

    elif mode == t("ورود", "Login"):
        st.subheader(t("ورود", "Login"))
        username_input = st.text_input(t("نام کاربری", "Username"), key="login_username")
        password_input = st.text_input(t("رمز عبور", "Password"), type="password", key="login_password")
        if st.button(t("ورود", "Login")):
            sel = sa.select(users_table).where(users_table.c.username == username_input)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error(t("نام کاربری یافت نشد.", "Username not found."))
            elif check_password(password_input, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.experimental_rerun()
            else:
                st.error(t("رمز عبور اشتباه است.", "Wrong password."))

    else:
        st.subheader(t("حالت دمو", "Demo Mode"))
        st.info(t("در حالت دمو داده ذخیره نمی‌شود.", "In demo mode, data is not saved."))
        f = st.file_uploader(t("آپلود تصویر برگ/میوه/ساقه", "Upload leaf/fruit/stem image"), type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success(t("پیش‌بینی دمو: سالم", "Demo prediction: Healthy"))
            st.write(t("یادداشت: این نتیجه آزمایشی است.", "Notes: This is a demo result."))
            st.session_state['demo_data'].append({'file': f.name, 'result': 'Healthy', 'time': datetime.now()})
            if st.session_state['demo_data']:
                st.subheader(t("تاریخچه دمو", "Demo History"))
                df_demo = pd.DataFrame(st.session_state['demo_data'])
                st.dataframe(df_demo)
