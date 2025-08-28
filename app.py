import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta

# ----------- تنظیم دیتابیس ----------------
DB_FILE = "app_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # جدول کاربران
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    # جدول زمانبندی
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
    # جدول پیش‌بینی نیاز آب و کود
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

# ----------- تنظیم راست‌چین و فونت فارسی ----------------
st.set_page_config(page_title="سیبتک – کشاورزی هوشمند", layout="wide")
st.markdown("""
    <style>
    body {direction: rtl; font-family: Vazir, Arial; }
    .stButton>button {width: 100%;}
    </style>
""", unsafe_allow_html=True)

# ----------- مدیریت سشن استیت ----------------
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# ----------- صفحه ورود و ثبت‌نام ----------------
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
            st.error("نام کاربری یا رمز عبور اشتباه است.")

def signup_page():
    st.subheader("ثبت نام کاربر جدید")
    username = st.text_input("نام کاربری جدید")
    password = st.text_input("رمز عبور جدید", type="password")
    if st.button("ثبت نام"):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            st.success("ثبت نام موفق! حالا می‌توانید وارد شوید.")
        except sqlite3.IntegrityError:
            st.error("این نام کاربری قبلاً ثبت شده است.")

# ----------- صفحه اصلی ----------------
def page_home():
    st.title("سیبتک – داشبورد مدیریت نهال")
    st.image("logo.png", width=200)
    
    user_id = st.session_state['user_id']
    if not user_id:
        st.warning("لطفاً ابتدا وارد شوید.")
        return

    st.subheader("پیش‌بینی نیاز آب و کود")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today = datetime.today().strftime("%Y-%m-%d")
    
    # بررسی پیش‌بینی امروز، اگر نیست ایجاد می‌کنیم
    cursor.execute("SELECT * FROM predictions WHERE user_id=? AND prediction_date=?", (user_id, today))
    prediction = cursor.fetchone()
    if not prediction:
        water_needed = 50  # می‌توان با الگوریتم واقعی جایگزین شود
        fertilize_needed = 20
        cursor.execute("INSERT INTO predictions (user_id, prediction_date, water_needed, fertilize_needed) VALUES (?, ?, ?, ?)",
                       (user_id, today, water_needed, fertilize_needed))
        conn.commit()
        prediction = (None, user_id, today, water_needed, fertilize_needed)
    conn.close()
    
    st.write(f"تاریخ: {prediction[2]}")
    st.write(f"میزان آب مورد نیاز: {prediction[3]} لیتر")
    st.write(f"میزان کود مورد نیاز: {prediction[4]} واحد")

# ----------- صفحه زمانبندی ----------------
def page_schedule():
    st.subheader("زمانبندی فعالیت‌ها")
    user_id = st.session_state['user_id']
    if not user_id:
        st.warning("لطفاً ابتدا وارد شوید.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # اضافه کردن تسک جدید
    with st.form("add_task_form"):
        task = st.text_input("فعالیت")
        date = st.date_input("تاریخ")
        notes = st.text_area("یادداشت")
        submitted = st.form_submit_button("افزودن")
        if submitted and task:
            cursor.execute("INSERT INTO schedule (user_id, task, date, notes) VALUES (?, ?, ?, ?)",
                           (user_id, task, date.strftime("%Y-%m-%d"), notes))
            conn.commit()
            st.success("فعالیت اضافه شد!")

    # نمایش تسک‌ها
    cursor.execute("SELECT id, task, date, notes FROM schedule WHERE user_id=? ORDER BY date DESC", (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    
    if tasks:
        for t in tasks:
            st.markdown(f"**{t[1]}** – {t[2]} – {t[3]}")
    else:
        st.info("هیچ فعالیتی ثبت نشده است.")

# ----------- منو ----------------
menu = ["ورود / ثبت‌نام", "داشبورد", "زمانبندی"]
menu_choice = st.sidebar.selectbox("منو", menu)

if menu_choice == "ورود / ثبت‌نام":
    tab = st.tabs(["ورود", "ثبت‌نام"])
    with tab[0]:
        login_page()
    with tab[1]:
        signup_page()
elif menu_choice == "داشبورد":
    page_home()
elif menu_choice == "زمانبندی":
    page_schedule()
