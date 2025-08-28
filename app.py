import streamlit as st
import sqlalchemy as sa
import pandas as pd
from datetime import date
from PIL import Image

# ---------------- اتصال به دیتابیس ----------------
engine = sa.create_engine("sqlite:///apple_dashboard.db")
meta = sa.MetaData()

# جدول کاربران
users_table = sa.Table(
    "users",
    meta,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("username", sa.String, nullable=False, unique=True),
    sa.Column("password", sa.String, nullable=False)
)

# جدول زمان‌بندی فعالیت‌ها
schedule_table = sa.Table(
    "schedule",
    meta,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("user_id", sa.Integer, nullable=False),
    sa.Column("task", sa.String, nullable=False),
    sa.Column("date", sa.String, nullable=False),
    sa.Column("notes", sa.String, nullable=True)
)

meta.create_all(engine)

# ---------------- ورود کاربر ----------------
def login():
    st.title("ورود به داشبورد نهال سیب")
    username = st.text_input("نام کاربری")
    password = st.text_input("رمز عبور", type="password")
    login_btn = st.button("ورود")

    if login_btn:
        with engine.connect() as conn:
            sel = sa.select(users_table).where(
                (users_table.c.username == username) &
                (users_table.c.password == password)
            )
            user = conn.execute(sel).mappings().first()
            if user:
                st.session_state.user_id = user["id"]
                st.success("ورود موفقیت‌آمیز!")
            else:
                st.error("نام کاربری یا رمز عبور اشتباه است.")

# ---------------- داشبورد اصلی ----------------
def dashboard():
    st.header("داشبورد نهال سیب 🌱")
    st.write("اینجا می‌توانید فعالیت‌ها را مدیریت کنید و پیش‌بینی بیماری را مشاهده کنید.")

# ---------------- پیش‌بینی بیماری ----------------
def disease_prediction():
    st.header("پیش‌بینی بیماری نهال")
    st.write("در این بخش می‌توانید تصویر برگ یا نهال را آپلود کنید و پیش‌بینی بیماری دریافت کنید.")
    uploaded_file = st.file_uploader("آپلود تصویر برگ")
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="تصویر بارگذاری شده", use_container_width=True)
        # اینجا می‌تونیم مدل ML قرار بدیم
        st.info("مدل پیش‌بینی بیماری در حال حاضر فعال نیست.")

# ---------------- زمان‌بندی فعالیت‌ها ----------------
def schedule_page():
    st.header("زمان‌بندی فعالیت‌ها")

    if "user_id" not in st.session_state:
        st.warning("ابتدا وارد شوید.")
        return

    user_id = st.session_state.user_id

    # فرم ثبت فعالیت جدید
    with st.form("add_task_form"):
        task = st.text_input("فعالیت:")
        task_date = st.date_input("تاریخ:", value=date.today())
        task_notes = st.text_area("توضیحات:")
        submitted = st.form_submit_button("ثبت فعالیت")

        if submitted:
            if not task:
                st.error("لطفاً نام فعالیت را وارد کنید.")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(
                            schedule_table.insert().values(
                                user_id=user_id,
                                task=task,
                                date=str(task_date),
                                notes=task_notes
                            )
                        )
                    st.success("فعالیت با موفقیت ثبت شد!")
                except Exception as e:
                    st.error(f"خطا در ثبت فعالیت: {e}")

    # نمایش جدول برنامه‌های کاربر
    st.subheader("فعالیت‌های ثبت‌شده")
    try:
        with engine.connect() as conn:
            sel = sa.select(schedule_table).where(schedule_table.c.user_id == user_id).order_by(schedule_table.c.date.desc())
            rows = conn.execute(sel).mappings().all()
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("هیچ برنامه‌ای ثبت نشده است.")
    except Exception as e:
        st.error(f"خطای غیرمنتظره: {e}")

# ---------------- روتر صفحات ----------------
def main():
    if "user_id" not in st.session_state:
        login()
    else:
        pages = {
            "داشبورد": dashboard,
            "پیش‌بینی بیماری": disease_prediction,
            "زمان‌بندی فعالیت‌ها": schedule_page
        }
        choice = st.sidebar.selectbox("صفحه:", list(pages.keys()))
        pages[choice]()

# ---------------- اجرای برنامه ----------------
if __name__ == "__main__":
    main()
