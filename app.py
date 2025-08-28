# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageStat
import os
import base64
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
import io

# برای دانلود از گیت‌هاب (در صورت نیاز)
try:
    import requests
except Exception:
    requests = None

# ---------- تنظیمات (اگر می‌خواهی خودکار از گیت‌هاب دانلود شود، آدرس raw فایل را اینجا قرار بده) ----------
# مثال: "https://raw.githubusercontent.com/USERNAME/REPO/main/users_data.db"
GITHUB_DB_RAW_URL = ""  # <-- این را با raw url فایل users_data.db در گیت‌هاب خودت (در صورت وجود) پر کن

# ---------- Page Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS / RTL ----------
st.markdown("""
<style>
:root {
    --accent: #2e7d32;
    --accent-2: #388e3c;
    --bg-1: #eaf9e7;
    --card: #ffffff;
}
.block-container { direction: rtl !important; text-align: right !important; padding: 1.2rem 2rem; background: var(--bg-1); }
body { font-family: Vazirmatn, Tahoma, sans-serif; }
.stButton>button { background-color: var(--accent-2) !important; color: white !important; border-radius: 8px !important; padding: 8px 16px; }
.card { background: var(--card); padding: 1rem; border-radius: 12px; margin-bottom:10px; box-shadow:0 4px 8px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

# ---------- Database path ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "users_data.db")

# ---------- Utility: try download DB from GitHub if not exists ----------
def try_download_db_from_github(raw_url: str, target_path: str, timeout: int = 10) -> bool:
    """
    تلاش می‌کند فایل دیتابیس را از raw_url دانلود کند و در target_path ذخیره کند.
    در صورت موفقیت True برمی‌گرداند، در غیر این صورت False.
    """
    if not raw_url:
        return False
    if requests is None:
        return False
    try:
        resp = requests.get(raw_url, timeout=timeout)
        if resp.status_code == 200:
            # اگر پاسخی داریم، محتوا را بنویس
            with open(target_path, "wb") as f:
                f.write(resp.content)
            return True
        else:
            return False
    except Exception:
        return False

# اگر فایل دیتابیس وجود نداشت، تلاش کن از گیت‌هاب دانلود کنی
db_status_msg = ""
if not os.path.exists(DB_FILE):
    downloaded = False
    if GITHUB_DB_RAW_URL:
        downloaded = try_download_db_from_github(GITHUB_DB_RAW_URL, DB_FILE)
    if downloaded:
        db_status_msg = "دیتابیس از گیت‌هاب دانلود و ذخیره شد."
    else:
        # اگر دانلود نشد، فایل دیتابیس را خالی می‌سازیم (create_all بعداً جداول را اضافه می‌کند)
        try:
            # ایجاد فایل خالی
            open(DB_FILE, "wb").close()
            db_status_msg = "فایل دیتابیس محلی ایجاد شد (جداول در ادامه ساخته می‌شوند)."
        except Exception as e:
            db_status_msg = f"خطا در ایجاد فایل دیتابیس محلی: {e}"

# ---------- Engine و Meta ----------
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

# ایجاد جداول در صورت نبودن
try:
    meta.create_all(engine)
except Exception as e:
    st.error(f"خطا هنگام ساخت جداول دیتابیس: {e}")

# ---------- Helpers ----------
def hash_password(password: str) -> str:
    # bcrypt ممکن است زمان‌بر باشد اما امن است
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

# ---------- UI Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;margin-left:10px;'>"
        except Exception:
            img_html = "<div style='font-size:36px;'>🍎</div>"
    else:
        img_html = "<div style='font-size:36px;'>🍎</div>"

    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:10px;'>
        {img_html}
        <div>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#555'>مدیریت و پایش نهال</small>
        </div>
    </div>
    <hr/>
    """, unsafe_allow_html=True)
    if db_status_msg:
        st.info(db_status_msg)

app_header()

# ---------- Authentication ----------
def register_user(username, password):
    if not username or not password:
        st.error("نام کاربری و رمز عبور را وارد کنید.")
        return False
    with engine.connect() as conn:
        sel = sa.select(users_table).where(users_table.c.username==username)
        if conn.execute(sel).mappings().first():
            st.error("این نام کاربری قبلاً ثبت شده.")
            return False
        else:
            try:
                conn.execute(users_table.insert().values(username=username, password_hash=hash_password(password)))
                st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
                return True
            except Exception as e:
                st.error(f"خطا در ثبت‌نام: {e}")
                return False

def login_user(username, password):
    if not username or not password:
        st.error("نام کاربری و رمز عبور را وارد کنید.")
        return False
    with engine.connect() as conn:
        r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
        if not r:
            st.error("نام کاربری یافت نشد.")
            return False
        elif check_password(password, r['password_hash']):
            st.session_state.user_id = r['id']
            st.session_state.username = r['username']
            # بعد از ورود صفحه را ری‌رن کنید تا state اعمال شود
            st.experimental_rerun()
            return True
        else:
            st.error("رمز عبور اشتباه است.")
            return False

def auth_ui():
    st.subheader("ورود / ثبت‌نام")
    mode = st.radio("حالت:", ["ورود","ثبت‌نام"], horizontal=True)
    if mode=="ثبت‌نام":
        u = st.text_input("نام کاربری", key="signup_u")
        p = st.text_input("رمز عبور", type="password", key="signup_p")
        if st.button("ثبت‌نام"):
            register_user(u.strip(), p)
    else:
        u = st.text_input("نام کاربری", key="login_u")
        p = st.text_input("رمز عبور", type="password", key="login_p")
        if st.button("ورود"):
            login_user(u.strip(), p)

if st.session_state.user_id is None:
    auth_ui()
    st.stop()

# ---------- Sidebar Menu ----------
menu = st.sidebar.selectbox(f"خوش آمدید، {st.session_state.username}", [
    "🏠 خانه",
    "🌱 پایش نهال",
    "📈 پیش‌بینی هرس",
    "📥 دانلود داده‌ها",
    "🚪 خروج"
])

user_id = st.session_state.user_id

if menu=="🚪 خروج":
    st.session_state.user_id=None
    st.session_state.username=None
    st.experimental_rerun()

# ---------- Pages ----------
if menu=="🏠 خانه":
    st.header("خانه")
    try:
        with engine.connect() as conn:
            m_sel = sa.select(measurements).where(measurements.c.user_id==user_id)
            ms = conn.execute(m_sel).mappings().all()
    except Exception as e:
        st.error(f"خطا هنگام خواندن اندازه‌گیری‌ها: {e}")
        ms = []
    st.markdown(f"<div class='card'><h3>تعداد اندازه‌گیری‌ها: {len(ms)}</h3></div>", unsafe_allow_html=True)

elif menu=="🌱 پایش نهال":
    st.header("پایش نهال")
    with st.form("add_measure"):
        date = st.date_input("تاریخ", value=datetime.today())
        height = st.number_input("ارتفاع (cm)", min_value=0, step=1)
        leaves = st.number_input("تعداد برگ", min_value=0, step=1)
        notes = st.text_area("یادداشت")
        prune = st.checkbox("نیاز به هرس؟")
        if st.form_submit_button("ثبت"):
            try:
                with engine.connect() as conn:
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

    # نمایش نمودار رشد
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date)).mappings().all()
            if rows:
                df = pd.DataFrame(rows)
                # مطمئن شویم ستون date قابل تبدیل است
                try:
                    df['date'] = pd.to_datetime(df['date'])
                    st.line_chart(df.set_index('date')['height'])
                except Exception:
                    st.info("تبدیل تاریخ ممکن نبود؛ داده‌ها نمایش داده نمی‌شوند.")
            else:
                st.info("هیچ داده‌ای برای نمایش وجود ندارد.")
    except Exception as e:
        st.error(f"خطا در بارگذاری داده‌ها: {e}")

elif menu=="📈 پیش‌بینی هرس":
    st.header("پیش‌بینی نیاز به هرس (بارگذاری تصویر)")
    uploaded = st.file_uploader("آپلود تصویر نهال", type=["jpg","jpeg","png"])
    if uploaded:
        try:
            img = Image.open(uploaded)
            st.image(img, use_container_width=True)
            stat = ImageStat.Stat(img.convert("RGB"))
            arr = np.array(img)
            if arr.ndim == 3 and arr.shape[2] >= 3:
                r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
                # نسبت‌های ساده
                yellow_ratio = float(((r>g)&(g>=b)).mean())
                green_ratio = float(((g>r+10)&(g>b+10)).mean())
                needs_prune = green_ratio < 0.12 or yellow_ratio > 0.25
                st.success(f"نیاز به هرس: {'بله' if needs_prune else 'خیر'}")
            else:
                st.info("تصویر بارگذاری شده برای تحلیل مناسب نیست.")
        except Exception as e:
            st.error(f"خطا در پردازش تصویر: {e}")

elif menu=="📥 دانلود داده‌ها":
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
