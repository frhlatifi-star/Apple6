import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
import altair as alt

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Custom CSS for UI ----------
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
if 'lang_rerun_done' not in st.session_state: st.session_state['lang_rerun_done'] = False

# ---------- Language ----------
def t(fa, en):
    return en if st.session_state['lang'] == 'English' else fa

# Sidebar language selection
with st.sidebar:
    lang_selection = st.selectbox("Language / زبان", ["فارسی", "English"],
                                  index=0 if st.session_state['lang'] == 'فارسی' else 1)

# Apply language change only if different and rerun not done yet
if lang_selection != st.session_state['lang'] and not st.session_state['lang_rerun_done']:
    st.session_state['lang'] = lang_selection
    st.session_state['lang_rerun_done'] = True
    st.experimental_rerun()
else:
    st.session_state['lang_rerun_done'] = False

text_class = 'rtl' if st.session_state['lang'] == 'فارسی' else 'ltr'

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Auth ----------
if st.session_state['user_id'] is None:
    st.sidebar.header(t("احراز هویت", "Authentication"))
    mode = st.sidebar.radio(t("حالت", "Mode"), [t("ورود", "Login"), t("ثبت‌نام", "Sign Up"), t("دمو", "Demo")])

    if mode == t("ثبت‌نام", "Sign Up"):
        st.header(t("ثبت‌نام", "Sign Up"))
        username = st.text_input(t("نام کاربری", "Username"))
        password = st.text_input(t("رمز عبور", "Password"), type="password")
        if st.button(t("ثبت", "Register")):
            if not username or not password:
                st.error(t("نام کاربری و رمز عبور را وارد کنید.", "Provide username & password."))
            else:
                sel = sa.select(users_table).where(users_table.c.username==username)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error(t("نام کاربری وجود دارد.", "Username already exists."))
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success(t("ثبت شد. لطفا وارد شوید.", "Registered. Please login."))

    elif mode == t("ورود", "Login"):
        st.header(t("ورود", "Login"))
        username = st.text_input(t("نام کاربری", "Username"))
        password = st.text_input(t("رمز عبور", "Password"), type="password")
        if st.button(t("ورود", "Login")):
            sel = sa.select(users_table).where(users_table.c.username==username)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error(t("نام کاربری یافت نشد.", "Username not found."))
            elif check_password(password, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.experimental_rerun()
            else:
                st.error(t("رمز عبور اشتباه است.", "Wrong password."))

    else:
        st.header(t("حالت دمو", "Demo Mode"))
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
