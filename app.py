import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

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
                     Column('prune_needed', Integer))

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

# ---------- Logo ----------
try:
    logo = Image.open("logo.png")  # مطمئن شوید لوگو در مسیر اجرا موجود است
except:
    logo = None

if logo:
    st.image(logo, width=150)

# ---------- Authentication ----------
if st.session_state['user_id'] is None:
    st.header("🍎 ورود / ثبت‌نام")
    mode = st.radio("حالت", ["ورود", "ثبت‌نام", "دمو"])

    if mode == "ثبت‌نام":
        username_input = st.text_input("نام کاربری", key="signup_username")
        password_input = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت"):
            if not username_input or not password_input:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                sel = sa.select(users_table).where(users_table.c.username==username_input)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error("نام کاربری وجود دارد.")
                else:
                    hashed = hash_password(password_input)
                    with engine.begin() as conn_write:
                        conn_write.execute(users_table.insert().values(username=username_input, password_hash=hashed))
                    st.success("ثبت شد. لطفا وارد شوید.")

    elif mode == "ورود":
        username_input = st.text_input("نام کاربری", key="login_username")
        password_input = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            sel = sa.select(users_table).where(users_table.c.username==username_input)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error("نام کاربری یافت نشد.")
            elif check_password(password_input, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
                st.success("ورود موفق!")
                st.experimental_rerun()
            else:
                st.error("رمز عبور اشتباه است.")

    else:  # Demo
        st.header("دمو")
        f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            st.success("پیش‌بینی دمو: سالم")
            st.session_state['demo_data'].append({'file': f.name, 'result': 'Healthy', 'time': datetime.now()})
        if st.session_state['demo_data']:
            df_demo = pd.DataFrame(st.session_state['demo_data'])
            st.subheader("تاریخچه دمو")
            st.dataframe(df_demo)

# ---------- Main App ----------
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", ["🏠 خانه", "🌱 پایش", "📅 زمان‌بندی", "📈 پیش‌بینی", "🍎 بیماری", "📥 دانلود", "🚪 خروج"])

    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    elif menu == "🏠 خانه":
        st.header("خانه")
        st.write("خوش آمدید به Seedling Pro. از منو گزینه‌ها را انتخاب کنید.")

    elif menu == "🌱 پایش":
        st.header("پایش نهال")
        with st.expander("➕ افزودن اندازه‌گیری"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت", placeholder="وضعیت آبیاری، کوددهی، علائم...")
            prune = st.checkbox("نیاز به هرس؟")
            if st.button("ثبت اندازه‌گیری"):
                with engine.begin() as conn_write:
                    conn_write.execute(measurements.insert().values(
                        user_id=user_id, date=str(date), height=height, leaves=leaves, notes=notes, prune_needed=int(prune)
                    ))
                st.success("اندازه‌گیری ذخیره شد.")
        sel = sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())
        df = pd.DataFrame(conn.execute(sel).mappings().all())
        if not df.empty:
            st.dataframe(df)

    elif menu == "📅 زمان‌بندی":
        st.header("زمان‌بندی")
        st.write("در این بخش می‌توانید برنامه زمان‌بندی مراقبت از نهال‌ها را ببینید.")

    elif menu == "📈 پیش‌بینی":
        st.header("پیش‌بینی")
        st.write("در این بخش می‌توانید پیش‌بینی رشد نهال‌ها را مشاهده کنید.")

    elif menu == "🍎 بیماری":
        st.header("بیماری")
        st.write("در این بخش اطلاعات مربوط به بیماری‌های نهال‌ها را ببینید.")

    elif menu == "📥 دانلود":
        st.header("دانلود")
        st.write("اینجا می‌توانید داده‌ها را دانلود کنید.")
