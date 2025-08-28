import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image
import io
import random

# ---------- Config ----------
st.set_page_config(page_title="🍎 سیب نهال پرو", page_icon="🍎", layout="wide")

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
                    Column('id', Integer, primary_key=True),
                    Column('username', String, unique=True, nullable=False),
                    Column('password_hash', String, nullable=False))

measurements = Table('measurements', meta,
                     Column('id', Integer, primary_key=True),
                     Column('user_id', Integer, ForeignKey('users.id')),
                     Column('date', String),
                     Column('height', Integer),
                     Column('leaves', Integer),
                     Column('notes', String),
                     Column('prune_needed', Integer),
                     Column('image_file', String))

meta.create_all(engine)

# ---------- Session ----------
if 'user_id' not in st.session_state: st.session_state['user_id'] = None
if 'username' not in st.session_state: st.session_state['username'] = None
if 'demo_data' not in st.session_state: st.session_state['demo_data'] = []

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Header Logo ----------
def show_header():
    col1, col2 = st.columns([1,3])
    with col1:
        try:
            st.image("logo.png", width=80)  # لوگوی خود را در مسیر پروژه قرار دهید
        except:
            st.write("🍎")
    with col2:
        st.markdown("<h1 style='text-align:right;'>سیب نهال پرو</h1>", unsafe_allow_html=True)

# ---------- Authentication ----------
if st.session_state['user_id'] is None:
    show_header()
    st.subheader("ورود به سیستم")
    username_input = st.text_input("نام کاربری", key="login_username")
    password_input = st.text_input("رمز عبور", type="password", key="login_password")
    
    if st.button("ورود"):
        sel = sa.select(users_table).where(users_table.c.username==username_input)
        r = engine.connect().execute(sel).mappings().first()
        if not r:
            st.error("نام کاربری یافت نشد.")
        elif check_password(password_input, r['password_hash']):
            st.session_state['user_id'] = r['id']
            st.session_state['username'] = r['username']
            st.success("ورود موفق!")
            st.experimental_rerun()
        else:
            st.error("رمز عبور اشتباه است.")
    
    st.markdown("---")
    st.subheader("ثبت نام کاربر جدید")
    new_username = st.text_input("نام کاربری جدید", key="signup_username")
    new_password = st.text_input("رمز عبور جدید", type="password", key="signup_password")
    if st.button("ثبت نام"):
        if not new_username or not new_password:
            st.error("نام کاربری و رمز عبور را وارد کنید.")
        else:
            sel = sa.select(users_table).where(users_table.c.username==new_username)
            r = engine.connect().execute(sel).mappings().first()
            if r:
                st.error("نام کاربری وجود دارد.")
            else:
                hashed = hash_password(new_password)
                with engine.begin() as conn:
                    conn.execute(users_table.insert().values(username=new_username, password_hash=hashed))
                st.success("ثبت نام موفق! لطفا وارد شوید.")

else:
    # ---------- Main App after Login ----------
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", ["🏠 خانه", "🌱 پایش", "📅 زمان‌بندی", "📈 پیش‌بینی", "🍎 بیماری", "📥 دانلود", "💻 دمو", "🚪 خروج"])
    
    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    elif menu == "🏠 خانه":
        st.header("🏠 خانه")
        st.markdown("به اپلیکیشن سیب نهال پرو خوش آمدید.")

    elif menu == "🌱 پایش":
        st.header("🌱 پایش نهال")
        with st.expander("➕ افزودن اندازه‌گیری"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت", placeholder="وضعیت آبیاری، کوددهی، علائم...")
            prune = st.checkbox("نیاز به هرس؟")
            f = st.file_uploader("آپلود تصویر نهال", type=["jpg","jpeg","png"])
            if st.button("ثبت اندازه‌گیری"):
                with engine.begin() as conn:
                    conn.execute(measurements.insert().values(
                        user_id=st.session_state['user_id'],
                        date=str(date),
                        height=height,
                        leaves=leaves,
                        notes=notes,
                        prune_needed=int(prune),
                        image_file=f.name if f else ""
                    ))
                st.success("اندازه‌گیری ذخیره شد.")
        sel = sa.select(measurements).where(measurements.c.user_id==st.session_state['user_id']).order_by(measurements.c.date.desc())
        df = pd.DataFrame(engine.connect().execute(sel).mappings().all())
        if not df.empty:
            st.dataframe(df)

    elif menu == "💻 دمو":
        st.header("💻 دمو پیش‌بینی سلامت نهال")
        f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            # پیش‌بینی با پردازش تصویر ساده
            image = Image.open(f)
            # اینجا می‌توان مدل ML یا پردازش تصویر واقعی قرار داد
            result = random.choice(["سالم", "بیمار"])  # نمونه ساده
            st.success(f"پیش‌بینی: {result}")
            st.session_state['demo_data'].append({'file': f.name, 'result': result, 'time': datetime.now()})
        
        if st.session_state['demo_data']:
            st.subheader("تاریخچه دمو")
            df_demo = pd.DataFrame(st.session_state['demo_data'])
            st.dataframe(df_demo)

    else:
        st.header(menu)
        st.info("این بخش هنوز فعال نیست.")
