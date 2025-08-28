# app_predict_smart.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageStat
import os, base64, bcrypt, sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# TensorFlow
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

users_table = Table('users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)
measurements = Table('measurements', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('date', String), Column('height', Integer), Column('leaves', Integer),
    Column('notes', String), Column('prune_needed', Integer)
)
predictions_table = Table('predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)
meta.create_all(engine)

# ---------- Session ----------
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None

# ---------- Password helpers ----------
def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def check_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Load model ----------
MODEL_PATH = "model/seedling_model.h5"
_model = None
_model_loaded = False
if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        @st.cache_resource
        def load_model(path):
            return tf.keras.models.load_model(path)
        _model = load_model(MODEL_PATH)
        _model_loaded = True
    except Exception as e:
        st.warning(f"خطا در بارگذاری مدل: {e}")

# ---------- Heuristic fallback ----------
def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    r,g,b = stat.mean[:3]
    green_ratio = g/(r+g+b)
    mean_val = np.mean(stat.mean)
    if green_ratio<0.35 or mean_val<80:
        return "نیاز به هرس", f"{int((0.35-green_ratio)*100+50)}%"
    else:
        return "نیاز به هرس نیست", f"{int(green_ratio*100)}%"

# ---------- Model prediction ----------
def predict_with_model(img: Image.Image):
    x = np.expand_dims(np.array(img.convert("RGB").resize((224,224)))/255.0,0)
    preds = _model.predict(x)
    classes = ["سالم","بیمار","نیاز به هرس","کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = int(float(np.max(preds[0]))*100)
    return classes[idx], f"{confidence}%"

# ---------- Authentication ----------
if st.session_state.user_id is None:
    st.sidebar.subheader("ورود / ثبت‌نام")
    mode = st.sidebar.radio("حالت:", ["ورود","ثبت‌نام","ورود مهمان"])
    if mode=="ثبت‌نام":
        u = st.sidebar.text_input("نام کاربری", key="signup_u")
        p = st.sidebar.text_input("رمز عبور", type="password", key="signup_p")
        if st.sidebar.button("ثبت‌نام"):
            if not u or not p: st.sidebar.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    if conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first():
                        st.sidebar.error("نام کاربری قبلاً ثبت شده.")
                    else:
                        conn.execute(users_table.insert().values(username=u,password_hash=hash_password(p)))
                        st.sidebar.success("ثبت‌نام انجام شد.")
    elif mode=="ورود":
        u = st.sidebar.text_input("نام کاربری", key="login_u")
        p = st.sidebar.text_input("رمز عبور", type="password", key="login_p")
        if st.sidebar.button("ورود"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==u)).mappings().first()
                if r and check_password(p,r['password_hash']):
                    st.session_state.user_id = int(r['id'])
                    st.session_state.username = r['username']
                    st.experimental_rerun()
                else: st.sidebar.error("نام کاربری یا رمز اشتباه است.")
    else:
        st.session_state.user_id = 0
        st.session_state.username = "مهمان"
        st.experimental_rerun()
    st.stop()

# ---------- Sidebar Menu ----------
st.sidebar.subheader(f"خوش آمدید {st.session_state.username}")
menu = ["🏠 خانه","🌱 پایش نهال","📈 پیش‌بینی هوشمند هرس","📥 دانلود داده‌ها","🚪 خروج"]
choice = st.sidebar.radio("منو", menu)

# ---------- Pages ----------
if choice=="🏠 خانه":
    st.header("🏠 خانه")
    with engine.connect() as conn:
        last = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id).order_by(measurements.c.id.desc()).limit(1)).mappings().first()
        st.write("آخرین اندازه‌گیری:", last['height'] if last else "—")

elif choice=="🌱 پایش نهال":
    st.header("ثبت اندازه‌گیری نهال")
    with st.form("measure_form"):
        date = st.date_input("تاریخ", value=datetime.today())
        height = st.number_input("ارتفاع", min_value=0, step=1)
        leaves = st.number_input("تعداد برگ", min_value=0, step=1)
        notes = st.text_area("یادداشت")
        prune = st.checkbox("نیاز به هرس؟")
        if st.form_submit_button("ثبت"):
            with engine.connect() as conn:
                conn.execute(measurements.insert().values(
                    user_id=st.session_state.user_id,date=str(date),
                    height=int(height),leaves=int(leaves),
                    notes=notes,prune_needed=int(prune)
                ))
                st.success("ثبت شد.")

elif choice=="📈 پیش‌بینی هوشمند هرس":
    st.header("آپلود تصویر نهال")
    uploaded = st.file_uploader("انتخاب تصویر", type=["jpg","jpeg","png"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        try:
            if _model_loaded:
                label,conf = predict_with_model(img)
            else:
                label,conf = heuristic_predict(img)
            st.success(f"نتیجه: {label} — اعتماد: {conf}")
            # ذخیره در DB
            with engine.connect() as conn:
                conn.execute(predictions_table.insert().values(
                    user_id=st.session_state.user_id,
                    file_name=getattr(uploaded,"name",f"img_{datetime.now().timestamp()}"),
                    result=label, confidence=conf,
                    date=str(datetime.now())
                ))
        except Exception as e:
            st.error(f"خطا در پیش‌بینی: {e}")

elif choice=="📥 دانلود داده‌ها":
    st.header("دانلود داده‌ها")
    with engine.connect() as conn:
        ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state.user_id)).mappings().all()
        if ms:
            df = pd.DataFrame(ms)
            st.download_button("دانلود اندازه‌گیری‌ها", df.to_csv(index=False).encode(), "measurements.csv")
        else: st.info("هیچ داده‌ای برای دانلود وجود ندارد.")

elif choice=="🚪 خروج":
    st.session_state.user_id = None
    st.session_state.username = None
    st.experimental_rerun()
