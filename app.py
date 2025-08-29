# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image
import os
import base64
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey

# try import matplotlib, otherwise fallback to streamlit charts
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    HAS_MPL = False

# ---------- Page Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
.block-container { direction: rtl !important; text-align: right !important; padding: 0 2rem; background: #f1f8f6; }
body { font-family: Vazirmatn, Tahoma, sans-serif; }
.card { background: #ffffff; padding: 1rem; border-radius: 12px; margin-bottom:10px; box-shadow:0 4px 8px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "users_data.db")
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)
measurements = Table(
    'measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)
meta.create_all(engine)

# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

# ---------- Session defaults ----------
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'menu' not in st.session_state:
    st.session_state.menu = "🏠 خانه"

# ---------- Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            img_html = f"<img src='data:image/png;base64,{encoded}' width='48' style='border-radius:12px;margin-left:10px;'>"
        except Exception:
            img_html = "<div style='font-size:32px;'>🍎</div>"
    else:
        img_html = "<div style='font-size:32px;'>🍎</div>"

    st.markdown(f"""
    <div style='display:flex;align-items:center;margin:10px 0;'>
        {img_html}
        <div>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#555'>مدیریت و پایش نهال</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

app_header()

# ---------- Authentication ----------
def register_user(username, password):
    if not username or not password:
        st.error("نام کاربری و رمز عبور را وارد کنید.")
        return False
    try:
        with engine.begin() as conn:
            sel = sa.select(users_table).where(users_table.c.username == username.strip())
            if conn.execute(sel).mappings().first():
                st.error("این نام کاربری قبلاً ثبت شده.")
                return False
            conn.execute(users_table.insert().values(
                username=username.strip(),
                password_hash=hash_password(password)
            ))
        st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
        return True
    except Exception as e:
        st.error(f"خطا در ثبت‌نام: {e}")
        return False

def login_user(username, password):
    if not username or not password:
        st.error("نام کاربری و رمز عبور را وارد کنید.")
        return False
    try:
        with engine.connect() as conn:
            r = conn.execute(sa.select(users_table).where(users_table.c.username==username.strip())).mappings().first()
        if not r:
            st.error("نام کاربری یافت نشد.")
            return False
        if check_password(password, r['password_hash']):
            st.session_state.user_id = r['id']
            st.session_state.username = r['username']
            # safe rerun
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()
            return True
        else:
            st.error("رمز عبور اشتباه است.")
            return False
    except Exception as e:
        st.error(f"خطا در ورود: {e}")
        return False

def auth_ui():
    st.subheader("ورود / ثبت‌نام")
    mode = st.radio("حالت:", ["ورود","ثبت‌نام"], horizontal=True)
    if mode == "ثبت‌نام":
        u = st.text_input("نام کاربری", key="signup_u")
        p = st.text_input("رمز عبور", type="password", key="signup_p")
        if st.button("ثبت‌نام"):
            register_user(u, p)
    else:
        u = st.text_input("نام کاربری", key="login_u")
        p = st.text_input("رمز عبور", type="password", key="login_p")
        if st.button("ورود"):
            login_user(u, p)

if st.session_state.user_id is None:
    auth_ui()
    st.stop()

user_id = st.session_state.user_id

# ---------- Top Navbar ----------
menu_items = ["🏠 خانه", "🌱 پایش نهال", "📈 پیش‌بینی هرس", "📥 دانلود داده‌ها"]
cols = st.columns(len(menu_items) + 1)  # +1 برای خروج

# دکمه‌های منو
for i, item in enumerate(menu_items):
    with cols[i]:
        if st.button(item, key=f"nav_{i}"):
            st.session_state.menu = item

# دکمه خروج جدا
with cols[-1]:
    if st.button("🚪 خروج", key="logout_btn"):
        for k in ["user_id", "username"]:
            st.session_state[k] = None
        st.session_state.menu = "🏠 خانه"
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()

menu = st.session_state.menu

# ---------- Pages ----------
if menu == "🏠 خانه":
    st.header("خانه")
    try:
        with engine.connect() as conn:
            ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
    except Exception as e:
        st.error(f"خطا هنگام خواندن اندازه‌گیری‌ها: {e}")
        ms = []

    if ms:
        df_home = pd.DataFrame(ms)
        df_home['date'] = pd.to_datetime(df_home['date'], errors="coerce")
        df_home = df_home.sort_values('date')

        # آمار کلیدی
        avg_growth = df_home['height'].diff().mean().round(2)
        max_height = df_home['height'].max()
        last_height = df_home['height'].iloc[-1]

        c1, c2, c3 = st.columns(3)
        c1.metric("میانگین رشد (cm)", avg_growth if not pd.isna(avg_growth) else 0)
        c2.metric("بیشترین ارتفاع", max_height)
        c3.metric("آخرین ارتفاع", last_height)

        # نمودار ارتفاع + برگ‌ها
        if HAS_MPL:
            fig, ax1 = plt.subplots()
            ax1.plot(df_home['date'], df_home['height'], label="ارتفاع (cm)", linewidth=2)
            ax2 = ax1.twinx()
            ax2.plot(df_home['date'], df_home['leaves'], color="green", linestyle="--", label="تعداد برگ‌ها")
            ax1.set_xlabel("تاریخ")
            ax1.set_ylabel("ارتفاع (cm)")
            ax2.set_ylabel("تعداد برگ")
            fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9))
            st.pyplot(fig)
        else:
            st.warning("پکیج matplotlib نصب نیست — نمایش نمودارها با چارت‌های داخلی Streamlit.")
            # دو چارت جداگانه (ارتفاع و برگ) به عنوان fallback
            st.subheader("ارتفاع (cm)")
            st.line_chart(df_home.set_index('date')['height'])
            st.subheader("تعداد برگ‌ها")
            st.line_chart(df_home.set_index('date')['leaves'])

        # جدول آخرین ۱۰ رکورد
        st.subheader("آخرین اندازه‌گیری‌ها")
        df_show = df_home[['date','height','leaves','prune_needed','notes']].tail(10)
        df_show['prune_needed'] = df_show['prune_needed'].map({0:"خیر",1:"بله"})
        st.dataframe(df_show, use_container_width=True)
    else:
        st.info("هنوز داده‌ای ثبت نشده است.")

elif menu == "🌱 پایش نهال":
    st.header("پایش نهال")
    with st.form("add_measure"):
        date = st.date_input("تاریخ", value=datetime.today())
        height = st.number_input("ارتفاع (cm)", min_value=0, step=1)
        leaves = st.number_input("تعداد برگ", min_value=0, step=1)
        notes = st.text_area("یادداشت")
        prune = st.checkbox("نیاز به هرس؟")
        if st.form_submit_button("ثبت"):
            try:
                with engine.begin() as conn:
                    conn.execute(measurements.insert().values(
                        user_id=user_id,
                        date=str(date),
                        height=int(height),
                        leaves=int(leaves),
                        notes=notes or "",
                        prune_needed=int(bool(prune))
                    ))
                st.success("ثبت شد.")
            except Exception as e:
                st.error(f"خطا در ثبت اندازه‌گیری: {e}")

    # نمایش داده‌ها
    with engine.connect() as conn:
        rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
    if rows:
        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date'], errors="coerce")
        df = df.sort_values('date')

        # فیلتر تاریخ
        min_d, max_d = df['date'].min(), df['date'].max()
        start, end = st.date_input("بازه تاریخی", [min_d, max_d])
        df = df[(df['date'] >= pd.to_datetime(start)) & (df['date'] <= pd.to_datetime(end))]

        st.dataframe(df[['date','height','leaves','prune_needed','notes']], use_container_width=True)

        if not df.empty:
            st.line_chart(df.set_index('date')['height'])
    else:
        st.info("هیچ داده‌ای برای نمایش وجود ندارد.")

elif menu == "📈 پیش‌بینی هرس":
    st.header("پیش‌بینی نیاز به هرس (بارگذاری تصویر)")
    uploaded = st.file_uploader("آپلود تصویر نهال", type=["jpg","jpeg","png"])
    if uploaded:
        try:
            img = Image.open(uploaded)
            st.image(img, use_container_width=True)
            arr = np.array(img)
            if arr.ndim == 3 and arr.shape[2] >= 3:
                r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
                yellow_ratio = float(((r>g)&(g>=b)).mean())
                green_ratio = float(((g>r+10)&(g>b+10)).mean())
                needs_prune = green_ratio < 0.12 or yellow_ratio > 0.25
                st.success(f"نیاز به هرس: {'بله' if needs_prune else 'خیر'}")
            else:
                st.info("تصویر بارگذاری شده برای تحلیل مناسب نیست.")
        except Exception as e:
            st.error(f"خطا در پردازش تصویر: {e}")

elif menu == "📥 دانلود داده‌ها":
    st.header("دانلود داده‌ها")
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
            if rows:
                df = pd.DataFrame(rows)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("دانلود اندازه‌گیری‌ها (CSV)", csv, "measurements.csv", "text/csv")
            else:
                st.info("هیچ داده‌ای برای دانلود وجود ندارد.")
    except Exception as e:
        st.error(f"خطا در آماده‌سازی فایل دانلود: {e}")
