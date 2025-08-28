import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# تنظیم فونت و راست‌چین
st.set_page_config(page_title="سیبتک – کشاورزی هوشمند", layout="wide")
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
    html, body, [class*="css"]  {
        font-family: 'Vazir', sans-serif;
        direction: rtl;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

# ایجاد دیتابیس و جدول‌ها
conn = sqlite3.connect("apple_dashboard.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    task TEXT,
    date TEXT,
    notes TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    prediction_date TEXT,
    prediction TEXT
)
""")
conn.commit()

# مدیریت جلسه کاربر
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ------------------ صفحه ورود ------------------
def login_page():
    st.title("ورود به سیستم")
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    if st.button("ورود"):
        cursor.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            st.session_state.user_id = user[0]
            st.success("ورود موفق!")
        else:
            st.error("نام کاربری یا رمز عبور اشتباه است.")

# ------------------ صفحه ثبت‌نام ------------------
def signup_page():
    st.title("ثبت‌نام در سیستم")
    new_username = st.text_input("نام کاربری جدید", key="signup_username")
    new_password = st.text_input("رمز عبور جدید", type="password", key="signup_password")
    if st.button("ثبت‌نام"):
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, new_password))
            conn.commit()
            st.success("ثبت‌نام با موفقیت انجام شد! حالا می‌توانید وارد شوید.")
        except sqlite3.IntegrityError:
            st.error("این نام کاربری قبلا ثبت شده است.")

# ------------------ داشبورد ------------------
def dashboard_page():
    st.title("داشبورد مدیریت نهال")
    menu = ["رصد رشد نهال", "زمان‌بندی فعالیت‌ها", "پیش‌بینی", "دانلود داده‌ها", "خروج"]
    choice = st.sidebar.selectbox("منوی اصلی", menu)

    if choice == "رصد رشد نهال":
        st.subheader("رصد رشد نهال")
        st.write("اینجا می‌توانید اطلاعات مربوط به رشد نهال را مشاهده کنید.")
    elif choice == "زمان‌بندی فعالیت‌ها":
        st.subheader("زمان‌بندی فعالیت‌ها")
        df_schedule = pd.DataFrame(cursor.execute("SELECT task, date, notes FROM schedule WHERE user_id=?", (st.session_state.user_id,)).fetchall(), columns=["کار", "تاریخ", "یادداشت"])
        st.table(df_schedule)
    elif choice == "پیش‌بینی":
        st.subheader("پیش‌بینی وضعیت نهال")
        df_pred = pd.DataFrame(cursor.execute("SELECT prediction_date, prediction FROM predictions WHERE user_id=?", (st.session_state.user_id,)).fetchall(), columns=["تاریخ پیش‌بینی", "پیش‌بینی"])
        st.table(df_pred)
    elif choice == "دانلود داده‌ها":
        st.subheader("دانلود داده‌ها")
        df_sch = pd.DataFrame(cursor.execute("SELECT * FROM schedule WHERE user_id=?", (st.session_state.user_id,)).fetchall())
        df_pred = pd.DataFrame(cursor.execute("SELECT * FROM predictions WHERE user_id=?", (st.session_state.user_id,)).fetchall())
        st.download_button("دانلود زمان‌بندی", df_sch.to_csv(index=False), "schedule.csv")
        st.download_button("دانلود پیش‌بینی", df_pred.to_csv(index=False), "predictions.csv")
    elif choice == "خروج":
        st.session_state.user_id = None
        st.success("خروج موفق!")

# ------------------ جریان اصلی ------------------
if st.session_state.user_id:
    dashboard_page()
else:
    st.sidebar.success("لطفا وارد شوید یا ثبت‌نام کنید")
    tab = st.tabs(["ورود", "ثبت‌نام"])
    with tab[0]:
        login_page()
    with tab[1]:
        signup_page()
