import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image
import io

# ---------- Config ----------
st.set_page_config(page_title="🍎 Seedling Pro", page_icon="🍎", layout="wide")

# ---------- Custom CSS ----------
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e0f7fa, #ffffff);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.rtl {
    direction: rtl;
    text-align: right;
}
.section-card {
    background-color: #ffffff;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
h1, h2, h3 {
    color: #00796b;
}
.logo {
    width: 120px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

text_class = 'rtl'

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
                     Column('image_name', String),
                     Column('result', String),
                     Column('notes', String))

meta.create_all(engine)
conn = engine.connect()

# ---------- Session ----------
for key, default in [('user_id', None), ('username', None), ('demo_data', [])]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------- Password helpers ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Logo ----------
try:
    image_data = io.BytesIO()
    Image.new('RGB', (120, 120), color='#00796b').save(image_data, format='PNG')
    image_data.seek(0)
    st.image(image_data, width=120)
except:
    st.write("لوگو نمایش داده نشد")

st.markdown(f"<div class='{text_class}'><h1>سیستم مدیریت نهال سیب</h1></div>", unsafe_allow_html=True)

# ---------- Authentication ----------
if st.session_state['user_id'] is None:
    st.sidebar.header("احراز هویت")
    mode = st.sidebar.radio("حالت", ["ورود", "ثبت‌نام", "دمو"])

    if mode == "ثبت‌نام":
        st.subheader("ثبت‌نام")
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
                    conn.execute(users_table.insert().values(username=username_input, password_hash=hashed))
                    st.success("ثبت شد. لطفا وارد شوید.")

    elif mode == "ورود":
        st.subheader("ورود")
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
                st.experimental_rerun()
            else:
                st.error("رمز عبور اشتباه است.")

    else:
        st.subheader("حالت دمو")
        st.info("در حالت دمو داده ذخیره نمی‌شود.")
        f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
        if f:
            image = Image.open(f)
            st.image(image, use_container_width=True)
            st.success("پیش‌بینی دمو: سالم")
            st.write("یادداشت: این نتیجه آزمایشی است.")
            st.session_state['demo_data'].append({'file': f.name, 'result': 'Healthy', 'time': datetime.now()})
            if st.session_state['demo_data']:
                st.subheader("تاریخچه دمو")
                df_demo = pd.DataFrame(st.session_state['demo_data'])
                st.dataframe(df_demo)

# ---------- Main App after login ----------
if st.session_state['user_id']:
    st.sidebar.header(f"خوش آمدید {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", ["🏠 خانه", "🌱 پایش", "📅 زمان‌بندی", "📈 پیش‌بینی", "🍎 بیماری", "📥 دانلود", "🚪 خروج"])
    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.success("خروج انجام شد.")

    elif menu == "🏠 خانه":
        st.markdown(f"<div class='{text_class}'><h2>صفحه اصلی</h2><p>به اپلیکیشن مدیریت نهال سیب خوش آمدید.</p></div>", unsafe_allow_html=True)

    elif menu == "🌱 پایش":
        st.markdown(f"<div class='{text_class}'><h2>پایش نهال</h2></div>", unsafe_allow_html=True)
        with st.expander("➕ افزودن تصویر و ثبت اطلاعات"):
            f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"], key="tracking_upload")
            notes = st.text_area("یادداشت")
            if st.button("ثبت اندازه‌گیری") and f:
                try:
                    image = Image.open(f)
                    result = 'Healthy'  # پایه پردازش تصویر
                    conn.execute(measurements.insert().values(user_id=user_id, date=str(datetime.today()), image_name=f.name, result=result, notes=notes))
                    st.success("اندازه‌گیری ثبت شد.")
                except Exception as e:
                    st.error(f"خطا در ثبت اندازه‌گیری: {e}")
        try:
            sel = sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())
            df = pd.DataFrame(conn.execute(sel).mappings().all())
            if not df.empty:
                st.dataframe(df)
        except Exception as e:
            st.error(f"خطا در دریافت داده‌ها: {e}")

    elif menu == "📅 زمان‌بندی":
        st.markdown(f"<div class='{text_class}'><h2>زمان‌بندی آبیاری و کوددهی</h2><p>اینجا می‌توانید زمان‌بندی‌ها را مشاهده کنید.</p></div>", unsafe_allow_html=True)

    elif menu == "📈 پیش‌بینی":
        st.markdown(f"<div class='{text_class}'><h2>پیش‌بینی رشد</h2><p>در آینده مدل پیشرفته پیش‌بینی رشد اضافه خواهد شد.</p></div>", unsafe_allow_html=True)

    elif menu == "🍎 بیماری":
        st.markdown(f"<div class='{text_class}'><h2>تشخیص بیماری</h2><p>در آینده مدل تشخیص بیماری اضافه خواهد شد.</p></div>", unsafe_allow_html=True)

    elif menu == "📥 دانلود":
        st.markdown(f"<div class='{text_class}'><h2>دانلود اطلاعات</h2></div>", unsafe_allow_html=True)
        try:
            sel = sa.select(measurements).where(measurements.c.user_id==user_id)
            df = pd.DataFrame(conn.execute(sel).mappings().all())
            if not df.empty:
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("دانلود CSV", data=csv, file_name='measurements.csv', mime='text/csv')
        except Exception as e:
            st.error(f"خطا در دانلود داده‌ها: {e}")
