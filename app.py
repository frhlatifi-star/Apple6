import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image
from io import BytesIO
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 Seedling Pro", page_icon="🍎", layout="wide")

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
def display_logo():
    try:
        logo = Image.open("logo.png")  # مسیر لوگو خود را اینجا قرار دهید
        st.image(logo, width=100)
    except:
        st.write("سیبتک 🍎 Seedling Pro")  # اگر لوگو نیست متن نمایش داده شود

# ---------- Login / Sign Up ----------
if st.session_state['user_id'] is None:
    col1, col2 = st.columns([1,3])
    with col1:
        display_logo()
    with col2:
        st.title("سیبتک 🍎 Seedling Pro")

    auth_mode = st.radio("حالت:", ["ورود", "ثبت‌نام", "دمو"])

    if auth_mode == "ثبت‌نام":
        st.subheader("ثبت‌نام")
        username = st.text_input("نام کاربری")
        password = st.text_input("رمز عبور", type="password")
        if st.button("ثبت نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                sel = sa.select(users_table).where(users_table.c.username==username)
                r = conn.execute(sel).mappings().first()
                if r:
                    st.error("نام کاربری وجود دارد.")
                else:
                    hashed = hash_password(password)
                    conn.execute(users_table.insert().values(username=username, password_hash=hashed))
                    st.success("ثبت شد. لطفا وارد شوید.")

    elif auth_mode == "ورود":
        st.subheader("ورود")
        username = st.text_input("نام کاربری")
        password = st.text_input("رمز عبور", type="password")
        if st.button("ورود"):
            sel = sa.select(users_table).where(users_table.c.username==username)
            r = conn.execute(sel).mappings().first()
            if not r:
                st.error("نام کاربری یافت نشد.")
            elif check_password(password, r['password_hash']):
                st.session_state['user_id'] = r['id']
                st.session_state['username'] = r['username']
            else:
                st.error("رمز عبور اشتباه است.")

    else:
        st.subheader("دمو")
        f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            # دمو ساده
            st.success("پیش‌بینی دمو: سالم")
            st.session_state['demo_data'].append({'file': f.name, 'result': 'سالم', 'time': datetime.now()})
        if st.session_state['demo_data']:
            st.subheader("تاریخچه دمو")
            df_demo = pd.DataFrame(st.session_state['demo_data'])
            st.dataframe(df_demo)

# ---------- Main Menu ----------
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو", ["🏠 خانه", "🌱 پایش", "💻 دمو", "🚪 خروج"])
    user_id = st.session_state['user_id']

    if menu == "🚪 خروج":
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.experimental_rerun()

    elif menu == "🏠 خانه":
        st.header("خانه")
        st.write("به سیبتک 🍎 Seedling Pro خوش آمدید!")

    elif menu == "🌱 پایش":
        st.header("پایش نهال")
        with st.expander("➕ افزودن اندازه‌گیری"):
            date = st.date_input("تاریخ", value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت", placeholder="وضعیت آبیاری، کوددهی، علائم...")
            prune = st.checkbox("نیاز به هرس؟")
            if st.button("ثبت اندازه‌گیری"):
                conn.execute(measurements.insert().values(
                    user_id=user_id, date=str(date),
                    height=height, leaves=leaves,
                    notes=notes, prune_needed=int(prune)
                ))
                st.success("اندازه‌گیری ذخیره شد.")

        try:
            sel = sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())
            df = pd.DataFrame(conn.execute(sel).mappings().all())
            if not df.empty:
                st.dataframe(df)
        except Exception as e:
            st.error(f"خطا در بارگذاری داده‌ها: {e}")

    elif menu == "💻 دمو":
        st.header("دمو پیش‌بینی سلامت نهال")
        f = st.file_uploader("آپلود تصویر برگ/میوه/ساقه", type=["jpg","jpeg","png"])
        if f:
            st.image(f, use_container_width=True)
            try:
                # مدل خود را اینجا بارگذاری کنید
                model = load_model("model_leaf.h5")
                img = image.load_img(f, target_size=(128,128))
                img_array = image.img_to_array(img)
                img_array = np.expand_dims(img_array, axis=0) / 255.0
                prediction = model.predict(img_array)
                class_names = ["سالم", "بیمار"]
                result = class_names[np.argmax(prediction)]
                st.success(f"پیش‌بینی: {result}")
                st.session_state['demo_data'].append({'file': f.name, 'result': result, 'time': datetime.now()})
            except:
                st.success("پیش‌بینی دمو: سالم (مدل واقعی موجود نیست)")

        if st.session_state['demo_data']:
            st.subheader("تاریخچه دمو")
            df_demo = pd.DataFrame(st.session_state['demo_data'])
            st.dataframe(df_demo)
