# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import base64
import os
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat

# --- TensorFlow (اختیاری) ---
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- تنظیمات صفحه ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS و راست‌چین ----------
st.markdown("""
<style>
:root {
    --accent: #2e7d32;
    --accent-2: #388e3c;
    --bg-1: #eaf9e7;
    --card: #ffffff;
}
body, html, [class*="css"] {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Vazirmatn', Tahoma, sans-serif;
    background: linear-gradient(135deg, #eaf9e7, #f7fff8);
}
.stButton>button {
    background-color: var(--accent-2) !important;
    color: white !important;
    border-radius: 8px !important;
    padding: 8px 16px;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #2e7d32 !important;
}
input, textarea {
    background-color: #ffffff !important;
    color: #000 !important;
}
.card {
    background-color: var(--card);
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    margin-bottom: 15px;
}
.card h3 {
    margin: 0;
}
</style>
""", unsafe_allow_html=True)

# ---------- دیتابیس ----------
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
    Column('date', String),
    Column('height', Integer),
    Column('leaves', Integer),
    Column('notes', String),
    Column('prune_needed', Integer)
)

schedule_table = Table('schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)

predictions_table = Table('predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)

disease_table = Table('disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)

meta.create_all(engine)

# ---------- Session defaults ----------
for key in ['user_id','username']:
    if key not in st.session_state:
        st.session_state[key] = None

# ---------- رمزگذاری ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- مدل پیش‌بینی ----------
MODEL_PATH = "model/seedling_model.h5"
_model = None
_model_loaded = False
if TF_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        @st.cache_resource
        def _load_model(path):
            return tf.keras.models.load_model(path)
        _model = _load_model(MODEL_PATH)
        _model_loaded = True
    except Exception as e:
        st.warning(f"بارگذاری مدل با خطا مواجه شد: {e}")

def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    arr = np.array(img)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_ratio = ((r>g)&(g>=b)).mean()
    green_ratio = ((g>r+10)&(g>b+10)).mean()
    mean = arr.mean()
    # تشخیص وضعیت
    if green_ratio>0.12 and mean>80:
        return "سالم", "بالا"
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25:
            return "بیمار", "کم"
        return "نیاز به هرس/کم‌آبی", "متوسط"
    return "نامشخص", "50%"

def predict_with_model(img: Image.Image):
    x = np.expand_dims(np.array(img.convert("RGB").resize((224,224)))/255.0,0)
    preds = _model.predict(x)
    classes = ["سالم","بیمار","نیاز به هرس","کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = int(float(np.max(preds[0]))*100)
    return classes[idx], f"{confidence}%"

# ---------- Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path,"rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;'>"
    else:
        img_html = "<div style='font-size:36px;'>🍎</div>"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:20px;'>
        {img_html}
        <div style='margin-right:12px;'>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#666'>مدیریت و پایش نهال</small>
        </div>
    </div>
    <hr/>
    """, unsafe_allow_html=True)

app_header()

# ---------- Authentication ----------
if st.session_state['user_id'] is None:
    st.subheader("ورود یا ثبت‌نام")
    col1,col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2: st.write("")
    if mode=="ثبت‌نام":
        username = st.text_input("نام کاربری", key="signup")
        password = st.text_input("رمز عبور", type="password", key="pass_signup")
        if st.button("ثبت‌نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                try:
                    with engine.connect() as conn:
                        sel = sa.select(users_table).where(users_table.c.username==username)
                        if conn.execute(sel).mappings().first():
                            st.error("نام کاربری موجود است.")
                        else:
                            conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                            st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
                except Exception as e:
                    st.error(f"خطا: {e}")
    elif mode=="ورود":
        username = st.text_input("نام کاربری", key="login")
        password = st.text_input("رمز عبور", type="password", key="pass_login")
        if st.button("ورود"):
            try:
                with engine.connect() as conn:
                    r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                    if not r:
                        st.error("نام کاربری یافت نشد.")
                    elif check_password(password,r['password_hash']):
                        st.session_state['user_id']=int(r['id'])
                        st.session_state['username']=r['username']
                        st.experimental_rerun()
                    else:
                        st.error("رمز اشتباه است.")
            except Exception as e:
                st.error(f"خطا: {e}")
    else:
        st.info("حالت دمو — فقط پیش‌بینی آزمایشی فعال است.")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded:
                label,conf = predict_with_model(img)
            else:
                label,conf = heuristic_predict(img)
            st.markdown(f"<div class='card'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)
    st.stop()

# ---------- Menu ----------
st.markdown("### منو")
menu_items = [
    ("🏠 خانه","home"),
    ("🌱 پایش نهال","tracking"),
    ("📅 زمان‌بندی","schedule"),
    ("📈 پیش‌بینی سلامت","predict"),
    ("🍎 ثبت بیماری","disease"),
    ("📥 دانلود داده‌ها","download"),
    ("🚪 خروج","logout")
]
cols = st.columns(len(menu_items))
for idx,(label,key) in enumerate(menu_items):
    with cols[idx]:
        if st.button(label):
            st.session_state['page'] = key

# ---------- Router ----------
page = st.session_state.get('page',"home")

if page=="home":
    st.header("🏠 خانه")
    with engine.connect() as conn:
        ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==st.session_state['user_id'])).mappings().all()
        ps = conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==st.session_state['user_id'])).mappings().all()
        ds = conn.execute(sa.select(disease_table).where(disease_table.c.user_id==st.session_state['user_id'])).mappings().all()
    st.markdown(f"<div class='card'><h3>خوش آمدید {st.session_state['username']}</h3><div>تعداد ثبت‌ها: {len(ms)}</div><div>تعداد پیش‌بینی‌ها: {len(ps)}</div><div>تعداد یادداشت بیماری: {len(ds)}</div></div>",unsafe_allow_html=True)

elif page=="tracking":
    st.header("🌱 پایش نهال")
    height = st.number_input("ارتفاع (سانتی‌متر)",min_value=0,max_value=300)
    leaves = st.number_input("تعداد برگ‌ها",min_value=0,max_value=500)
    notes = st.text_area("یادداشت")
    prune_needed = st.selectbox("آیا نیاز به هرس دارد؟",["خیر","بله"])
    if st.button("ثبت اطلاعات"):
        with engine.connect() as conn:
            conn.execute(measurements.insert().values(
                user_id=st.session_state['user_id'],
                date=str(datetime.now()),
                height=int(height),
                leaves=int(leaves),
                notes=notes,
                prune_needed=1 if prune_needed=="بله" else 0
            ))
        st.success("اطلاعات ثبت شد.")

elif page=="schedule":
    st.header("📅 زمان‌بندی")
    task = st.text_input("نام کار")
    date = st.date_input("تاریخ انجام")
    notes = st.text_area("یادداشت")
    if st.button("ثبت کار"):
        with engine.connect() as conn:
            conn.execute(schedule_table.insert().values(
                user_id=st.session_state['user_id'],
                task=task,
                date=str(date),
                notes=notes
            ))
        st.success("کار ثبت شد.")

elif page=="predict":
    st.header("📈 پیش‌بینی سلامت نهال")
    uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        if _model_loaded:
            label,conf = predict_with_model(img)
        else:
            label,conf = heuristic_predict(img)
        with engine.connect() as conn:
            conn.execute(predictions_table.insert().values(
                user_id=st.session_state['user_id'],
                file_name=uploaded.name,
                result=label,
                confidence=conf,
                date=str(datetime.now())
            ))
        st.markdown(f"<div class='card'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)

elif page=="disease":
    st.header("🍎 ثبت بیماری")
    note = st.text_area("شرح بیماری یا مشکل")
    if st.button("ثبت"):
        with engine.connect() as conn:
            conn.execute(disease_table.insert().values(
                user_id=st.session_state['user_id'],
                note=note,
                date=str(datetime.now())
            ))
        st.success("ثبت شد.")

elif page=="download":
    st.header("📥 دانلود داده‌ها")
    with engine.connect() as conn:
        df = pd.read_sql(sa.select(measurements).where(measurements.c.user_id==st.session_state['user_id']),conn)
    csv = df.to_csv(index=False).encode()
    st.download_button("دانلود CSV",data=csv,file_name="measurements.csv",mime="text/csv")

elif page=="logout":
    st.session_state['user_id']=None
    st.session_state['username']=None
    st.experimental_rerun()
