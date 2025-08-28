import streamlit as st
import pandas as pd
import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, Date, Float, MetaData
from datetime import datetime, timedelta
import os
import random

# ======================
# تنظیمات دیتابیس SQLite
# ======================
DB_FILE = "app_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}")
conn = engine.connect()
metadata = MetaData()

# ======================
# جدول‌های دیتابیس
# ======================
users_table = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False)
)

schedule_table = Table(
    "schedule", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("task", String, nullable=False),
    Column("date", Date, nullable=False),
    Column("notes", String)
)

predictions_table = Table(
    "predictions", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("date", Date, nullable=False),
    Column("water_needed", Float, nullable=False),
    Column("pruning_needed", String, nullable=False)
)

# ایجاد جدول‌ها اگر موجود نباشند
metadata.create_all(engine)

# ======================
# بخش UI
# ======================
st.set_page_config(page_title="سیبتک – کشاورزی هوشمند", layout="wide")
st.title("🌱 سیبتک – مدیریت نهال سیب")

# منو اصلی به شکل دکمه
menu_options = ["خانه", "ثبت برنامه", "مشاهده زمان‌بندی", "پیش‌بینی نیاز آبیاری و حرص", "دانلود داده‌ها"]
menu_choice = st.radio("صفحات:", menu_options)

# ======================
# داده‌های نمونه کاربر
# ======================
def get_user_id():
    # در نسخه نمونه یک user ثابت داریم
    user = conn.execute(sa.select(users_table).where(users_table.c.name=="کاربر نمونه")).fetchone()
    if user is None:
        result = conn.execute(users_table.insert().values(name="کاربر نمونه"))
        return result.inserted_primary_key[0]
    return user.id

user_id = get_user_id()

# ======================
# صفحه خانه
# ======================
def page_home():
    st.header("خانه")
    st.write("📌 خوش آمدید به اپلیکیشن مدیریت هوشمند نهال سیب")
    st.write("در این اپلیکیشن می‌توانید برنامه‌ها، پیش‌بینی آبیاری و حرص را مدیریت کنید.")

# ======================
# ثبت برنامه
# ======================
def page_schedule():
    st.header("ثبت برنامه جدید")
    task = st.text_input("نام برنامه")
    date = st.date_input("تاریخ اجرای برنامه", datetime.today())
    notes = st.text_area("یادداشت‌ها")
    if st.button("ثبت"):
        if task:
            conn.execute(schedule_table.insert().values(user_id=user_id, task=task, date=date, notes=notes))
            st.success("برنامه ثبت شد ✅")
        else:
            st.error("نام برنامه نمی‌تواند خالی باشد!")

# ======================
# مشاهده زمان‌بندی
# ======================
def page_view_schedule():
    st.header("برنامه‌های زمان‌بندی")
    df = pd.DataFrame(conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id).order_by(schedule_table.c.date.desc())).mappings().all())
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("هیچ برنامه‌ای ثبت نشده است.")

# ======================
# پیش‌بینی نیاز آبیاری و حرص
# ======================
def page_prediction():
    st.header("پیش‌بینی نیاز آبیاری و حرص")
    today = datetime.today().date()
    future_days = [today + timedelta(days=i) for i in range(7)]
    
    # تولید داده پیش‌بینی نمونه
    predictions = []
    for d in future_days:
        water_needed = round(random.uniform(0.0, 2.0), 2)  # لیتر
        pruning_needed = random.choice(["نیاز ندارد", "نیاز دارد"])
        predictions.append({"date": d, "water_needed": water_needed, "pruning_needed": pruning_needed})
    
    df_pred = pd.DataFrame(predictions)
    st.dataframe(df_pred)

    # ذخیره در دیتابیس
    for row in predictions:
        exists = conn.execute(
            sa.select(predictions_table).where(
                (predictions_table.c.user_id==user_id) & 
                (predictions_table.c.date==row["date"])
            )
        ).fetchone()
        if not exists:
            conn.execute(predictions_table.insert().values(
                user_id=user_id,
                date=row["date"],
                water_needed=row["water_needed"],
                pruning_needed=row["pruning_needed"]
            ))

# ======================
# دانلود داده‌ها
# ======================
def page_download():
    st.header("دانلود داده‌ها")
    df_schedule = pd.DataFrame(conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id)).mappings().all())
    df_pred = pd.DataFrame(conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all())
    if st.button("دانلود CSV زمان‌بندی"):
        df_schedule.to_csv("schedule.csv", index=False)
        st.success("فایل schedule.csv ایجاد شد ✅")
    if st.button("دانلود CSV پیش‌بینی"):
        df_pred.to_csv("predictions.csv", index=False)
        st.success("فایل predictions.csv ایجاد شد ✅")

# ======================
# اجرای صفحات
# ======================
pages = {
    "خانه": page_home,
    "ثبت برنامه": page_schedule,
    "مشاهده زمان‌بندی": page_view_schedule,
    "پیش‌بینی نیاز آبیاری و حرص": page_prediction,
    "دانلود داده‌ها": page_download
}

pages[menu_choice]()
