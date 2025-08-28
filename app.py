# app.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from PIL import Image
import os

# =====================
# تنظیمات صفحه
# =====================
st.set_page_config(page_title="سیبتک – کشاورزی هوشمند", layout="wide")
st.markdown("""
<style>
body { direction: rtl; font-family: Vazir, Tahoma; }
</style>
""", unsafe_allow_html=True)

# =====================
# لوگو و هدر
# =====================
logo_path = "logo.png"  # فایل لوگو را کنار این اسکریپت قرار بده
if os.path.exists(logo_path):
    st.image(logo_path, width=120)
st.title("سیبتک – مدیریت و پایش نهال سیب")

# =====================
# پایگاه داده
# =====================
DB_FILE = "app_data.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

def init_db():
    conn = get_connection()
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
    # جدول پیش بینی آبیاری / حرص
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

# =====================
# ورود و ثبت نام
# =====================
def login_page():
    st.subheader("ورود کاربر")
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    if st.button("ورود"):
        conn = get_connection()
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
    new_username = st.text_input("نام کاربری جدید", key="signup_user")
    new_password = st.text_input("رمز عبور جدید", type="password", key="signup_pass")
    if st.button("ثبت نام"):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?,?)", (new_username, new_password))
            conn.commit()
            st.success("ثبت نام موفق! اکنون وارد شوید.")
        except sqlite3.IntegrityError:
            st.error("این نام کاربری قبلا ثبت شده است.")
        conn.close()

# =====================
# منو اصلی
# =====================
if 'user_id' not in st.session_state:
    menu_choice = st.radio("انتخاب:", ["ورود", "ثبت نام"])
    if menu_choice == "ورود":
        login_page()
    elif menu_choice == "ثبت نام":
        signup_page()
else:
    user_id = st.session_state['user_id']
    st.write(f"👤 کاربر فعلی: {user_id}")
    menu_choice = st.radio("منو:", ["خانه", "پایش رشد", "زمانبندی", "دانلود داده‌ها", "خروج"])

    conn = get_connection()
    
    if menu_choice == "خانه":
        st.header("خانه")
        st.write("📊 خلاصه وضعیت نهال‌ها")
        # نمایش آخرین پیش‌بینی‌ها
        df_pred = pd.read_sql(f"SELECT * FROM predictions WHERE user_id={user_id} ORDER BY prediction_date DESC", conn)
        if not df_pred.empty:
            st.dataframe(df_pred)
        else:
            st.info("هیچ پیش‌بینی‌ای موجود نیست.")

    elif menu_choice == "پایش رشد":
        st.header("پایش رشد نهال")
        st.write("📈 نمودار رشد و وضعیت نهال‌ها اینجا نمایش داده می‌شود.")
        # نمونه داده
        df = pd.DataFrame({
            "تاریخ": pd.date_range(start="2025-01-01", periods=10, freq='D'),
            "ارتفاع": [10, 12, 15, 17, 19, 20, 21, 23, 24, 25]
        })
        st.line_chart(df.set_index("تاریخ"))

    elif menu_choice == "زمانبندی":
        st.header("زمانبندی کارها")
        # نمایش جدول کارها
        df_schedule = pd.read_sql(f"SELECT * FROM schedule WHERE user_id={user_id} ORDER BY date DESC", conn)
        st.dataframe(df_schedule)
        # اضافه کردن کار جدید
        with st.form("add_task"):
            task = st.text_input("عنوان کار")
            date = st.date_input("تاریخ انجام")
            notes = st.text_area("یادداشت")
            if st.form_submit_button("اضافه کردن"):
                conn.execute("INSERT INTO schedule (user_id, task, date, notes) VALUES (?,?,?,?)",
                             (user_id, task, str(date), notes))
                conn.commit()
                st.success("کار اضافه شد!")
        # پیش‌بینی خودکار نیاز به آبیاری / حرص
        st.subheader("پیش‌بینی خودکار نیاز آبیاری و حرص")
        st.write("💧 برنامه به طور خودکار بررسی می‌کند که نهال نیاز به آب یا حرص دارد.")
        # نمونه: هر روز نیاز بررسی شود
        import random
        water_needed = random.choice([0, 1])
        fertilize_needed = random.choice([0, 1])
        st.write(f"💧 آبیاری: {'نیاز دارد' if water_needed else 'نیاز ندارد'}")
        st.write(f"🌱 حرص: {'نیاز دارد' if fertilize_needed else 'نیاز ندارد'}")
        # ذخیره پیش‌بینی
        conn.execute("INSERT INTO predictions (user_id, prediction_date, water_needed, fertilize_needed) VALUES (?,?,?,?)",
                     (user_id, str(datetime.today().date()), water_needed, fertilize_needed))
        conn.commit()

    elif menu_choice == "دانلود داده‌ها":
        st.header("دانلود داده‌ها")
        df_schedule = pd.read_sql(f"SELECT * FROM schedule WHERE user_id={user_id}", conn)
        st.download_button("دانلود زمانبندی", df_schedule.to_csv(index=False), "schedule.csv", "text/csv")

    elif menu_choice == "خروج":
        st.session_state.pop('user_id')
        st.experimental_rerun()

    conn.close()
