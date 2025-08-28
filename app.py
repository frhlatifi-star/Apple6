# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from PIL import Image, ImageStat
import os, base64
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey

# --- Optional TensorFlow (model) ---
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- Config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS / RTL ----------
st.markdown("""
<style>
:root { --accent: #2e7d32; --accent-2: #388e3c; --bg-1: #eaf9e7; --card: #ffffff; }
body, html { direction: rtl; text-align: right; font-family: Vazirmatn, Tahoma, sans-serif; background: linear-gradient(135deg, #eaf9e7, #f7fff8);}
.card { background: var(--card); padding: 1rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 15px;}
.stButton>button { background-color: var(--accent-2) !important; color: white !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
DB_FILE = "users_data.db"
engine = sa.create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
meta = MetaData()

# Users
users_table = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String, unique=True, nullable=False),
    Column('password_hash', String, nullable=False)
)

# Measurements
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

# Schedule
schedule_table = Table(
    'schedule', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('task', String),
    Column('date', String),
    Column('notes', String)
)

# Predictions
predictions_table = Table(
    'predictions', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('file_name', String),
    Column('result', String),
    Column('confidence', String),
    Column('date', String)
)

# Disease notes
disease_table = Table(
    'disease', meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('note', String),
    Column('date', String)
)

# Create tables if not exist
meta.create_all(engine)

# ---------- Session defaults ----------
for key in ['user_id', 'username', 'demo_history']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'demo_history' else []

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------- Model ----------
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

# ---------- Heuristic prediction ----------
def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    arr = np.array(img).astype(int)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_ratio = ((r>g)&(g>=b)).mean()
    green_ratio = ((g>r+10)&(g>b+10)).mean()
    mean_val = np.mean(arr)
    # Determine label
    if green_ratio>0.12 and mean_val>80:
        prune_needed = 0
        return "سالم", f"{min(99,int(50+green_ratio*200))}%", prune_needed
    elif yellow_ratio>0.12 or mean_val<60:
        prune_needed = 1
        if yellow_ratio>0.25:
            return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%", prune_needed
        else:
            return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean_val/255)*200))}%", prune_needed
    return "نامشخص", "50%", 0

def predict_with_model(img: Image.Image):
    x = np.expand_dims(np.array(img.convert("RGB").resize((224,224)))/255.0,0)
    preds = _model.predict(x)
    classes = ["سالم","بیمار","نیاز به هرس","کم‌آبی"]
    idx = int(np.argmax(preds[0]))
    confidence = int(float(np.max(preds[0]))*100)
    prune_needed = 1 if classes[idx] in ["بیمار","نیاز به هرس","کم‌آبی"] else 0
    return classes[idx], f"{confidence}%", prune_needed

# ---------- Header ----------
def app_header():
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path,"rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_html = f"<img src='data:image/png;base64,{encoded}' width='64' style='border-radius:12px;'>"
    else:
        img_html = "🍎"
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:10px;'>
        {img_html}
        <div style='margin-right:12px;'>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#555'>مدیریت و پایش نهال</small>
        </div>
    </div><hr/>
    """, unsafe_allow_html=True)
app_header()

# ---------- Authentication ----------
if st.session_state['user_id'] is None:
    st.write("### ورود / ثبت‌نام / دمو")
    col1,col2 = st.columns([1,2])
    with col1:
        mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2:
        st.write("")
    
    if mode=="ثبت‌نام":
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام"):
            if not username or not password:
                st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                with engine.connect() as conn:
                    sel = sa.select(users_table).where(users_table.c.username==username)
                    if conn.execute(sel).mappings().first():
                        st.error("این نام کاربری قبلاً ثبت شده است.")
                    else:
                        conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                        st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
    elif mode=="ورود":
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            with engine.connect() as conn:
                r = conn.execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                if not r:
                    st.error("نام کاربری یافت نشد.")
                elif check_password(password,r['password_hash']):
                    st.session_state['user_id']=int(r['id'])
                    st.session_state['username']=r['username']
                    st.experimental_rerun = lambda: None
                else:
                    st.error("رمز عبور اشتباه است.")
    else:  # Demo
        st.subheader("حالت دمو — پیش‌بینی نمونه")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded:
                label,conf,prune = predict_with_model(img)
            else:
                label,conf,prune = heuristic_predict(img)
            color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
            st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)
    st.stop()

# ---------- Sidebar Menu ----------
menu_choice = st.sidebar.selectbox(f"خوش آمدید، {st.session_state['username']}", 
                                   ["🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت نهال","🍎 ثبت بیماری / یادداشت","📥 دانلود داده‌ها","🚪 خروج"])
user_id = st.session_state['user_id']

# ---------- Pages ----------
def page_home():
    st.header("خانه")
    with engine.connect() as conn:
        m_sel = sa.select(measurements).where(measurements.c.user_id==user_id)
        df = pd.DataFrame(conn.execute(m_sel).mappings().all())
    if not df.empty:
        st.line_chart(df.set_index('date')['height'])
page_home

def page_measure():
    st.header("پایش نهال")
    uploaded = st.file_uploader("تصویر نهال", type=["jpg","jpeg","png"])
    note = st.text_area("یادداشت")
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        if _model_loaded:
            label,conf,prune = predict_with_model(img)
        else:
            label,conf,prune = heuristic_predict(img)
        # Save measurement
        with engine.connect() as conn:
            conn.execute(measurements.insert().values(user_id=user_id,date=str(datetime.today().date()),
                                                      height=np.random.randint(30,80),leaves=np.random.randint(5,25),
                                                      notes=note,prune_needed=prune))
        color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
        st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)
page_measure

def page_schedule():
    st.header("زمان‌بندی")
    task = st.text_input("کار")
    date_input = st.date_input("تاریخ")
    notes = st.text_area("یادداشت")
    if st.button("افزودن کار"):
        with engine.connect() as conn:
            conn.execute(schedule_table.insert().values(user_id=user_id,task=task,date=str(date_input),notes=notes))
            st.success("کار اضافه شد.")
    # نمایش جدول
    with engine.connect() as conn:
        sel = sa.select(schedule_table).where(schedule_table.c.user_id==user_id).order_by(schedule_table.c.date.desc())
        df = pd.DataFrame(conn.execute(sel).mappings().all())
        st.dataframe(df)

def page_predict():
    st.header("پیش‌بینی سلامت نهال")
    uploaded = st.file_uploader("تصویر نهال برای پیش‌بینی", type=["jpg","jpeg","png"], key="predict_page")
    if uploaded:
        img = Image.open(uploaded)
        st.image(img,use_container_width=True)
        if _model_loaded:
            label,conf,prune = predict_with_model(img)
        else:
            label,conf,prune = heuristic_predict(img)
        # Save prediction
        with engine.connect() as conn:
            conn.execute(predictions_table.insert().values(user_id=user_id,file_name=uploaded.name,result=label,
                                                           confidence=conf,date=str(datetime.today().date())))
        color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
        st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)

def page_disease():
    st.header("ثبت بیماری / یادداشت")
    note = st.text_area("یادداشت بیماری")
    if st.button("ثبت یادداشت"):
        with engine.connect() as conn:
            conn.execute(disease_table.insert().values(user_id=user_id,note=note,date=str(datetime.today().date())))
            st.success("یادداشت ذخیره شد.")

def page_download():
    st.header("دانلود داده‌ها")
    with engine.connect() as conn:
        df1 = pd.DataFrame(conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all())
        df2 = pd.DataFrame(conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id)).mappings().all())
        df3 = pd.DataFrame(conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all())
        df4 = pd.DataFrame(conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id)).mappings().all())
    for df,name in zip([df1,df2,df3,df4],["measurements","schedule","predictions","disease"]):
        if not df.empty:
            df.to_csv(f"{name}.csv",index=False)
            st.markdown(f"- [{name}.csv](./{name}.csv)")

def page_logout():
    st.session_state['user_id']=None
    st.session_state['username']=None
    st.experimental_rerun = lambda: None

# ---------- Menu Router ----------
pages = {
    "🏠 خانه": page_home,
    "🌱 پایش نهال": page_measure,
    "📅 زمان‌بندی": page_schedule,
    "📈 پیش‌بینی سلامت نهال": page_predict,
    "🍎 ثبت بیماری / یادداشت": page_disease,
    "📥 دانلود داده‌ها": page_download,
    "🚪 خروج": page_logout
}

if menu_choice in pages:
    pages[menu_choice]()
