# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Table, MetaData, ForeignKey
from PIL import Image, ImageStat
import numpy as np
import os

# ML imports
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# ---------- Page config ----------
st.set_page_config(page_title="سیبتک 🍎 مدیریت نهال", page_icon="🍎", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
html, body, [class*="css"] {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Vazirmatn', sans-serif;
    background-color: #e6f2e6;
}
.stButton>button {
    cursor: pointer;
    background-color: #4CAF50;
    color: white;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
}
.stButton>button:hover { background-color: #45a049; }
.card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    margin-bottom: 15px;
}
.card h3 { margin: 0; }
.card .metric { font-size: 24px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ---------- Database setup ----------
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

# ---------- Session ----------
for key in ['user_id','username','demo_history']:
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
        def _load_model(path): return tf.keras.models.load_model(path)
        _model = _load_model(MODEL_PATH)
        _model_loaded = True
    except Exception as e:
        st.warning(f"بارگذاری مدل با خطا مواجه شد: {e}")

# ---------- Heuristic prediction ----------
def heuristic_predict(img: Image.Image):
    img = img.convert("RGB").resize((224,224))
    stat = ImageStat.Stat(img)
    mean = np.mean(stat.mean)
    arr = np.array(img).astype(int)
    r,g,b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    yellow_ratio = ((r>g)&(g>=b)).mean()
    green_ratio = ((g>r+10)&(g>b+10)).mean()
    if green_ratio>0.12 and mean>80: return "سالم", f"{min(99,int(50+green_ratio*200))}%"
    if yellow_ratio>0.12 or mean<60:
        if yellow_ratio>0.25: return "بیمار", f"{min(95,int(40+yellow_ratio*200))}%"
        else: return "کم‌آبی/نیاز هرس", f"{min(90,int(30+(0.2-mean/255)*200))}%"
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
    st.markdown(f"""
    <div style='display:flex;align-items:center;margin-bottom:20px;'>
        <img src='logo.png' width='64' style='margin-left:12px;border-radius:12px;'>
        <div>
            <h2 style='margin:0'>سیبتک</h2>
            <small style='color:#666'>مدیریت و پایش نهال</small>
        </div>
    </div><hr/>
    """, unsafe_allow_html=True)
app_header()

# ---------- Auth ----------
if st.session_state['user_id'] is None:
    col1,col2 = st.columns([1,2])
    with col1: mode = st.radio("حالت:", ["ورود","ثبت‌نام","دمو"])
    with col2: st.write("")
    if mode=="ثبت‌نام":
        st.subheader("ثبت‌نام کاربر جدید")
        username = st.text_input("نام کاربری", key="signup_username")
        password = st.text_input("رمز عبور", type="password", key="signup_password")
        if st.button("ثبت‌نام"):
            if not username or not password: st.error("نام کاربری و رمز عبور را وارد کنید.")
            else:
                try:
                    with engine.connect() as conn:
                        sel = sa.select(users_table).where(users_table.c.username==username)
                        if conn.execute(sel).mappings().first(): st.error("این نام کاربری قبلاً ثبت شده است.")
                        else:
                            conn.execute(users_table.insert().values(username=username,password_hash=hash_password(password)))
                            st.success("ثبت‌نام انجام شد. اکنون وارد شوید.")
                except Exception as e: st.error(f"خطا در ثبت‌نام: {e}")
    elif mode=="ورود":
        st.subheader("ورود به حساب کاربری")
        username = st.text_input("نام کاربری", key="login_username")
        password = st.text_input("رمز عبور", type="password", key="login_password")
        if st.button("ورود"):
            try:
                r = engine.connect().execute(sa.select(users_table).where(users_table.c.username==username)).mappings().first()
                if not r: st.error("نام کاربری یافت نشد.")
                elif check_password(password,r['password_hash']):
                    st.session_state['user_id']=int(r['id'])
                    st.session_state['username']=r['username']
                    st.experimental_rerun = lambda: None
                else: st.error("رمز عبور اشتباه است.")
            except Exception as e: st.error(f"خطا در ورود: {e}")
    else:  # Demo
        st.subheader("حالت دمو — پیش‌بینی نمونه")
        uploaded = st.file_uploader("یک تصویر آپلود کنید", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded: label,conf = predict_with_model(img)
            else: label,conf = heuristic_predict(img)
            color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
            st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)

# ---------- Main app ----------
else:
    st.sidebar.header(f"خوش آمدید، {st.session_state['username']}")
    menu = st.sidebar.selectbox("منو",[
        "🏠 خانه","🌱 پایش نهال","📅 زمان‌بندی","📈 پیش‌بینی سلامت نهال",
        "🍎 ثبت بیماری / یادداشت","📥 دانلود داده‌ها","🚪 خروج"])
    user_id = st.session_state['user_id']

    if menu=="🚪 خروج":
        st.session_state['user_id']=None
        st.session_state['username']=None
        st.experimental_rerun = lambda: None

    # --- Home ---
    if menu=="🏠 خانه":
        st.header("خانه")
        with engine.connect() as conn:
            ms = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
            ps = conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id)).mappings().all()
        col1,col2 = st.columns(2)
        col1.markdown(f"<div class='card'><h3>تعداد اندازه‌گیری‌ها</h3><div class='metric'>{len(ms)}</div></div>",unsafe_allow_html=True)
        col2.markdown(f"<div class='card'><h3>تعداد پیش‌بینی‌ها</h3><div class='metric'>{len(ps)}</div></div>",unsafe_allow_html=True)

    # --- Measurements ---
    elif menu=="🌱 پایش نهال":
        st.header("پایش نهال — ثبت رشد")
        with st.expander("➕ افزودن اندازه‌گیری"):
            date = st.date_input("تاریخ",value=datetime.today())
            height = st.number_input("ارتفاع (سانتی‌متر)", min_value=0, step=1)
            leaves = st.number_input("تعداد برگ", min_value=0, step=1)
            notes = st.text_area("یادداشت")
            prune = st.checkbox("نیاز به هرس؟")
            if st.button("ثبت اندازه‌گیری"):
                with engine.connect() as conn:
                    conn.execute(measurements.insert().values(user_id=user_id,date=str(date),height=int(height),leaves=int(leaves),notes=notes,prune_needed=int(prune)))
                    st.success("اندازه‌گیری ثبت شد.")
        # نمایش جدول و نمودار
        with engine.connect() as conn:
            rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id).order_by(measurements.c.date.desc())).mappings().all()
        if rows:
            df = pd.DataFrame(rows)
            st.subheader("تاریخچه اندازه‌گیری‌ها")
            st.dataframe(df)
            try:
                df_plot = df.copy(); df_plot['date']=pd.to_datetime(df_plot['date'])
                st.line_chart(df_plot.set_index('date')['height'])
                st.line_chart(df_plot.set_index('date')['leaves'])
            except: pass
        else: st.info("هیچ اندازه‌گیری‌ای ثبت نشده است.")

    # --- Schedule ---
    elif menu=="📅 زمان‌بندی":
        st.header("زمان‌بندی فعالیت‌ها")
        with st.expander("➕ افزودن برنامه"):
            task = st.text_input("فعالیت")
            task_date = st.date_input("تاریخ برنامه")
            task_notes = st.text_area("یادداشت")
            if st.button("ثبت برنامه"):
                with engine.connect() as conn:
                    conn.execute(schedule_table.insert().values(user_id=user_id,task=task,date=str(task_date),notes=task_notes))
                    st.success("برنامه ثبت شد.")
        with engine.connect() as conn:
            rows = conn.execute(sa.select(schedule_table).where(schedule_table.c.user_id==user_id).order_by(schedule_table.c.date.desc())).mappings().all()
        if rows:
            st.subheader("برنامه‌های ثبت‌شده")
            st.dataframe(pd.DataFrame(rows))
        else: st.info("هیچ برنامه‌ای ثبت نشده است.")

    # --- Prediction ---
    elif menu=="📈 پیش‌بینی سلامت نهال":
        st.header("پیش‌بینی سلامت نهال")
        uploaded = st.file_uploader("آپلود تصویر نهال", type=["jpg","jpeg","png"])
        if uploaded:
            img = Image.open(uploaded)
            st.image(img,use_container_width=True)
            if _model_loaded: label,conf = predict_with_model(img)
            else: label,conf = heuristic_predict(img)
            color = "#4CAF50" if "سالم" in label else "#FF9800" if "کم‌آبی" in label else "#F44336"
            st.markdown(f"<div class='card' style='border-left:6px solid {color};'><h3>نتیجه: {label}</h3><div>اعتماد: {conf}</div></div>",unsafe_allow_html=True)
            with engine.connect() as conn:
                conn.execute(predictions_table.insert().values(user_id=user_id,file_name=getattr(uploaded,'name',str(datetime.now().timestamp())),result=label,confidence=conf,date=str(datetime.now())))
            # history
            with engine.connect() as conn:
                rows = conn.execute(sa.select(predictions_table).where(predictions_table.c.user_id==user_id).order_by(predictions_table.c.date.desc())).mappings().all()
            if rows:
                st.subheader("تاریخچه پیش‌بینی‌ها")
                st.dataframe(pd.DataFrame(rows))

    # --- Disease notes ---
    elif menu=="🍎 ثبت بیماری / یادداشت":
        st.header("ثبت بیماری / یادداشت")
        note = st.text_area("شرح مشکل یا علائم")
        if st.button("ثبت یادداشت"):
            with engine.connect() as conn:
                conn.execute(disease_table.insert().values(user_id=user_id,note=note,date=str(datetime.now())))
                st.success("یادداشت ثبت شد.")
        with engine.connect() as conn:
            rows = conn.execute(sa.select(disease_table).where(disease_table.c.user_id==user_id).order_by(disease_table.c.date.desc())).mappings().all()
        if rows:
            st.subheader("یادداشت‌های ثبت‌شده")
            st.dataframe(pd.DataFrame(rows))
        else: st.info("هیچ یادداشتی ثبت نشده است.")

    # --- Download ---
    elif menu=="📥 دانلود داده‌ها":
        st.header("دانلود داده‌ها")
        with engine.connect() as conn:
            rows = conn.execute(sa.select(measurements).where(measurements.c.user_id==user_id)).mappings().all()
        if rows:
            df = pd.DataFrame(rows)
            st.download_button("دانلود اندازه‌گیری‌ها (CSV)",df.to_csv(index=False).encode('utf-8-sig'),"measurements.csv","text/csv")
        else: st.info("داده‌ای برای دانلود وجود ندارد.")
