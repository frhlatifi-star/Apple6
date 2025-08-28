import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from PIL import Image

# ---------- فونت و راست‌چین ----------
st.set_page_config(page_title="سیبتک – کشاورزی هوشمند", layout="wide")

st.markdown("""
<style>
body { direction: rtl; font-family: Vazir, Tahoma, sans-serif; }
h1, h2, h3, h4, h5, h6 { text-align: right; }
</style>
""", unsafe_allow_html=True)

# ---------- اتصال به دیتابیس ----------
conn = sqlite3.connect('users_data.db', check_same_thread=False)
cursor = conn.cursor()

# ایجاد جداول در صورت نبودن
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task TEXT,
    date TEXT,
    notes TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    prediction_date TEXT,
    result TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
''')

conn.commit()

# ---------- لوگو ----------
st.sidebar.image("logo.png", use_column_width=True)  # لوگوی حرفه‌ای خودت را قرار بده

# ---------- منوی اصلی ----------
menu_options = ["ورود", "ثبت‌نام"]
if 'logged_in' in st.session_state and st.session_state.logged_in:
    menu_options += ["پیش‌بینی", "زمان‌بندی", "خروج"]

menu_choice = st.sidebar.radio("منوی اصلی", menu_options)

# ---------- تابع ورود ----------
def login_page():
    st.header("ورود به اپلیکیشن")
    username = st.text_input("نام کاربری", key="login_user")
    password = st.text_input("رمز عبور", type="password", key="login_pass")
    if st.button("ورود", key="login_btn"):
        cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            st.success("ورود موفق!")
            st.session_state.logged_in = True
            st.session_state.user_id = user[0]
            st.experimental_rerun()
        else:
            st.error("نام کاربری یا رمز عبور اشتباه است!")

# ---------- تابع ثبت‌نام ----------
def signup_page():
    st.header("ثبت‌نام در اپلیکیشن")
    new_username = st.text_input("نام کاربری", key="signup_user")
    new_password = st.text_input("رمز عبور", type="password", key="signup_pass")
    if st.button("ثبت‌نام", key="signup_btn"):
        if new_username and new_password:
            try:
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, new_password))
                conn.commit()
                st.success("ثبت‌نام با موفقیت انجام شد! اکنون وارد شوید.")
            except sqlite3.IntegrityError:
                st.error("این نام کاربری قبلا ثبت شده است.")
        else:
            st.warning("لطفا همه فیلدها را پر کنید.")

# ---------- تابع پیش‌بینی ----------
def page_prediction():
    st.header("صفحه پیش‌بینی")
    user_id = st.session_state.user_id
    cursor.execute("SELECT * FROM predictions WHERE user_id=?", (user_id,))
    df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])
    st.dataframe(df)

# ---------- تابع زمان‌بندی ----------
def page_schedule():
    st.header("صفحه زمان‌بندی")
    user_id = st.session_state.user_id
    cursor.execute("SELECT * FROM schedule WHERE user_id=? ORDER BY date DESC", (user_id,))
    df = pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])
    st.dataframe(df)

# ---------- خروج ----------
def logout():
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.success("با موفقیت خارج شدید.")
    st.experimental_rerun()

# ---------- مدیریت صفحات ----------
if menu_choice == "ورود":
    login_page()
elif menu_choice == "ثبت‌نام":
    signup_page()
elif menu_choice == "پیش‌بینی":
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        page_prediction()
elif menu_choice == "زمان‌بندی":
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        page_schedule()
elif menu_choice == "خروج":
    logout()
