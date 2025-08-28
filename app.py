import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image
import matplotlib.pyplot as plt
import io

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# Users table
users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))

# Measurements table
measurements = Table('measurements', meta,
                     Column('id', Integer, primary_key=True),
                     Column('user_id', Integer, ForeignKey('users.id')),
                     Column('date', String),
                     Column('height', Integer),
                     Column('leaves', Integer),
                     Column('notes', String),
                     Column('prune_needed', Integer))

# Schedule table
schedule_table = Table('schedule', meta,
                       Column('id', Integer, primary_key=True),
                       Column('user_id', Integer, ForeignKey('users.id')),
                       Column('task', String),
                       Column('date', String),
                       Column('notes', String))

meta.create_all(engine)
conn = engine.connect()

# ---------- Session ----------
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'username' not in st.session_state: st.session_state['username'] = None
if 'demo_data' not in st.session_state: st.session_state['demo_data'] = []

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Login / SignUp ----------
if st.session_state['user_id'] is None:
    # Header with logo and app name
    st.markdown(
        """
        <div style='display:flex; align-items:center;'>
            <img src='https://i.imgur.com/4Y2E2XQ.png' width='60' style='margin-right:15px;'/>
            <h2 style='margin:0;'>سیبتک 🍎 پایش نهال</h2>
        </div>
        """, unsafe_allow_html=True
    )

    mode = st.radio("حالت:", ["ورود", "ثبت‌نام", "دمو"], index=0, horizontal=True)

    if mode == "ثبت‌نام":
        st.subheader("ثبت‌نام")
        username = st.text_input("نام کاربری")
        password = st.text_input("رمز عبور", type="password")
        if st.button("ثبت"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                sel = sa.select(users_table).where(users_table.c.username == username)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error("نام کاربری موجود است.")
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success("ثبت‌نام انجام شد. لطفاً وارد شوید.")

    elif mode == "ورود":
        st.subheader("ورود")
        username = st.text_input("نام کاربری")
        password = st.text_input("رمز عبور", type="password")
        if st.button("ورود"):
            sel = sa.select(users_table).where(users_table.c.username == username)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error("نام کاربری یافت نشد.")
            elif check_password(password, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.experimental_rerun()
            else:
                st.error("رمز عبور اشتباه است.")

    else:  # Demo
        st.subheader("دمو")
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

# ---------- Logged-in Menu ----------
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", ["🏠 خانه", "🌱 پایش", "📅 زمان‌بندی", "📈 پیش‌بینی", "🍎 بیماری", "📥 دانلود", "🚪 خروج"])
    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    # ---------- Home ----------
    elif menu == "🏠 خانه":
        st.header("خانه")
        st.write("به سیبتک 🍎 پایش نهال خوش آمدید!")

    # ---------- Tracking ----------
    elif menu == "🌱 پایش":
        st.header("پایش نهال")
        with st.expander("➕ افزودن اندازه‌گیری"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت", placeholder="وضعیت آبیاری، کوددهی، علائم...")
            prune = st.checkbox("نیاز به هرس؟")
            if st.button("ثبت اندازه‌گیری"):
                conn.execute(measurements.insert().values(user_id=user_id, date=str(date),
                                                          height=height, leaves=leaves, notes=notes,
                                                          prune_needed=int(prune)))
                st.success("اندازه‌گیری ذخیره شد.")
        sel = sa.select(measurements).where(measurements.c.user_id == user_id).order_by(measurements.c.date.desc())
        df = pd.DataFrame(conn.execute(sel).mappings().all())
        if not df.empty:
            st.dataframe(df)
            # نمودار پایش
            fig, ax = plt.subplots()
            ax.plot(pd.to_datetime(df['date']), df['height'], marker='o', label='ارتفاع')
            ax.set_xlabel("تاریخ")
            ax.set_ylabel("ارتفاع (سانتی‌متر)")
            ax.set_title("روند ارتفاع نهال‌ها")
            ax.grid(True)
            st.pyplot(fig)

    # ---------- Schedule ----------
    elif menu == "📅 زمان‌بندی":
        st.header("زمان‌بندی")
        with st.expander("➕ افزودن برنامه"):
            task = st.text_input("فعالیت")
            date = st.date_input("تاریخ برنامه")
            notes = st.text_area("یادداشت")
            if st.button("ثبت برنامه"):
                conn.execute(schedule_table.insert().values(user_id=user_id, task=task, date=str(date), notes=notes))
                st.success("برنامه ثبت شد.")
        sel = sa.select(schedule_table).where(schedule_table.c.user_id == user_id).order_by(schedule_table.c.date.desc())
        df = pd.DataFrame(conn.execute(sel).mappings().all())
        if not df.empty:
            st.dataframe(df)

    # ---------- Prediction ----------
    elif menu == "📈 پیش‌بینی":
        st.header("پیش‌بینی سلامت")
        f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success("پیش‌بینی: سالم (نمونه)")
            st.write("یادداشت: این نتیجه آزمایشی است.")

    # ---------- Disease ----------
    elif menu == "🍎 بیماری":
        st.header("ثبت بیماری")
        disease_note = st.text_area("علائم یا مشکل مشاهده شده")
        if st.button("ثبت"):
            st.success("یادداشت بیماری ثبت شد.")

    # ---------- Download ----------
    elif menu == "📥 دانلود":
        st.header("دانلود داده‌ها")
        sel = sa.select(measurements).where(measurements.c.user_id == user_id)
        df = pd.DataFrame(conn.execute(sel).mappings().all())
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("دانلود CSV", csv, "measurements.csv", "text/csv")
        else:
            st.info("داده‌ای برای دانلود موجود نیست.")
