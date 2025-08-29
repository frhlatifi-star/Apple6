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

# ---------- Page Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
.block-container { direction: rtl !important; text-align: right !important; padding: 0 2rem; background: #f1f8f6; }
body { font-family: Vazirmatn, Tahoma, sans-serif; }

.navbar-wrap { display:flex; justify-content:center; margin-bottom:16px; flex-wrap: nowrap; }
.nav-item { background: #2e7d32; color: white; padding: 6px 12px; margin: 0 4px; border-radius: 6px;
            font-weight: 600; font-size: 14px; text-align: center; cursor: pointer; display: inline-block; }
.nav-item:hover { background: #1b5e20; }
.nav-item.active { background: #1b5e20; }
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
            st.rerun()
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
        st.rerun()

menu = st.session_state.menu

# ---------- Pages ----------
if menu == "🏠 خانه":
    st.header("خانه")
    try:
        with engine.connect() as conn:
            m_sel = sa.select(measurements).where(measurements.c.user_id==user_id)
            ms = conn.execute(m_sel).mappings().all()
        df_home = pd.DataFrame(ms)
    except Exception as e:
        st.error(f"خطا هنگام خواندن اندازه‌گیری‌ها: {e}")
        df_home = pd.DataFrame()

    if not df_home.empty:
        df_home['date'] = pd.to_datetime(df_home['date'])
        avg_growth = round(df_home['height'].diff().mean(), 2) if not df_home.empty else 0
        max_height = df_home['height'].max()
        last_height = df_home['height'].iloc[-1]

        c1, c2, c3 = st.columns(3)
        c1.metric("میانگین رشد (cm)", avg_growth if not pd.isna(avg_growth) else 0)
        c2.metric("بیشترین ارتفاع", max_height)
        c3.metric("آخرین ارتفاع", last_height)

        st.line_chart(df_home.set_index('date')['height'])
    else:
        st.info("هیچ داده‌ای برای نمایش وجود ندارد.")

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
                st.rerun()
            except Exception as e:
                st.error(f"خطا در ثبت اندازه‌گیری: {e}")

    # نمایش داده‌ها
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date)).mappings().all()
        if rows:
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            st.dataframe(df[['date','height','leaves','notes','prune_needed']])
            st.line_chart(df.set_index('date')['height'])
        else:
            st.info("هیچ داده‌ای برای نمایش وجود ندارد.")
    except Exception as e:
        st.error(f"خطا در بارگذاری داده‌ها: {e}")

elif menu == "📈 پیش‌بینی هرس":
    st.header("پیش‌بینی نیاز به هرس (بارگذاری تصویر)")

    uploaded_files = st.file_uploader(
        "آپلود تصویر نهال (تک یا چندگانه)", 
        type=["jpg","jpeg","png"], 
        accept_multiple_files=True
    )

    for uploaded in uploaded_files:
        try:
            img = Image.open(uploaded).convert("RGB")
            st.image(img, use_container_width=True, caption=uploaded.name)

            arr = np.array(img)

            # تحلیل رنگ
            r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
            yellow_ratio = float(((r>g)&(g>=b)).mean())
            green_ratio = float(((g>r+10)&(g>b+10)).mean())

            # محاسبه نیاز به هرس و احتمال
            needs_prune = green_ratio < 0.12 or yellow_ratio > 0.25
            probability = min(1.0, max(0.0, 0.5 + yellow_ratio - green_ratio))

            # نمایش کارت حرفه‌ای
            color = "#4CAF50" if not needs_prune else "#FF9800"
            icon = "✅" if not needs_prune else "⚠️"
            st.markdown(f"""
            <div style='background:{color}; padding:15px; border-radius:12px; text-align:center; font-size:18px; color:white; margin-bottom:10px;'>
                {icon} نیاز به هرس: {'بله' if needs_prune else 'خیر'} <br>
                احتمال: {probability*100:.1f}%
            </div>
            """, unsafe_allow_html=True)

            # نمودار رشد و رنگ برگ‌ها از داده‌های قبلی
            try:
                with engine.connect() as conn:
                    rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date)).mappings().all()
                if rows:
                    df_hist = pd.DataFrame(rows)
                    df_hist['date'] = pd.to_datetime(df_hist['date'])
                    st.subheader("نمودار رشد و تعداد برگ‌ها")
                    chart_data = pd.DataFrame({
                        "ارتفاع": df_hist['height'],
                        "تعداد برگ‌ها": df_hist['leaves']
                    }, index=df_hist['date'])
                    st.line_chart(chart_data)
            except Exception:
                pass

        except Exception as e:
            st.error(f"خطا در پردازش تصویر {uploaded.name}: {e}")

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
