import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# ==========================
# فایل دیتابیس
DB_FILE = "app_data.db"

# پاک کردن دیتابیس قبلی (برای تست)
# if os.path.exists(DB_FILE):
#     os.remove(DB_FILE)

# ==========================
# ساخت دیتابیس و جدول‌ها
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task TEXT,
            date TEXT,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            prediction_date TEXT,
            water_needed INTEGER,
            fertilize_needed INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==========================
# استایل راست‌چین و فونت فارسی
st.set_page_config(page_title="سیبتک – کشاورزی هوشمند", layout="wide")
st.markdown("""
<style>
body { direction: rtl; font-family: Vazir, sans-serif; }
h1, h2, h3, h4, h5, h6 { font-family: Vazir, sans-serif; }
</style>
""", unsafe_allow_html=True)

# ==========================
# لوگوی اپ
st.image("logo.png", width=150)  # لوگوی سیب خود را اینجا بگذارید

# ==========================
# توابع ورود و ثبت‌نام
def signup_page():
    st.subheader("ثبت‌نام کاربر جدید")
    new_username = st.text_input("نام کاربری")
    new_password = st.text_input("رمز عبور", type="password")
    if st.button("ثبت‌نام"):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, new_password))
            conn.commit()
            st.success("ثبت‌نام با موفقیت انجام شد!")
        except sqlite3.IntegrityError:
            st.error("این نام کاربری قبلاً ثبت شده است!")
        conn.close()

def login_page():
    st.subheader("ورود کاربر")
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    if st.button("ورود"):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            st.session_state['user_id'] = user[0]
            st.success("ورود موفق!")
        else:
            st.error("نام کاربری یا رمز عبور اشتباه است!")

# ==========================
# بخش زمان‌بندی
def page_schedule():
    st.subheader("برنامه‌های زمان‌بندی شده")
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.warning("لطفاً ابتدا وارد شوید.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # نمایش برنامه‌ها
    df = pd.read_sql_query("SELECT * FROM schedule WHERE user_id=? ORDER BY date DESC", conn, params=(user_id,))
    st.dataframe(df)

    # افزودن برنامه جدید
    with st.form("new_task_form"):
        task = st.text_input("کار جدید")
        date = st.date_input("تاریخ")
        notes = st.text_area("توضیحات")
        submitted = st.form_submit_button("افزودن")
        if submitted:
            cursor.execute("INSERT INTO schedule (user_id, task, date, notes) VALUES (?, ?, ?, ?)",
                           (user_id, task, str(date), notes))
            conn.commit()
            st.success("برنامه جدید اضافه شد!")

    conn.close()

# ==========================
# بخش پیش‌بینی
def page_prediction():
    st.subheader("پیش‌بینی نیاز آب و کود")
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.warning("لطفاً ابتدا وارد شوید.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    today = datetime.today().date()
    # یک پیش‌بینی نمونه
    cursor.execute("INSERT INTO predictions (user_id, prediction_date, water_needed, fertilize_needed) VALUES (?, ?, ?, ?)",
                   (user_id, str(today), 10, 5))
    conn.commit()

    df = pd.read_sql_query("SELECT * FROM predictions WHERE user_id=? ORDER BY prediction_date DESC", conn, params=(user_id,))
    st.dataframe(df)

    conn.close()

# ==========================
# منو ثابت (نه اسلایدبار)
menu_options = ["خانه", "ورود / ثبت‌نام", "زمان‌بندی", "پیش‌بینی"]
menu_choice = st.radio("منوی اصلی", menu_options, horizontal=True)

if menu_choice == "ورود / ثبت‌نام":
    tab = st.tabs(["ورود", "ثبت‌نام"])
    with tab[0]:
        login_page()
    with tab[1]:
        signup_page()
elif menu_choice == "زمان‌بندی":
    page_schedule()
elif menu_choice == "پیش‌بینی":
    page_prediction()
else:
    st.subheader("خانه")
    st.write("به اپلیکیشن سیبتک خوش آمدید!")
